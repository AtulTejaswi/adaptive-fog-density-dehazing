"""Sky / white-object mask used by the v2 airlight and transmission handling.

A sky (or large white object) region is bright, smooth and spatially large.
Inside such regions the dark-channel prior under-estimates transmission, so
amplifying detail there mostly amplifies noise and colour artefacts.  v2 can
floor the transmission and blend back toward the input in these regions.

The mask is deliberately conservative (bright + low gradient + large connected
component) and is disabled by default (`v2.sky.enabled: false`).
"""
from __future__ import annotations

import cv2
import numpy as np

from .density import grayscale


def gradient_magnitude(img: np.ndarray) -> np.ndarray:
    """Sobel gradient magnitude normalised to ~[0, 1] (a 0->1 step maps to 1)."""
    gray = grayscale(img).astype(np.float32)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    return np.clip(np.hypot(gx, gy) / 4.0, 0.0, 1.0).astype(np.float32)


def sky_mask(img: np.ndarray, cfg: dict | None = None) -> np.ndarray:
    """Boolean mask of bright, low-gradient, large connected regions."""
    cfg = cfg or {}
    gray = grayscale(img)
    bright = gray >= float(cfg.get("brightness_threshold", 0.80))
    smooth = gradient_magnitude(img) <= float(cfg.get("gradient_threshold", 0.04))
    mask = (bright & smooth).astype(np.uint8)

    k = int(cfg.get("morph_kernel", 5))
    if k > 1:
        kernel = np.ones((k, k), dtype=np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    h, w = mask.shape[:2]
    min_area = max(1, int(float(cfg.get("min_area_fraction", 0.02)) * h * w))
    num, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    if num <= 1:
        return np.zeros((h, w), dtype=bool)
    keep_labels = np.nonzero(stats[1:, cv2.CC_STAT_AREA] >= min_area)[0] + 1
    if keep_labels.size == 0:
        return np.zeros((h, w), dtype=bool)
    return np.isin(labels, keep_labels)
