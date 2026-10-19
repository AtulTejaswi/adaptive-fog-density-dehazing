import numpy as np

from src.density import rms_contrast
from src.synthetic import apply_haze, beta_to_class, make_depth


def test_beta_to_class():
    assert beta_to_class(0.2) == "light"
    assert beta_to_class(0.8) == "moderate"
    assert beta_to_class(1.5) == "heavy"


def test_depth_range(sample_image, rng):
    depth = make_depth(rng, *sample_image.shape[:2])
    assert depth.shape == sample_image.shape[:2]
    assert depth.min() >= 0.0 and depth.max() <= 1.5


def test_haze_model_range_and_contrast(sample_image, rng):
    depth = make_depth(rng, *sample_image.shape[:2])
    hazy, t = apply_haze(sample_image, depth, 1.2, 0.9, noise_sigma=0.0, rng=rng)
    assert hazy.shape == sample_image.shape
    assert hazy.min() >= 0.0 and hazy.max() <= 1.0
    assert t.min() > 0.0 and t.max() <= 1.0
    assert rms_contrast(hazy) < rms_contrast(sample_image)
