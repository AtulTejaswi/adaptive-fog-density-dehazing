"""Stage 1: acquisition and preprocessing.

Load -> resize (long side from config) -> light denoise -> float32 RGB [0, 1].
The same deterministic preprocessing is used by the baseline and the adaptive
pipeline so the comparison is fair.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .io_utils import read_rgb


def resize_long_side(img: np.ndarray, long_side: int) -> np.ndarray:
    """Resize so max(h, w) == long_side, preserving aspect ratio."""
    if long_side is None or long_side <= 0:
        return img
    h, w = img.shape[:2]
    scale = float(long_side) / float(max(h, w))
    if abs(scale - 1.0) < 1e-9:
        return img
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    interp = cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC
    return cv2.resize(img, (new_w, new_h), interpolation=interp)


def denoise(img: np.ndarray, cfg: dict) -> np.ndarray:
    """Optional light edge-preserving denoise (bilateral by default)."""
    if not cfg.get("enabled", False):
        return img
    method = cfg.get("method", "bilateral")
    if method == "none":
        return img
    if method != "bilateral":
        raise ValueError(f"Unknown denoise method: {method}")
    d = int(cfg.get("diameter", 5))
    if d % 2 == 0:
        d += 1
    out = cv2.bilateralFilter(
        img.astype(np.float32),
        d=d,
        sigmaColor=float(cfg.get("sigma_color", 20)),
        sigmaSpace=float(cfg.get("sigma_space", 20)),
        borderType=cv2.BORDER_REFLECT,
    )
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def preprocess_array(img: np.ndarray, params: dict) -> np.ndarray:
    """Preprocess an RGB float or uint8 array."""
    if img.dtype == np.uint8:
        img = img.astype(np.float32) / 255.0
    img = np.clip(img.astype(np.float32), 0.0, 1.0)
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    if img.shape[-1] == 4:
        img = img[..., :3]
    pp = params.get("preprocess", {})
    img = resize_long_side(img, int(pp.get("resize_long_side", 640)))
    img = np.clip(img, 0.0, 1.0)
    img = denoise(img, pp.get("denoise", {}))
    return np.ascontiguousarray(img, dtype=np.float32)


def preprocess_image(path: str | Path, params: dict) -> np.ndarray:
    return preprocess_array(read_rgb(path), params)
