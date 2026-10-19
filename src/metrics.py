"""Stage 5: full-reference and no-reference quality metrics."""
from __future__ import annotations

import numpy as np
from scipy import stats
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from .density import grayscale, michelson_contrast, rms_contrast, shannon_entropy


def psnr(reference: np.ndarray, image: np.ndarray, data_range: float = 1.0) -> float:
    reference, image = _match(reference, image)
    return float(peak_signal_noise_ratio(reference, image, data_range=data_range))


def ssim(reference: np.ndarray, image: np.ndarray, data_range: float = 1.0) -> float:
    reference, image = _match(reference, image)
    return float(structural_similarity(reference, image, data_range=data_range, channel_axis=-1))


def _match(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if a.shape != b.shape:
        raise ValueError(f"Shape mismatch: {a.shape} vs {b.shape}")
    return a.astype(np.float32), b.astype(np.float32)


def edge_energy(img: np.ndarray, operator: str = "sobel") -> float:
    import cv2

    gray = grayscale(img).astype(np.float32)
    if operator == "sobel":
        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    elif operator == "scharr":
        gx = cv2.Scharr(gray, cv2.CV_32F, 1, 0)
        gy = cv2.Scharr(gray, cv2.CV_32F, 0, 1)
    else:
        raise ValueError(f"Unknown edge operator: {operator}")
    return float(np.mean(np.sqrt(gx * gx + gy * gy)))


def colorfulness(img: np.ndarray) -> float:
    """Hasler-Suesstrunk colourfulness."""
    r, g, b = img[..., 0], img[..., 1], img[..., 2]
    rg = r - g
    yb = 0.5 * (r + g) - b
    std = np.sqrt(np.std(rg) ** 2 + np.std(yb) ** 2)
    mean = np.sqrt(np.mean(rg) ** 2 + np.mean(yb) ** 2)
    return float(std + 0.3 * mean)


def color_cast(img: np.ndarray) -> float:
    """Spread of channel means; lower is closer to gray-world balanced."""
    means = img.reshape(-1, 3).mean(axis=0)
    return float(np.std(means))


def no_reference_metrics(hazy: np.ndarray, out: np.ndarray,
                         edge_operator: str = "sobel") -> dict[str, float]:
    h_entropy, o_entropy = shannon_entropy(hazy), shannon_entropy(out)
    h_rms, o_rms = rms_contrast(hazy), rms_contrast(out)
    h_edge, o_edge = edge_energy(hazy, edge_operator), edge_energy(out, edge_operator)
    return {
        "entropy_in": h_entropy,
        "entropy_out": o_entropy,
        "entropy_gain": o_entropy - h_entropy,
        "rms_in": h_rms,
        "rms_out": o_rms,
        "contrast_improvement": (o_rms + 1e-8) / (h_rms + 1e-8),
        "michelson_out": michelson_contrast(out),
        "edge_in": h_edge,
        "edge_out": o_edge,
        "edge_preservation": (o_edge + 1e-8) / (h_edge + 1e-8),
        "colorfulness_in": colorfulness(hazy),
        "colorfulness_out": colorfulness(out),
        "color_cast_in": color_cast(hazy),
        "color_cast_out": color_cast(out),
    }


def full_reference_metrics(clear: np.ndarray, out: np.ndarray,
                           data_range: float = 1.0) -> dict[str, float]:
    return {
        "psnr": psnr(clear, out, data_range),
        "ssim": ssim(clear, out, data_range),
    }


def evaluate_pair(clear: np.ndarray, hazy: np.ndarray, out: np.ndarray,
                  data_range: float = 1.0, edge_operator: str = "sobel") -> dict[str, float]:
    metrics = no_reference_metrics(hazy, out, edge_operator)
    metrics.update(full_reference_metrics(clear, out, data_range))
    metrics["psnr_hazy"] = psnr(clear, hazy, data_range)
    metrics["ssim_hazy"] = ssim(clear, hazy, data_range)
    metrics["psnr_gain"] = metrics["psnr"] - metrics["psnr_hazy"]
    metrics["ssim_gain"] = metrics["ssim"] - metrics["ssim_hazy"]
    return metrics


def summarize(values) -> dict[str, float]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float64)
    if arr.size == 0:
        return {"mean": float("nan"), "std": float("nan"), "n": 0}
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
        "median": float(np.median(arr)),
        "min": float(arr.min()),
        "max": float(arr.max()),
        "n": int(arr.size),
    }


def paired_test(a, b) -> dict[str, float]:
    """Wilcoxon signed-rank test for paired adaptive-vs-baseline values."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    a, b = a[mask], b[mask]
    diff = a - b
    out = {
        "mean_diff": float(np.mean(diff)) if diff.size else float("nan"),
        "adaptive_wins": int(np.sum(diff > 0)),
        "baseline_wins": int(np.sum(diff < 0)),
        "ties": int(np.sum(np.isclose(diff, 0.0))),
        "n": int(diff.size),
        "win_rate": float(np.mean(diff > 0)) if diff.size else float("nan"),
    }
    if diff.size >= 5 and np.any(~np.isclose(diff, 0.0)):
        try:
            stat, p = stats.wilcoxon(a, b, zero_method="wilcox", alternative="two-sided")
            out["wilcoxon_stat"] = float(stat)
            out["p_value"] = float(p)
        except ValueError:
            out["p_value"] = float("nan")
    else:
        out["p_value"] = float("nan")
    return out


def bootstrap_ci(values, n_boot: int = 1000, alpha: float = 0.05, seed: int = 42) -> dict[str, float]:
    arr = np.asarray([v for v in values if np.isfinite(v)], dtype=np.float64)
    if arr.size < 2:
        return {"mean": float(arr.mean()) if arr.size else float("nan"),
                "ci_low": float("nan"), "ci_high": float("nan"), "n": int(arr.size)}
    rng = np.random.default_rng(seed)
    means = np.array([rng.choice(arr, size=arr.size, replace=True).mean() for _ in range(n_boot)])
    return {
        "mean": float(arr.mean()),
        "ci_low": float(np.quantile(means, alpha / 2)),
        "ci_high": float(np.quantile(means, 1 - alpha / 2)),
        "n": int(arr.size),
    }
