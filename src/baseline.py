"""Fixed-parameter DCP baseline (D-02).

omega=0.95, t0=0.10, patch=15, guided filter r=60 / eps=1e-4, no enhancement.
This is the comparison method for every table in the report.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .dcp import dcp_dehaze
from .preprocess import preprocess_array, preprocess_image


def dehaze_baseline(img: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    """Run the fixed DCP baseline on an already-preprocessed RGB image."""
    cfg = params.get("dehaze", {}).get("baseline", {})
    gf = cfg.get("guided_filter", {})
    out, info = dcp_dehaze(
        img,
        omega=float(cfg.get("omega", 0.95)),
        t0=float(cfg.get("t0", 0.10)),
        patch_size=int(cfg.get("patch_size", 15)),
        guided_radius=int(gf.get("radius", 60)),
        guided_eps=float(gf.get("eps", 1e-4)),
    )
    info["method"] = "baseline"
    return out, info


def baseline_from_path(path: str | Path, params: dict) -> tuple[np.ndarray, dict]:
    img = preprocess_image(path, params)
    return dehaze_baseline(img, params)


def baseline_from_array(img: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    return dehaze_baseline(preprocess_array(img, params), params)
