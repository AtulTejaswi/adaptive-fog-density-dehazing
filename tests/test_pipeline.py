import numpy as np

from src.baseline import dehaze_baseline
from src.config import load_params
from src.density import rms_contrast
from src.pipeline import dehaze_adaptive


def test_baseline_output(hazy_pair):
    params = load_params()
    out, info = dehaze_baseline(hazy_pair["hazy"], params)
    assert out.shape == hazy_pair["hazy"].shape
    assert out.dtype == np.float32
    assert 0.0 <= out.min() <= out.max() <= 1.0
    assert info["method"] == "baseline"
    assert rms_contrast(out) > rms_contrast(hazy_pair["hazy"])


def test_adaptive_info(hazy_pair):
    params = load_params()
    out, info = dehaze_adaptive(hazy_pair["hazy"], params)
    assert out.shape == hazy_pair["hazy"].shape
    assert 0.0 <= info["score"] <= 1.0
    assert info["class"] in {"light", "moderate", "heavy"}
    assert {"density", "dcp", "enhance", "total"} <= set(info["timing_ms"])
    assert info["transmission"].shape == out.shape[:2]
    assert len(info["airlight"]) == 3


def test_adaptive_no_enhancement(hazy_pair):
    params = load_params()
    out, info = dehaze_adaptive(hazy_pair["hazy"], params, use_enhancement=False)
    assert info["applied_enhancements"] == {}
    assert out.shape == hazy_pair["hazy"].shape


def test_adaptive_force_class(hazy_pair):
    params = load_params()
    for label in ("light", "moderate", "heavy"):
        out, info = dehaze_adaptive(hazy_pair["hazy"], params, force_class=label)
        assert info["class"] == label
        assert out.shape == hazy_pair["hazy"].shape


def test_adaptive_feature_mask(hazy_pair):
    params = load_params()
    _, full = dehaze_adaptive(hazy_pair["hazy"], params)
    _, dc_only = dehaze_adaptive(hazy_pair["hazy"], params,
                                 feature_mask={"entropy": False, "contrast": False})
    assert 0.0 <= dc_only["score"] <= 1.0
    assert full["score"] != dc_only["score"]


def test_selector_modes(hazy_pair):
    params = load_params()
    for mode in ("three_bin", "continuous"):
        _, info = dehaze_adaptive(hazy_pair["hazy"], params, mode=mode)
        assert info["selector_mode"] == mode
