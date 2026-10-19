import numpy as np

from src.density import (
    DEFAULT_STATS,
    DensityEstimator,
    dark_channel,
    dark_channel_mean,
    extract_features,
    fit_normalisation,
    global_contrast,
    shannon_entropy,
    spearman_correlation,
)
from src.synthetic import apply_haze, make_depth

CFG = {
    "patch_size": 15,
    "entropy_bins": 256,
    "contrast_percentiles": [5, 95],
    "normalization": {"low_percentile": 2, "high_percentile": 98},
    "weights": {"dark_channel": 0.45, "entropy": 0.30, "contrast": 0.25},
    "features": {"dark_channel": True, "entropy": True, "contrast": True},
}


def test_dark_channel_shape_and_range(sample_image):
    dc = dark_channel(sample_image, 9)
    assert dc.shape == sample_image.shape[:2]
    assert dc.min() >= 0.0 and dc.max() <= 1.0
    assert dark_channel_mean(sample_image, 9) >= 0.0


def test_entropy_of_constant_image_is_zero():
    const = np.full((32, 32, 3), 0.5, dtype=np.float32)
    assert shannon_entropy(const) == 0.0


def test_entropy_drops_with_haze(sample_image, rng):
    depth = make_depth(rng, *sample_image.shape[:2])
    hazy, _ = apply_haze(sample_image, depth, 1.5, 0.9, noise_sigma=0.0, rng=rng)
    assert shannon_entropy(hazy) < shannon_entropy(sample_image)


def test_contrast_drops_with_haze(sample_image, rng):
    depth = make_depth(rng, *sample_image.shape[:2])
    hazy, _ = apply_haze(sample_image, depth, 1.5, 0.9, noise_sigma=0.0, rng=rng)
    assert global_contrast(hazy) < global_contrast(sample_image)


def test_score_range(sample_image):
    est = DensityEstimator(cfg=CFG, stats=DEFAULT_STATS)
    result = est.score(sample_image)
    assert 0.0 <= result["score"] <= 1.0
    assert set(result["features"]) >= {"dark_channel", "entropy", "contrast"}


def test_score_monotonic_with_beta(sample_image, rng):
    depth = make_depth(rng, *sample_image.shape[:2])
    betas = [0.2, 0.5, 0.8, 1.2, 1.6, 2.0]
    scores = []
    for beta in betas:
        hazy, _ = apply_haze(sample_image, depth, beta, 0.9, noise_sigma=0.0, rng=rng)
        est = DensityEstimator(cfg=CFG, stats=DEFAULT_STATS)
        scores.append(est.score(hazy)["score"])
    assert spearman_correlation(betas, scores) > 0.8
    # non-decreasing up to small numerical noise
    assert np.all(np.diff(scores) > -0.02)


def test_feature_ablation_mask(sample_image):
    est = DensityEstimator(cfg=CFG, stats=DEFAULT_STATS)
    full = est.score(sample_image)["score"]
    dc_only = est.score(sample_image, feature_mask={"entropy": False, "contrast": False})["score"]
    assert 0.0 <= dc_only <= 1.0
    assert full != dc_only


def test_fit_normalisation(sample_image, rng):
    rows = []
    for beta in [0.3, 0.8, 1.4]:
        depth = make_depth(rng, *sample_image.shape[:2])
        hazy, _ = apply_haze(sample_image, depth, beta, 0.9, noise_sigma=0.0, rng=rng)
        rows.append(extract_features(hazy, CFG))
    stats = fit_normalisation(rows, CFG)
    for key in ("dark_channel", "entropy", "contrast"):
        assert stats[key]["high"] > stats[key]["low"]
