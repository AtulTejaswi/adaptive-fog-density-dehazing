"""Edge-preserving guided filter (He et al., 2010), box-filter implementation.

Implemented locally so OpenCV-contrib is not required.
"""
from __future__ import annotations

import cv2
import numpy as np


def _box_filter(img: np.ndarray, radius: int) -> np.ndarray:
    radius = max(0, int(radius))
    ksize = (2 * radius + 1, 2 * radius + 1)
    return cv2.boxFilter(
        img, ddepth=-1, ksize=ksize, normalize=True, borderType=cv2.BORDER_REFLECT
    )


def guided_filter(
    guide: np.ndarray,
    src: np.ndarray,
    radius: int = 40,
    eps: float = 1e-3,
) -> np.ndarray:
    """Filter ``src`` using ``guide`` as structure.

    Parameters
    ----------
    guide : HxW or HxWxC float array in [0, 1]
    src   : HxW float array (e.g. a transmission map)
    radius: box-filter radius in pixels
    eps   : regularisation (larger -> smoother)
    """
    guide = guide.astype(np.float32)
    src = src.astype(np.float32)
    if guide.ndim == 3:
        guide = cv2.cvtColor(guide, cv2.COLOR_RGB2GRAY)
    if guide.shape[:2] != src.shape[:2]:
        raise ValueError("guide and src must have the same spatial shape")

    mean_i = _box_filter(guide, radius)
    mean_p = _box_filter(src, radius)
    corr_ii = _box_filter(guide * guide, radius)
    corr_ip = _box_filter(guide * src, radius)

    var_i = corr_ii - mean_i * mean_i
    cov_ip = corr_ip - mean_i * mean_p
    a = cov_ip / (var_i + float(eps))
    b = mean_p - a * mean_i

    mean_a = _box_filter(a, radius)
    mean_b = _box_filter(b, radius)
    out = mean_a * guide + mean_b
    return np.clip(out, 0.0, 1.0).astype(np.float32)
