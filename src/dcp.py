"""Dark Channel Prior (DCP) core: atmospheric light, transmission, recovery."""
from __future__ import annotations

import numpy as np

from .density import dark_channel, grayscale
from .guided_filter import guided_filter


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


def transmission_map(
    img: np.ndarray,
    airlight: np.ndarray,
    omega: float = 0.95,
    patch_size: int = 15,
    guided_radius: int = 60,
    guided_eps: float = 1e-4,
    refine: bool = True,
    t_min: float = 0.05,
) -> np.ndarray:
    """t(x) = 1 - omega * dark_channel(I / A), optionally guided-filtered."""
    a = np.maximum(airlight.astype(np.float32).reshape(1, 1, -1), 1e-3)
    normalised = np.clip(img.astype(np.float32) / a, 0.0, 1.0)
    dark = dark_channel(normalised, patch_size)
    t = 1.0 - float(omega) * dark
    t = np.clip(t, 0.0, 1.0).astype(np.float32)
    if refine and guided_radius > 0:
        t = guided_filter(grayscale(img), t, radius=int(guided_radius), eps=float(guided_eps))
    return np.clip(t, float(t_min), 1.0).astype(np.float32)


def recover_radiance(img: np.ndarray, airlight: np.ndarray, t: np.ndarray,
                     t0: float = 0.1) -> np.ndarray:
    """J = (I - A) / max(t, t0) + A."""
    a = airlight.astype(np.float32).reshape(1, 1, -1)
    tt = np.maximum(t, float(t0)).astype(np.float32)[..., None]
    out = (img.astype(np.float32) - a) / tt + a
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
