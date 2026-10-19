"""Full adaptive pipeline: density -> selector -> DCP -> enhancement."""
from __future__ import annotations

import copy
import time

import numpy as np

from .config import deep_update
from .dcp import dcp_dehaze
from .density import DensityEstimator
from .enhance import apply_enhancements
from .selector import AdaptiveSelector


def dehaze_adaptive(
    img: np.ndarray,
    params: dict,
    selector: AdaptiveSelector | None = None,
    estimator: DensityEstimator | None = None,
    mode: str | None = None,
    force_class: str | None = None,
    overrides: dict | None = None,
    feature_mask: dict | None = None,
    enhancement_switches: dict[str, bool] | None = None,
    use_enhancement: bool = True,
) -> tuple[np.ndarray, dict]:
    """Dehaze one preprocessed RGB float image.

    Parameters
    ----------
    force_class : optional class override (used by the parameter tuner only)
    overrides   : parameter overrides (tuner / ablations)
    feature_mask: density-feature ablation, e.g. {"entropy": False}
    enhancement_switches: per-step ablation switches
    """
    start = time.perf_counter()
    estimator = estimator or DensityEstimator.from_config(params)
    density = estimator.score(img, feature_mask=feature_mask)
    density_ms = (time.perf_counter() - start) * 1000.0

    selector = selector or AdaptiveSelector(params, mode=mode)
    selection = selector.select(density["score"], density["normalised"])
    if force_class is not None:
        selection["class"] = force_class
        selection["params"] = selector.params_for_class(force_class)
    cfg = copy.deepcopy(selection["params"])
    if overrides:
        deep_update(cfg, overrides)
    if mode == "continuous" and overrides:
        # keep continuous base but respect explicit tuner overrides
        pass

    omega = float(np.clip(cfg.get("omega", 0.85), 0.0, float(params.get("dehaze", {}).get("max_omega", 0.97))))
    t0 = float(np.clip(cfg.get("t0", 0.20), float(params.get("dehaze", {}).get("min_t0", 0.05)), 1.0))
    patch_size = int(cfg.get("patch_size", 15))
    gf = cfg.get("guided_filter", {})
    dcp_start = time.perf_counter()
    dehazed, dcp_info = dcp_dehaze(
        img,
        omega=omega,
        t0=t0,
        patch_size=patch_size,
        guided_radius=int(gf.get("radius", 60)),
        guided_eps=float(gf.get("eps", 0.001)),
    )
    dcp_ms = (time.perf_counter() - dcp_start) * 1000.0

    enh_start = time.perf_counter()
    switches = dict(enhancement_switches or {})
    if not use_enhancement:
        switches = {"retinex": False, "clahe": False, "gray_world": False}
    enhanced, applied = apply_enhancements(
        dehazed,
        class_cfg=cfg,
        defaults=params.get("dehaze", {}).get("defaults", {}),
        order=params.get("dehaze", {}).get("enhancement_order", ["retinex", "clahe", "gray_world"]),
        switches=switches,
    )
    enh_ms = (time.perf_counter() - enh_start) * 1000.0

    info = {
        "method": "adaptive",
        "score": density["score"],
        "features": density["features"],
        "normalised": density["normalised"],
        "class": selection["class"],
        "selector_mode": selection["mode"],
        "thresholds": selection["thresholds"],
        "params": {
            "omega": omega,
            "t0": t0,
            "patch_size": patch_size,
            "guided_filter": {"radius": int(gf.get("radius", 60)),
                              "eps": float(gf.get("eps", 0.001))},
            "clahe": cfg.get("clahe", {}),
            "retinex": cfg.get("retinex", {}),
            "gray_world": cfg.get("gray_world", {}),
        },
        "applied_enhancements": applied,
        "airlight": dcp_info["airlight"].tolist(),
        "transmission": dcp_info["transmission"],
        "mean_transmission": dcp_info["mean_transmission"],
        "min_transmission": dcp_info["min_transmission"],
        "timing_ms": {
            "density": density_ms,
            "dcp": dcp_ms,
            "enhance": enh_ms,
            "total": (time.perf_counter() - start) * 1000.0,
        },
    }
    return enhanced, info
