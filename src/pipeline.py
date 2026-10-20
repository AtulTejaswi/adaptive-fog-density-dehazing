"""Full adaptive pipeline: density -> selector -> DCP -> enhancement."""
from __future__ import annotations

import copy
import time

import numpy as np

from .config import deep_update
from .dcp import dcp_dehaze, dcp_dehaze_v2
from .density import DensityEstimator
from .enhance import apply_enhancements
from .selector import AdaptiveSelector
from .sky import sky_mask


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
    if bool(params.get("v2", {}).get("enabled", False)):
        return dehaze_adaptive_v2(
            img, params, selector=selector, estimator=estimator, mode=mode,
            force_class=force_class, overrides=overrides, feature_mask=feature_mask,
            enhancement_switches=enhancement_switches, use_enhancement=use_enhancement,
        )
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


def dehaze_adaptive_v2(
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
    v2: dict | None = None,
) -> tuple[np.ndarray, dict]:
    """v2 pipeline: optional v2 airlight, sky handling and local density maps.

    Every upgrade is opt-in through ``params['v2']``.  With all sub-flags off
    this function reproduces ``dehaze_adaptive`` (v1) exactly; see
    ``tests/test_v2_compat.py``.
    """
    start = time.perf_counter()
    v2 = dict(v2 if v2 is not None else params.get("v2", {}))
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

    max_omega = float(params.get("dehaze", {}).get("max_omega", 0.97))
    min_t0 = float(params.get("dehaze", {}).get("min_t0", 0.05))
    omega = float(np.clip(cfg.get("omega", 0.85), 0.0, max_omega))
    t0 = float(np.clip(cfg.get("t0", 0.20), min_t0, 1.0))

    local_cfg = v2.get("local_density", {})
    use_local = bool(local_cfg.get("enabled", False))
    local_ms = 0.0
    score_map = None
    omega_map = None
    t0_map = None
    if use_local:
        local_start = time.perf_counter()
        score_map = estimator.score_map(img, local_cfg, feature_mask)
        omega_map, t0_map = selector.parameter_maps(score_map)
        blend = float(np.clip(local_cfg.get("map_blend", 1.0), 0.0, 1.0))
        if blend < 1.0:
            omega_map = ((1.0 - blend) * omega + blend * omega_map).astype(np.float32)
            t0_map = ((1.0 - blend) * t0 + blend * t0_map).astype(np.float32)
        local_ms = (time.perf_counter() - local_start) * 1000.0

    airlight_cfg = v2.get("airlight", {})
    airlight_method = str(airlight_cfg.get("method", "v1"))
    if airlight_method not in {"v1", "v2", "quadtree"}:
        airlight_method = "v1"
    sky_cfg = v2.get("sky", {})
    sky_region = sky_mask(img, sky_cfg) if sky_cfg.get("enabled", False) else None

    patch_size = int(cfg.get("patch_size", 15))
    gf = cfg.get("guided_filter", {})
    dcp_start = time.perf_counter()
    dehazed, dcp_info = dcp_dehaze_v2(
        img,
        omega=omega,
        t0=t0,
        patch_size=patch_size,
        guided_radius=int(gf.get("radius", 60)),
        guided_eps=float(gf.get("eps", 0.001)),
        omega_map=omega_map,
        t0_map=t0_map,
        airlight_method=airlight_method,
        airlight_cfg=airlight_cfg,
        sky_region=sky_region,
        sky_cfg=sky_cfg,
    )
    dcp_ms = (time.perf_counter() - dcp_start) * 1000.0

    retinex_cfg = v2.get("retinex", {})
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
        retinex_fast=bool(retinex_cfg.get("fast", False)),
        retinex_scale=float(retinex_cfg.get("scale", 0.5)),
    )
    enhance_cfg = v2.get("enhance", {})
    if use_local and score_map is not None and enhance_cfg.get("local_blend", False):
        floor = float(np.clip(enhance_cfg.get("floor", 0.30), 0.0, 1.0))
        alpha = (floor + (1.0 - floor) * score_map)[..., None]
        enhanced = np.clip((1.0 - alpha) * dehazed + alpha * enhanced, 0.0, 1.0).astype(np.float32)
        applied["local_blend"] = {"floor": floor}
    enh_ms = (time.perf_counter() - enh_start) * 1000.0

    info = {
        "method": "adaptive_v2",
        "score": density["score"],
        "features": density["features"],
        "normalised": density["normalised"],
        "class": selection["class"],
        "selector_mode": selection["mode"],
        "thresholds": selection["thresholds"],
        "params": {
            "omega": float(np.mean(omega_map)) if omega_map is not None else omega,
            "t0": float(np.mean(t0_map)) if t0_map is not None else t0,
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
        "score_map": score_map,
        "omega_map": omega_map,
        "t0_map": t0_map,
        "sky_mask": sky_region,
        "airlight_method": airlight_method,
        "v2": {"airlight": airlight_method,
               "sky": bool(sky_cfg.get("enabled", False)),
               "local_density": use_local,
               "local_enhance": bool(use_local and enhance_cfg.get("local_blend", False)),
               "retinex_fast": bool(retinex_cfg.get("fast", False))},
        "timing_ms": {
            "density": density_ms,
            "local_density": local_ms,
            "dcp": dcp_ms,
            "enhance": enh_ms,
            "total": (time.perf_counter() - start) * 1000.0,
        },
    }
    return enhanced, info
