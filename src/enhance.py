"""Stage 4b: enhancement stack feeding the adaptive pipeline.

Order is configurable and defaults to Retinex -> CLAHE -> gray-world.  Every
step is individually togglable, which is what makes the ablations one-line
config changes.
"""
from __future__ import annotations

import copy

import cv2
import numpy as np

from .io_utils import to_uint8
from .density import grayscale
from .guided_filter import guided_filter


def _percentile_stretch(x: np.ndarray, low: float = 1.0, high: float = 99.0) -> np.ndarray:
    lo, hi = np.percentile(x, [low, high])
    if hi <= lo + 1e-6:
        return np.clip(x, 0.0, 1.0)
    return np.clip((x - lo) / (hi - lo), 0.0, 1.0)


def apply_clahe(img: np.ndarray, clip_limit: float = 2.0,
                tile_grid_size: tuple[int, int] | list[int] = (8, 8),
                strength: float = 1.0) -> np.ndarray:
    """CLAHE on the L channel in LAB, blended with the input by ``strength``."""
    lab = cv2.cvtColor(to_uint8(img), cv2.COLOR_RGB2LAB)
    l_chan, a_chan, b_chan = cv2.split(lab)
    tiles = (int(tile_grid_size[0]), int(tile_grid_size[1]))
    clahe = cv2.createCLAHE(clipLimit=float(max(clip_limit, 0.01)), tileGridSize=tiles)
    l_eq = clahe.apply(l_chan)
    equalised = cv2.cvtColor(cv2.merge([l_eq, a_chan, b_chan]), cv2.COLOR_LAB2RGB)
    equalised = np.clip(equalised.astype(np.float32) / 255.0, 0.0, 1.0)
    s = float(np.clip(strength, 0.0, 1.0))
    return np.clip((1.0 - s) * img + s * equalised, 0.0, 1.0).astype(np.float32)


def _retinex_luminance(lum: np.ndarray, sigmas: list[float]) -> np.ndarray:
    eps = 1e-6
    log_l = np.log(lum + eps)
    msr = np.zeros_like(lum, dtype=np.float32)
    for sigma in sigmas:
        sigma = float(max(sigma, 0.5))
        blur = cv2.GaussianBlur(lum, ksize=(0, 0), sigmaX=sigma, sigmaY=sigma,
                                borderType=cv2.BORDER_REFLECT)
        msr += (log_l - np.log(blur + eps)).astype(np.float32)
    msr /= float(max(1, len(sigmas)))
    return _percentile_stretch(msr)


def apply_retinex(img: np.ndarray, strength: float = 0.5, method: str = "msr",
                  sigmas: list[float] | None = None) -> np.ndarray:
    """Retinex illumination correction on luminance, colour is preserved."""
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0:
        return img
    sigmas = list(sigmas or [15, 80, 250])
    if method == "ssr":
        sigmas = sigmas[:1]
    lum = np.clip(grayscale(img), 1e-3, 1.0)
    corrected = _retinex_luminance(lum, sigmas)
    gain = corrected / (lum + 1e-6)
    gain = np.clip(gain, 0.5, 2.0).astype(np.float32)
    lit = np.clip(img * gain[..., None], 0.0, 1.0)
    return np.clip((1.0 - strength) * img + strength * lit, 0.0, 1.0).astype(np.float32)


def apply_retinex_fast(img: np.ndarray, strength: float = 0.5,
                       scale: float = 0.5) -> np.ndarray:
    """Cheap Retinex approximation: guided-filter illumination on a downscaled copy.

    The illumination gain is estimated at ``scale`` resolution and bilinearly
    upsampled.  It is opt-in (`v2.retinex.fast: true`) so the v1 path is
    unchanged.
    """
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0:
        return img
    h, w = img.shape[:2]
    scale = float(np.clip(scale, 0.2, 1.0))
    sw, sh = max(8, int(round(w * scale))), max(8, int(round(h * scale)))
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    lum = np.clip(grayscale(small), 1e-3, 1.0)
    radius = max(4, int(0.03 * max(sw, sh)))
    illumination = guided_filter(lum, lum, radius=radius, eps=1e-2)
    gain = np.clip(lum / (illumination + 1e-6), 0.5, 2.0).astype(np.float32)
    gain_full = cv2.resize(gain, (w, h), interpolation=cv2.INTER_LINEAR)
    lit = np.clip(img * gain_full[..., None], 0.0, 1.0)
    return np.clip((1.0 - strength) * img + strength * lit, 0.0, 1.0).astype(np.float32)


def apply_gray_world(img: np.ndarray, strength: float = 0.6,
                     max_gain: float = 1.25) -> np.ndarray:
    """Reduce residual colour cast by equalising channel means."""
    strength = float(np.clip(strength, 0.0, 1.0))
    if strength <= 0.0:
        return img
    means = np.clip(img.reshape(-1, 3).mean(axis=0), 1e-4, None)
    target = float(means.mean())
    gain = np.clip(target / means, 1.0 / float(max_gain), float(max_gain)).astype(np.float32)
    cast_corrected = np.clip(img * gain.reshape(1, 1, 3), 0.0, 1.0)
    return np.clip((1.0 - strength) * img + strength * cast_corrected, 0.0, 1.0).astype(np.float32)


def apply_enhancements(
    img: np.ndarray,
    class_cfg: dict,
    defaults: dict,
    order: list[str],
    switches: dict[str, bool] | None = None,
    retinex_fast: bool = False,
    retinex_scale: float = 0.5,
) -> tuple[np.ndarray, dict]:
    """Apply the configured enhancement chain.

    ``switches`` is the ablation hook, e.g. ``{"retinex": False}``.
    Returns the enhanced image and the effective settings used.
    """
    cfg = copy.deepcopy(defaults or {})
    for key, value in class_cfg.items():
        if isinstance(value, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(value)
        else:
            cfg[key] = copy.deepcopy(value)
    switches = switches or {}
    applied: dict[str, dict] = {}
    out = img
    for step in order:
        if not switches.get(step, True):
            continue
        step_cfg = cfg.get(step) or {}
        if not step_cfg.get("enabled", False):
            continue
        if step == "retinex":
            if retinex_fast:
                out = apply_retinex_fast(out, strength=step_cfg.get("strength", 0.5),
                                         scale=retinex_scale)
            else:
                out = apply_retinex(
                    out,
                    strength=step_cfg.get("strength", 0.5),
                    method=step_cfg.get("method", "msr"),
                    sigmas=step_cfg.get("sigmas", [15, 80, 250]),
                )
        elif step == "clahe":
            out = apply_clahe(
                out,
                clip_limit=step_cfg.get("clip_limit", 2.0),
                tile_grid_size=step_cfg.get("tile_grid_size", [8, 8]),
                strength=step_cfg.get("strength", 1.0),
            )
        elif step == "gray_world":
            out = apply_gray_world(
                out,
                strength=step_cfg.get("strength", 0.6),
                max_gain=step_cfg.get("max_gain", 1.25),
            )
        else:
            raise ValueError(f"Unknown enhancement step: {step}")
        applied[step] = step_cfg
    return np.clip(out, 0.0, 1.0).astype(np.float32), applied
