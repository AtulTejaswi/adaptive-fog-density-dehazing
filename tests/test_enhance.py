import numpy as np

from src.density import rms_contrast
from src.enhance import (
    apply_clahe,
    apply_enhancements,
    apply_gray_world,
    apply_retinex,
)
from src.metrics import color_cast


def test_clahe_shape_range(sample_image):
    out = apply_clahe(sample_image, clip_limit=2.0, tile_grid_size=(8, 8))
    assert out.shape == sample_image.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert rms_contrast(out) >= rms_contrast(sample_image) - 1e-3


def test_retinex_strength_zero_is_identity(sample_image):
    out = apply_retinex(sample_image, strength=0.0)
    assert np.allclose(out, sample_image, atol=1e-6)


def test_retinex_shape_range(sample_image):
    out = apply_retinex(sample_image, strength=0.5, method="msr", sigmas=[5, 15])
    assert out.shape == sample_image.shape
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_gray_world_reduces_cast(sample_image):
    cast = np.clip(sample_image * np.array([1.25, 0.95, 0.8], dtype=np.float32), 0, 1)
    before = color_cast(cast)
    out = apply_gray_world(cast, strength=1.0, max_gain=1.5)
    assert color_cast(out) < before


def test_enhancement_switches(sample_image):
    class_cfg = {
        "clahe": {"enabled": True, "clip_limit": 2.0},
        "retinex": {"enabled": True, "strength": 0.4, "sigmas": [5, 15]},
        "gray_world": {"enabled": True, "strength": 0.5},
    }
    defaults = {}
    out, applied = apply_enhancements(
        sample_image, class_cfg, defaults, ["retinex", "clahe", "gray_world"],
        switches={"retinex": False},
    )
    assert set(applied) == {"clahe", "gray_world"}
    assert out.shape == sample_image.shape
    assert out.min() >= 0.0 and out.max() <= 1.0
