"""Tests for the v2 features: airlight, sky, local density, baselines, metrics."""
from __future__ import annotations

import numpy as np

from src.baseline import BASELINE_NAMES, dehaze_bccr, dehaze_cap, run
from src.config import load_params
from src.dcp import atmospheric_light_quadtree, atmospheric_light_v2
from src.density import DensityEstimator, local_feature_maps
from src.metrics import (
    ciede2000,
    evaluate_pair_v2,
    fade_fog_density,
    fit_niqe_model,
    niqe,
    niqe_features,
)
from src.pipeline import dehaze_adaptive_v2
from src.selector import AdaptiveSelector
from src.sky import sky_mask


def _v2_params() -> dict:
    params = load_params()
    params["v2"]["enabled"] = True
    params["v2"]["airlight"]["method"] = "v2"
    params["v2"]["sky"]["enabled"] = True
    params["v2"]["local_density"]["enabled"] = True
    params["v2"]["enhance"]["local_blend"] = True
    params["v2"]["retinex"]["fast"] = True
    return params


def test_airlight_v2_range_and_determinism(hazy_pair):
    a1 = atmospheric_light_v2(hazy_pair["hazy"])
    a2 = atmospheric_light_v2(hazy_pair["hazy"])
    assert a1.shape == (3,)
    assert np.all(a1 >= 0.0) and np.all(a1 <= 1.0)
    assert np.array_equal(a1, a2)


def test_airlight_v2_falls_back_on_flat_image():
    flat = np.full((48, 64, 3), 0.5, dtype=np.float32)
    out = atmospheric_light_v2(flat)
    assert out.shape == (3,)
    assert np.allclose(out, 0.5, atol=1e-6)


def test_quadtree_airlight_range(hazy_pair):
    out = atmospheric_light_quadtree(hazy_pair["hazy"])
    assert out.shape == (3,)
    assert np.all(out >= 0.0) and np.all(out <= 1.0)


def test_sky_mask_bright_smooth_region():
    image = np.zeros((80, 100, 3), dtype=np.float32)
    image[:38] = 0.96
    image[38:] = 0.12
    image[50:60, 10:30] = 0.5
    mask = sky_mask(image, {"brightness_threshold": 0.80, "gradient_threshold": 0.04,
                            "min_area_fraction": 0.05})
    assert mask.dtype == bool
    assert mask.shape == (80, 100)
    assert mask[:30].mean() > 0.5
    assert mask[60:].mean() < 0.1


def test_local_feature_maps(hazy_pair):
    maps = local_feature_maps(hazy_pair["hazy"], {"window": 21}, {"patch_size": 15})
    for key in ("dark_channel", "entropy", "contrast"):
        assert key in maps
        assert maps[key].shape == hazy_pair["hazy"].shape[:2]
        assert np.all(np.isfinite(maps[key]))
        assert maps[key].min() >= -1e-6


def test_score_map_range_and_determinism(hazy_pair):
    estimator = DensityEstimator.from_config(load_params())
    s1 = estimator.score_map(hazy_pair["hazy"])
    s2 = estimator.score_map(hazy_pair["hazy"])
    assert s1.shape == hazy_pair["hazy"].shape[:2]
    assert np.all(s1 >= 0.0) and np.all(s1 <= 1.0)
    assert np.array_equal(s1, s2)


def test_parameter_maps_are_monotone():
    params = load_params()
    selector = AdaptiveSelector(params)
    scores = np.linspace(0.0, 1.0, 101, dtype=np.float32).reshape(1, -1)
    omega, t0 = selector.parameter_maps(scores)
    assert omega.shape == scores.shape and t0.shape == scores.shape
    assert np.all(np.diff(omega[0]) >= -1e-6)
    assert np.all(np.diff(t0[0]) <= 1e-6)
    bounds = params["v2"]["local_density"]["omega_bounds"]
    assert omega.min() >= bounds[0] - 1e-6 and omega.max() <= bounds[1] + 1e-6


def test_cap_bccr_and_dispatch(hazy_pair):
    params = load_params()
    for name in BASELINE_NAMES:
        out1, info = run(name, hazy_pair["hazy"], params)
        out2, _ = run(name, hazy_pair["hazy"], params)
        assert out1.shape == hazy_pair["hazy"].shape
        assert out1.dtype == np.float32
        assert 0.0 <= out1.min() and out1.max() <= 1.0
        assert np.array_equal(out1, out2)
        assert info["method"] in {name, "baseline"}
    assert dehaze_cap(hazy_pair["hazy"], params)[0].shape == hazy_pair["hazy"].shape
    assert dehaze_bccr(hazy_pair["hazy"], params)[0].shape == hazy_pair["hazy"].shape


def test_ciede2000_zero_for_identical(hazy_pair):
    assert ciede2000(hazy_pair["hazy"], hazy_pair["hazy"]) < 1e-6


def test_fade_range(hazy_pair):
    value = fade_fog_density(hazy_pair["hazy"], load_params())
    assert 0.0 <= value <= 1.0


def test_niqe_model_and_distance(hazy_pair):
    model = fit_niqe_model([hazy_pair["clear"], np.clip(hazy_pair["clear"] * 0.9, 0, 1)])
    features = niqe_features(hazy_pair["hazy"])
    assert features.shape == (20,)
    assert all(np.isfinite(features))
    value = niqe(hazy_pair["out"] if "out" in hazy_pair else hazy_pair["hazy"], model)
    assert np.isfinite(value) and value >= 0.0


def test_evaluate_pair_v2_keys(hazy_pair):
    model = fit_niqe_model([hazy_pair["clear"], np.clip(hazy_pair["clear"] * 0.9, 0, 1)])
    output = np.clip(hazy_pair["clear"] * 0.9, 0.0, 1.0)
    metrics = evaluate_pair_v2(hazy_pair["clear"], hazy_pair["hazy"], output, model)
    for key in ("psnr", "ssim", "ciede2000", "niqe_out", "fade_in", "fade_out"):
        assert key in metrics
        assert np.isfinite(metrics[key])


def test_v2_pipeline_runs_all_features(hazy_pair):
    image = hazy_pair["hazy"]
    out, info = dehaze_adaptive_v2(image, _v2_params())
    assert out.shape == image.shape
    assert out.dtype == np.float32
    assert 0.0 <= out.min() and out.max() <= 1.0
    assert info["method"] == "adaptive_v2"
    assert info["score_map"].shape == image.shape[:2]
    assert info["omega_map"].shape == image.shape[:2]
    assert info["t0_map"].shape == image.shape[:2]
    assert info["sky_mask"].dtype == bool
    assert info["v2"]["local_density"] is True
