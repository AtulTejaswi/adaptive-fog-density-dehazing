"""Dark Channel Prior (DCP) core: atmospheric light, transmission, recovery."""
from __future__ import annotations

import cv2
import numpy as np

from .density import dark_channel, grayscale
from .guided_filter import guided_filter
from .sky import gradient_magnitude


def atmospheric_light(img: np.ndarray, dark: np.ndarray | None = None,
                      patch_size: int = 15, top_percent: float = 0.1) -> np.ndarray:
    """Estimate A from the brightest 0.1% of dark-channel pixels."""
    if dark is None:
        dark = dark_channel(img, patch_size)
    h, w = dark.shape[:2]
    n_pixels = max(1, int(h * w * float(top_percent) / 100.0))
    flat_dark = dark.reshape(-1)
    idx = np.argpartition(flat_dark, -n_pixels)[-n_pixels:]
    pixels = img.reshape(-1, img.shape[-1])[idx]
    # Mean of the brightest candidates is more stable than a single pixel.
    airlight = pixels.mean(axis=0)
    return np.clip(airlight, 0.0, 1.0).astype(np.float32)


def atmospheric_light_v2(img: np.ndarray, dark: np.ndarray | None = None,
                         patch_size: int = 15, cfg: dict | None = None) -> np.ndarray:
    """v2 airlight: connected + low-gradient candidates, with a v1 fallback.

    Candidate pixels are the brightest dark-channel values; isolated specks
    (small connected components) and high-gradient pixels (edges of bright
    objects) are rejected before averaging.  If nothing survives, the v1
    estimator is used unchanged.
    """
    cfg = cfg or {}
    if dark is None:
        dark = dark_channel(img, patch_size)
    h, w = dark.shape[:2]
    n_pixels = max(1, int(h * w * float(cfg.get("candidate_percent", 0.5)) / 100.0))
    flat = dark.reshape(-1)
    idx = np.argpartition(flat, -n_pixels)[-n_pixels:]
    candidate = np.zeros(h * w, dtype=np.uint8)
    candidate[idx] = 1
    candidate = candidate.reshape(h, w)

    num, labels, stats, _ = cv2.connectedComponentsWithStats(candidate, connectivity=8)
    min_area = max(1, int(float(cfg.get("min_component_fraction", 0.0005)) * h * w))
    if num > 1:
        keep_labels = np.nonzero(stats[1:, cv2.CC_STAT_AREA] >= min_area)[0] + 1
        keep = np.isin(labels, keep_labels) if keep_labels.size else np.zeros((h, w), bool)
    else:
        keep = np.zeros((h, w), dtype=bool)

    grad = gradient_magnitude(img)
    threshold = float(np.percentile(grad, float(cfg.get("gradient_percentile", 60))))
    keep &= grad <= threshold

    if int(keep.sum()) < max(1, int(0.05 * n_pixels)):
        return atmospheric_light(img, dark, patch_size)
    pixels = img.reshape(-1, img.shape[-1])[keep.reshape(-1)]
    return np.clip(pixels.mean(axis=0), 0.0, 1.0).astype(np.float32)


def atmospheric_light_quadtree(img: np.ndarray, cfg: dict | None = None,
                               gray: np.ndarray | None = None) -> np.ndarray:
    """Hierarchical (quad-tree) sky search: score = mean - std, recurse on the best."""
    cfg = cfg or {}
    gray = grayscale(img) if gray is None else gray
    y0, x0, y1, x1 = 0, 0, gray.shape[0], gray.shape[1]
    min_size = int(cfg.get("min_size", 32))
    for _ in range(int(cfg.get("max_depth", 6))):
        hh, ww = y1 - y0, x1 - x0
        if min(hh, ww) <= min_size:
            break
        ym, xm = y0 + hh // 2, x0 + ww // 2
        quads = [(y0, x0, ym, xm), (y0, xm, ym, x1),
                 (ym, x0, y1, xm), (ym, xm, y1, x1)]
        best = None
        for a, b, c, d in quads:
            patch = gray[a:c, b:d]
            if patch.size == 0:
                continue
            score = float(np.mean(patch) - np.std(patch))
            if best is None or score > best[0]:
                best = (score, a, b, c, d)
        if best is None:
            break
        _, y0, x0, y1, x1 = best
    patch = img[y0:y1, x0:x1].reshape(-1, img.shape[-1])
    values = gray[y0:y1, x0:x1].reshape(-1)
    k = max(1, int(0.1 * values.size))
    top = np.argpartition(values, -k)[-k:]
    return np.clip(patch[top].mean(axis=0), 0.0, 1.0).astype(np.float32)


def estimate_airlight(img: np.ndarray, dark: np.ndarray, patch_size: int,
                      method: str = "v1", cfg: dict | None = None) -> np.ndarray:
    """Dispatch to the v1 / v2 / quadtree atmospheric-light estimator."""
    cfg = cfg or {}
    if method == "v2":
        return atmospheric_light_v2(img, dark, patch_size, cfg)
    if method == "quadtree":
        return atmospheric_light_quadtree(img, cfg.get("quadtree", {}))
    return atmospheric_light(img, dark, patch_size)


