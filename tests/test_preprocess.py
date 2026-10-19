import numpy as np

from src.preprocess import preprocess_array, preprocess_image, resize_long_side


def test_resize_keeps_aspect():
    img = np.random.default_rng(0).random((100, 200, 3)).astype(np.float32)
    out = resize_long_side(img, 80)
    assert out.shape == (40, 80, 3)


def test_preprocess_shape_dtype_range(sample_image):
    params = {"preprocess": {"resize_long_side": 64,
                             "denoise": {"enabled": True, "method": "bilateral",
                                         "diameter": 5, "sigma_color": 20, "sigma_space": 20}}}
    out = preprocess_array(sample_image, params)
    assert out.ndim == 3 and out.shape[-1] == 3
    assert out.dtype == np.float32
    assert out.min() >= 0.0 and out.max() <= 1.0
    assert max(out.shape[:2]) == 64


def test_preprocess_accepts_uint8(sample_image):
    out = preprocess_array((sample_image * 255).astype(np.uint8), {"preprocess": {}})
    assert out.dtype == np.float32
    assert 0.0 <= out.min() <= out.max() <= 1.0


def test_denoise_can_be_disabled(sample_image):
    params = {"preprocess": {"resize_long_side": 0, "denoise": {"enabled": False}}}
    out = preprocess_array(sample_image, params)
    assert np.allclose(out, sample_image, atol=1e-6)
