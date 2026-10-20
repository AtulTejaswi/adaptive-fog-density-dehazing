"""Fixed-parameter DCP baseline (D-02).

omega=0.95, t0=0.10, patch=15, guided filter r=60 / eps=1e-4, no enhancement.
This is the comparison method for every table in the report.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .dcp import atmospheric_light, dcp_dehaze, recover_radiance, transmission_map
from .density import dark_channel, grayscale
from .guided_filter import guided_filter
from .preprocess import preprocess_array, preprocess_image

# Published Color Attenuation Prior coefficients (Zhu et al., 2015).
CAP_THETA = (0.121779, 0.959710, -0.780245)


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


def dehaze_cap(img: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    """Color Attenuation Prior baseline (Zhu et al., 2015).

    depth(x) = theta0 + theta1 * V(x) + theta2 * S(x), t = exp(-beta * depth).
    The published theta coefficients are used; beta/t0 are fixed config values
    (never fitted on the test splits).
    """
    cfg = params.get("baselines", {}).get("cap", {})
    beta = float(cfg.get("beta", 1.0))
    t0 = float(cfg.get("t0", 0.10))
    value = img.max(axis=2)
    minimum = img.min(axis=2)
    saturation = (value - minimum) / (value + 1e-6)
    depth = CAP_THETA[0] + CAP_THETA[1] * value + CAP_THETA[2] * saturation
    depth = np.clip(depth, 0.0, None).astype(np.float32)
    t = np.exp(-beta * depth).astype(np.float32)

    flat = depth.reshape(-1)
    n = max(1, int(flat.size * 0.001))
    idx = np.argpartition(flat, -n)[-n:]
    airlight = np.clip(img.reshape(-1, img.shape[-1])[idx].mean(axis=0), 0.0, 1.0)
    out = recover_radiance(img, airlight.astype(np.float32), t, t0=t0)
    info = {"method": "cap", "airlight": airlight, "transmission": t, "t0": t0,
            "beta": beta, "depth": depth}
    return out, info


def dehaze_bccr(img: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    """Boundary-constrained DCP baseline (simplified Meng et al., 2013).

    The dark-channel transmission is projected onto the physical boundary
    constraint 0 <= J <= 1, then refined with a guided filter (contextual
    regularisation).  The full L1 contextual solver is not reproduced.
    """
    cfg = params.get("baselines", {}).get("bccr", {})
    omega = float(cfg.get("omega", 0.95))
    t0 = float(cfg.get("t0", 0.10))
    patch = int(cfg.get("patch_size", 15))
    gf = cfg.get("guided_filter", {})
    radius = int(gf.get("radius", 60))
    eps = float(gf.get("eps", 1e-4))

    dark = dark_channel(img, patch)
    airlight = atmospheric_light(img, dark, patch)
    t = transmission_map(img, airlight, omega=omega, patch_size=patch,
                         guided_radius=0, refine=False, t_min=t0)

    a = np.maximum(airlight.astype(np.float32).reshape(1, 1, -1), 1e-3)
    bright_side = (img - a) / np.maximum(1.0 - a, 1e-3)
    dark_side = (a - img) / a
    lower = np.where(img > a, bright_side, dark_side).max(axis=2)
    lower = np.clip(lower, 0.0, 1.0).astype(np.float32)
    t = np.maximum(t, lower)
    if radius > 0:
        t = guided_filter(grayscale(img), t, radius=radius, eps=eps)
    t = np.clip(t, t0, 1.0).astype(np.float32)
    out = recover_radiance(img, airlight, t, t0=t0)
    info = {"method": "bccr", "airlight": airlight, "transmission": t, "t0": t0,
            "omega": omega}
    return out, info


def run(name: str, img: np.ndarray, params: dict) -> tuple[np.ndarray, dict]:
    """Common baseline interface: dcp | cap | bccr | adaptive (v1) | v2."""
    key = name.lower()
    if key in {"dcp", "baseline"}:
        return dehaze_baseline(img, params)
    if key == "cap":
        return dehaze_cap(img, params)
    if key == "bccr":
        return dehaze_bccr(img, params)
    if key in {"adaptive", "v1"}:
        from .pipeline import dehaze_adaptive
        return dehaze_adaptive(img, params)
    if key == "v2":
        from .pipeline import dehaze_adaptive_v2
        return dehaze_adaptive_v2(img, params)
    raise ValueError(f"Unknown method: {name}")


BASELINE_NAMES = ("dcp", "cap", "bccr")
