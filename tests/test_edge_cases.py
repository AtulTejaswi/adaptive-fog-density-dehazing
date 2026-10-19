"""Edge-case robustness tests for preprocessing, dehazing and metrics.

Covers: tiny/1-pixel images, very large images, grayscale (2D and HxWx1),
RGBA PNGs, pure white, pure black, a haze-free image, corrupt/missing files,
determinism, and output range/dtype/shape guarantees.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from src.baseline import dehaze_baseline
from src.config import load_params
from src.io_utils import read_rgb
from src.metrics import no_reference_metrics
from src.pipeline import dehaze_adaptive
from src.preprocess import preprocess_array

PARAMS = load_params()


def _run(img: np.ndarray):
    hazy = preprocess_array(img, PARAMS)
    out, info = dehaze_adaptive(hazy, PARAMS)
    base, _ = dehaze_baseline(hazy, PARAMS)
    return hazy, out, base, info


def _assert_clean(out: np.ndarray, shape: tuple) -> None:
    assert out.shape == shape, (out.shape, shape)
    assert out.dtype == np.float32
    assert np.isfinite(out).all()
    assert float(out.min()) >= 0.0 and float(out.max()) <= 1.0
    score = no_reference_metrics(np.zeros_like(out) + 0.5, out)
    assert all(np.isfinite(v) for v in score.values() if isinstance(v, float))


def test_one_pixel_image() -> None:
    _, out, base, _ = _run(np.full((1, 1, 3), 0.5, np.float32))
    _assert_clean(out, out.shape)
    _assert_clean(base, base.shape)


def test_tiny_non_square_image() -> None:
    _, out, _, _ = _run(np.full((3, 7, 3), 0.4, np.float32))
    _assert_clean(out, out.shape)


def test_very_large_image_is_resized_and_clean() -> None:
    rng = np.random.default_rng(0)
    big = rng.random((2000, 3000, 3), dtype=np.float32)
    hazy, out, _, _ = _run(big)
    assert max(hazy.shape[:2]) == 640
    _assert_clean(out, hazy.shape)


def test_grayscale_2d() -> None:
    hazy, out, _, _ = _run(np.full((60, 90), 0.5, np.float32))
    assert hazy.shape[-1] == 3
    _assert_clean(out, hazy.shape)


def test_single_channel_3d() -> None:
    hazy, out, _, _ = _run(np.full((60, 90, 1), 0.5, np.float32))
    assert hazy.shape[-1] == 3
    _assert_clean(out, hazy.shape)


def test_uint8_input() -> None:
    hazy, out, _, _ = _run((np.random.default_rng(1).random((80, 100, 3)) * 255).astype(np.uint8))
    assert hazy.dtype == np.float32
    _assert_clean(out, hazy.shape)


def test_grayscale_png_file(tmp_path) -> None:
    path = tmp_path / "gray.png"
    cv2.imwrite(str(path), np.full((48, 64), 128, np.uint8))
    img = read_rgb(path)
    assert img.shape == (48, 64, 3)
    _, out, _, _ = _run(img)
    _assert_clean(out, out.shape)


def test_rgba_png_file(tmp_path) -> None:
    path = tmp_path / "rgba.png"
    rgba = np.zeros((40, 50, 4), np.uint8)
    rgba[..., :3] = 90
    rgba[..., 3] = 255
    cv2.imwrite(str(path), cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA))
    img = read_rgb(path)
    assert img.shape == (40, 50, 3)
    _, out, _, _ = _run(img)
    _assert_clean(out, out.shape)


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_pure_black_and_white(value: float) -> None:
    _, out, base, info = _run(np.full((64, 64, 3), value, np.float32))
    _assert_clean(out, out.shape)
    _assert_clean(base, base.shape)
    assert 0.0 <= float(info["score"]) <= 1.0


def test_haze_free_image() -> None:
    rng = np.random.default_rng(3)
    clean = np.clip(rng.random((120, 160, 3), dtype=np.float32) * 0.6 + 0.2, 0, 1)
    _, out, _, info = _run(clean)
    _assert_clean(out, out.shape)
    assert info["class"] in {"light", "moderate", "heavy"}


def test_determinism() -> None:
    rng = np.random.default_rng(7)
    img = rng.random((100, 140, 3), dtype=np.float32)
    hazy = preprocess_array(img, PARAMS)
    a1, _ = dehaze_adaptive(hazy, PARAMS)
    a2, _ = dehaze_adaptive(hazy, PARAMS)
    b1, _ = dehaze_baseline(hazy, PARAMS)
    b2, _ = dehaze_baseline(hazy, PARAMS)
    assert np.array_equal(a1, a2)
    assert np.array_equal(b1, b2)


def test_corrupt_file_raises_clear_error(tmp_path) -> None:
    path = tmp_path / "broken.png"
    path.write_bytes(b"this is not a real image")
    with pytest.raises(ValueError, match="Cannot read image"):
        read_rgb(path)


def test_missing_file_raises(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        read_rgb(tmp_path / "nope.png")


def test_bad_shape_raises() -> None:
    with pytest.raises(ValueError, match="Expected a 2D grayscale"):
        preprocess_array(np.zeros((10, 10, 2), np.float32), PARAMS)
