import numpy as np
import pytest

from src.metrics import (
    color_cast,
    colorfulness,
    edge_energy,
    evaluate_pair,
    no_reference_metrics,
    paired_test,
    psnr,
    ssim,
    summarize,
)


def test_psnr_ssim_identical(sample_image):
    assert psnr(sample_image, sample_image) == float("inf")
    assert abs(ssim(sample_image, sample_image) - 1.0) < 1e-6


def test_psnr_decreases_with_noise(sample_image, rng):
    noisy = np.clip(sample_image + rng.normal(0, 0.05, sample_image.shape), 0, 1)
    assert psnr(sample_image, noisy.astype(np.float32)) < 35.0
    assert ssim(sample_image, noisy.astype(np.float32)) < 0.99


def test_metrics_ranges(hazy_pair):
    m = evaluate_pair(hazy_pair["clear"], hazy_pair["hazy"], hazy_pair["hazy"])
    assert m["edge_preservation"] == 1.0
    assert abs(m["entropy_gain"]) < 1e-6
    assert m["contrast_improvement"] > 0.0
    assert 0.0 <= m["ssim"] <= 1.0


def test_no_reference_metrics(hazy_pair):
    from src.density import shannon_entropy

    clear, hazy = hazy_pair["clear"], hazy_pair["hazy"]
    m = no_reference_metrics(hazy, clear)
    assert m["entropy_gain"] == pytest.approx(shannon_entropy(clear) - shannon_entropy(hazy))
    assert m["edge_preservation"] > 0.0
    assert m["color_cast_out"] >= 0.0


def test_paired_test():
    a = [1, 2, 3, 4, 5, 6]
    b = [0.5, 1.8, 3.1, 3.9, 4.8, 5.7]
    result = paired_test(a, b)
    assert result["adaptive_wins"] == 5
    assert result["baseline_wins"] == 1
    assert result["win_rate"] == pytest.approx(5 / 6)


def test_summarize_and_color():
    s = summarize([1.0, 2.0, 3.0])
    assert s["mean"] == 2.0 and s["n"] == 3
    img = np.ones((8, 8, 3), dtype=np.float32) * 0.5
    img[..., 0] = 0.6
    assert color_cast(img) > 0
    assert colorfulness(img) >= 0
    assert edge_energy(img) >= 0
