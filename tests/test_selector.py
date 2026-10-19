import numpy as np

from src.config import load_params
from src.selector import AdaptiveSelector, train_classifier


def test_thresholds_and_classes():
    params = load_params()
    selector = AdaptiveSelector(params, calibration={"thresholds": {"t1": 0.3, "t2": 0.7}})
    assert selector.classify(0.1) == "light"
    assert selector.classify(0.5) == "moderate"
    assert selector.classify(0.9) == "heavy"


def test_select_returns_params():
    params = load_params()
    selector = AdaptiveSelector(params, calibration={"thresholds": {"t1": 0.3, "t2": 0.7}})
    result = selector.select(0.8)
    assert result["class"] == "heavy"
    assert "omega" in result["params"]
    assert "t0" in result["params"]
    assert result["params"]["omega"] > 0.0


def test_continuous_mode_is_monotone():
    params = load_params()
    selector = AdaptiveSelector(params, calibration={"thresholds": {"t1": 0.3, "t2": 0.7}},
                                mode="continuous")
    low = selector.select(0.1)["params"]
    high = selector.select(0.9)["params"]
    assert low["omega"] <= high["omega"]
    assert low["t0"] >= high["t0"]
    assert low["retinex"]["strength"] >= high["retinex"]["strength"]


def test_params_for_class_has_enhancement_keys():
    params = load_params()
    selector = AdaptiveSelector(params, calibration={"thresholds": {"t1": 0.3, "t2": 0.7}})
    for label in ("light", "moderate", "heavy"):
        cfg = selector.params_for_class(label)
        assert {"omega", "t0", "patch_size", "guided_filter", "clahe", "retinex", "gray_world"} <= set(cfg)


def test_classifier_training(tmp_path, sample_image):
    from src.density import DEFAULT_STATS, DensityEstimator, extract_features

    rng = np.random.default_rng(0)
    params = load_params()
    params["paths"]["selector_classifier"] = str(tmp_path / "clf.joblib")
    features, labels = [], []
    for i in range(60):
        beta = [0.3, 0.8, 1.4][i % 3]
        noisy = np.clip(sample_image + rng.normal(0, 0.02, sample_image.shape), 0, 1)
        from src.synthetic import apply_haze, make_depth

        depth = make_depth(rng, *sample_image.shape[:2])
        hazy, _ = apply_haze(noisy.astype(np.float32), depth, beta, 0.9, noise_sigma=0.0, rng=rng)
        est = DensityEstimator(cfg=params["density"], stats=DEFAULT_STATS)
        info = est.score(hazy)
        features.append([info["normalised"]["dark_channel"], info["normalised"]["entropy"],
                         info["normalised"]["contrast"]])
        labels.append(["light", "moderate", "heavy"][i % 3])
    result = train_classifier(np.asarray(features), labels, params)
    assert 0.0 <= result["accuracy"] <= 1.0
    assert (tmp_path / "clf.joblib").exists()