def transmission_map(
    img: np.ndarray,
    airlight: np.ndarray,
    omega: float | np.ndarray = 0.95,
    patch_size: int = 15,
    guided_radius: int = 60,
    guided_eps: float = 1e-4,
    refine: bool = True,
    t_min: float | np.ndarray = 0.05,
) -> np.ndarray:
    """t(x) = 1 - omega * dark_channel(I / A), optionally guided-filtered.

    ``omega`` and ``t_min`` may be scalars (v1 behaviour, unchanged) or
    per-pixel arrays (v2 local density maps).
    """
    a = np.maximum(airlight.astype(np.float32).reshape(1, 1, -1), 1e-3)
    normalised = np.clip(img.astype(np.float32) / a, 0.0, 1.0)
    dark = dark_channel(normalised, patch_size)
    if np.isscalar(omega):
        t = 1.0 - float(omega) * dark
    else:
        t = 1.0 - np.asarray(omega, dtype=np.float32) * dark
    t = np.clip(t, 0.0, 1.0).astype(np.float32)
    if refine and guided_radius > 0:
        t = guided_filter(grayscale(img), t, radius=int(guided_radius), eps=float(guided_eps))
    if np.isscalar(t_min):
        return np.clip(t, float(t_min), 1.0).astype(np.float32)
    t = np.maximum(t, np.asarray(t_min, dtype=np.float32))
    return np.clip(t, 0.0, 1.0).astype(np.float32)


def recover_radiance(img: np.ndarray, airlight: np.ndarray, t: np.ndarray,
                     t0: float | np.ndarray = 0.1) -> np.ndarray:
    """J = (I - A) / max(t, t0) + A.  ``t0`` may be a scalar or a map."""
    a = airlight.astype(np.float32).reshape(1, 1, -1)
    if np.isscalar(t0):
        tt = np.maximum(t, float(t0)).astype(np.float32)
    else:
        tt = np.maximum(t, np.asarray(t0, dtype=np.float32))
    out = (img.astype(np.float32) - a) / tt[..., None] + a
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def dcp_dehaze(
    img: np.ndarray,
    omega: float = 0.95,
    t0: float = 0.1,
    patch_size: int = 15,
    guided_radius: int = 60,
    guided_eps: float = 1e-4,
    refine: bool = True,
    top_percent: float = 0.1,
    return_info: bool = True,
):
    """Full fixed-parameter DCP step (no enhancement)."""
    patch_size = int(patch_size)
    if patch_size % 2 == 0:
        patch_size += 1
    dark = dark_channel(img, patch_size)
    airlight = atmospheric_light(img, dark, patch_size, top_percent)
    t = transmission_map(
        img,
        airlight,
        omega=omega,
        patch_size=patch_size,
        guided_radius=guided_radius,
        guided_eps=guided_eps,
        refine=refine,
        t_min=t0,
    )
    out = recover_radiance(img, airlight, t, t0=t0)
    if not return_info:
        return out
    info = {
        "airlight": airlight,
        "transmission": t,
        "dark_channel": dark,
        "omega": float(omega),
        "t0": float(t0),
        "patch_size": patch_size,
        "guided_radius": int(guided_radius),
        "guided_eps": float(guided_eps),
        "mean_transmission": float(np.mean(t)),
        "min_transmission": float(np.min(t)),
    }
    return out, info


def dcp_dehaze_v2(
    img: np.ndarray,
    omega: float = 0.95,
    t0: float = 0.1,
    patch_size: int = 15,
    guided_radius: int = 60,
    guided_eps: float = 1e-4,
    refine: bool = True,
    omega_map: np.ndarray | None = None,
    t0_map: np.ndarray | None = None,
    airlight_method: str = "v1",
    airlight_cfg: dict | None = None,
    sky_region: np.ndarray | None = None,
    sky_cfg: dict | None = None,
    return_info: bool = True,
):
    """v2 DCP core: optional v2 airlight, per-pixel omega/t0 maps and sky handling.

    With default arguments (method v1, no maps, no sky) this reduces exactly to
    ``dcp_dehaze`` because it calls the same scalar primitives.
    """
    patch_size = int(patch_size)
    if patch_size % 2 == 0:
        patch_size += 1
    dark = dark_channel(img, patch_size)
    airlight = estimate_airlight(img, dark, patch_size, airlight_method, airlight_cfg)
    t = transmission_map(
        img,
        airlight,
        omega=omega_map if omega_map is not None else omega,
        patch_size=patch_size,
        guided_radius=guided_radius,
        guided_eps=guided_eps,
        refine=refine,
        t_min=t0_map if t0_map is not None else t0,
    )
    if sky_region is not None and sky_cfg:
        floor = float(sky_cfg.get("t_floor", 0.35))
        t = np.where(sky_region, np.maximum(t, floor), t).astype(np.float32)
    out = recover_radiance(img, airlight, t, t0=t0_map if t0_map is not None else t0)
    if sky_region is not None and sky_cfg:
        blend = float(sky_cfg.get("blend", 0.35))
        if blend > 0.0:
            m = sky_region.astype(np.float32)[..., None]
            out = np.clip((1.0 - blend * m) * out + blend * m * img, 0.0, 1.0).astype(np.float32)
    if not return_info:
        return out
    info = {
        "airlight": airlight,
        "transmission": t,
        "dark_channel": dark,
        "omega": float(omega) if omega_map is None else float(np.mean(omega_map)),
        "t0": float(t0) if t0_map is None else float(np.mean(t0_map)),
        "patch_size": patch_size,
        "guided_radius": int(guided_radius),
        "guided_eps": float(guided_eps),
        "airlight_method": airlight_method,
        "mean_transmission": float(np.mean(t)),
        "min_transmission": float(np.min(t)),
        "omega_map": omega_map,
        "t0_map": t0_map,
        "sky_region": sky_region,
    }
    return out, info
