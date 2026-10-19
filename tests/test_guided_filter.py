import numpy as np

from src.guided_filter import guided_filter


def test_guided_filter_shape_range(sample_image):
    guide = sample_image
    src = sample_image[..., 0]
    out = guided_filter(guide, src, radius=4, eps=1e-3)
    assert out.shape == src.shape
    assert out.dtype == np.float32
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_guided_filter_identity(sample_image):
    src = sample_image[..., 0]
    out = guided_filter(sample_image, src, radius=4, eps=1e-6)
    assert np.mean(np.abs(out - src)) < 0.02


def test_guided_filter_smooths_noise(sample_image):
    rng = np.random.default_rng(0)
    noisy = np.clip(sample_image[..., 0] + rng.normal(0, 0.05, sample_image.shape[:2]), 0, 1)
    out = guided_filter(sample_image, noisy.astype(np.float32), radius=6, eps=1e-2)
    assert np.std(out) < np.std(noisy)


def test_guided_filter_rejects_shape_mismatch(sample_image):
    try:
        guided_filter(sample_image, np.zeros((10, 10), dtype=np.float32))
    except ValueError:
        return
    raise AssertionError("expected ValueError")
