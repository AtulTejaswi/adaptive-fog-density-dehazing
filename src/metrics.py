"""Stage 5: full-reference and no-reference quality metrics."""
from __future__ import annotations

import cv2
import numpy as np
from scipy import stats
from skimage.metrics import peak_signal_noise_ratio, structural_similarity

from .density import dark_channel, grayscale, michelson_contrast, rms_contrast, shannon_entropy
from .io_utils import to_uint8


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


def ciede2000(reference: np.ndarray, image: np.ndarray) -> float:
    """Mean CIEDE2000 colour difference in Lab (lower is better)."""
    from skimage.color import deltaE_ciede2000, rgb2lab

    reference, image = _match(reference, image)
    delta = deltaE_ciede2000(rgb2lab(reference), rgb2lab(image))
    return float(np.mean(delta))


def _mscn(gray: np.ndarray) -> np.ndarray:
    sigma = 7.0 / 6.0
    mu = cv2.GaussianBlur(gray.astype(np.float32), (7, 7), sigma)
    var = cv2.GaussianBlur(gray.astype(np.float32) ** 2, (7, 7), sigma) - mu * mu
    return ((gray - mu) / (np.sqrt(np.maximum(var, 0.0)) + 1e-6)).astype(np.float32)


def niqe_features(img: np.ndarray) -> np.ndarray:
    """MSCN statistics at two scales (NIQE-style, 20 features)."""
    gray = grayscale(img).astype(np.float32)
    feats: list[float] = []
    for scale in range(2):
        m = _mscn(gray)
        h, w = m.shape
        maps = [
            m,
            m[:, :-1] * m[:, 1:],
            m[:-1, :] * m[1:, :],
            m[:-1, :-1] * m[1:, 1:],
            m[:-1, 1:] * m[1:, :-1],
        ]
        for values in maps:
            feats.extend([float(np.mean(values)), float(np.std(values))])
        if scale == 0:
            gray = cv2.resize(gray, (max(8, w // 2), max(8, h // 2)),
                              interpolation=cv2.INTER_AREA)
    return np.asarray(feats, dtype=np.float64)


def fit_niqe_model(images: list[np.ndarray], reg: float = 1e-3) -> dict:
    """Fit the pristine multivariate-Gaussian model on clean calib images."""
    if not images:
        raise ValueError("NIQE model needs at least one pristine image")
    features = np.vstack([niqe_features(img) for img in images])
    mean = features.mean(axis=0)
    n_features = features.shape[1]
    if features.shape[0] < 2:
        cov = np.diag(np.ones(n_features, dtype=np.float64))
    else:
        cov = np.atleast_2d(np.cov(features, rowvar=False))
        if cov.shape != (n_features, n_features) or not np.all(np.isfinite(cov)):
            cov = np.diag(np.var(features, axis=0) + 1e-6)
    scale = float(np.trace(cov)) / max(1, cov.shape[0])
    cov = cov + float(reg) * max(scale, 1e-9) * np.eye(cov.shape[0])
    return {
        "mean": mean.tolist(),
        "cov_inv": np.linalg.pinv(cov).tolist(),
        "n_images": int(features.shape[0]),
        "n_features": int(features.shape[1]),
    }


def niqe(img: np.ndarray, model: dict | None) -> float:
    """NIQE-style distance to the pristine model (lower is better)."""
    if not model or "mean" not in model or "cov_inv" not in model:
        return float("nan")
    mean = np.asarray(model["mean"], dtype=np.float64)
    cov_inv = np.asarray(model["cov_inv"], dtype=np.float64)
    diff = niqe_features(img) - mean
    value = float(diff @ cov_inv @ diff)
    return float(np.sqrt(max(value, 0.0)))


def fade_fog_density(img: np.ndarray, cfg: dict | None = None) -> float:
    """FADE-style perceptual fog density in [0, 1] (lower = clearer).

    Uses the Choi et al. (2015) feature set (dark channel, contrast,
    saturation, colourfulness, entropy) with fixed documented weights.  The
    official learned FADE model is not shipped, so this is a transparent
    stand-in and is labelled as such in the report.
    """
    weights = ((cfg or {}).get("fade", {}) or {}).get("weights", {})
    dark = np.clip(float(np.mean(dark_channel(img, 15))) / 0.75, 0.0, 1.0)
    contrast = np.clip(rms_contrast(img) / 0.35, 0.0, 1.0)
    saturation = float(np.mean(cv2.cvtColor(to_uint8(img), cv2.COLOR_RGB2HSV)[..., 1])) / 255.0
    colourful = np.clip(colorfulness(img) / 0.60, 0.0, 1.0)
    entropy = np.clip(shannon_entropy(img) / 8.0, 0.0, 1.0)
    value = (
        float(weights.get("dark_channel", 0.35)) * dark
        + float(weights.get("contrast", 0.25)) * (1.0 - contrast)
        + float(weights.get("saturation", 0.15)) * (1.0 - saturation)
        + float(weights.get("colorfulness", 0.15)) * (1.0 - colourful)
        + float(weights.get("entropy", 0.10)) * (1.0 - entropy)
    )
    return float(np.clip(value, 0.0, 1.0))


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


def no_reference_metrics_v2(hazy: np.ndarray, out: np.ndarray,
                            niqe_model: dict | None = None,
                            cfg: dict | None = None,
                            edge_operator: str = "sobel") -> dict[str, float]:
    """v1 no-reference metrics plus NIQE-style and FADE-style fog density."""
    metrics = no_reference_metrics(hazy, out, edge_operator)
    metrics["niqe_out"] = niqe(out, niqe_model)
    metrics["niqe_in"] = niqe(hazy, niqe_model)
    metrics["fade_in"] = fade_fog_density(hazy, cfg)
    metrics["fade_out"] = fade_fog_density(out, cfg)
    metrics["fade_reduction"] = metrics["fade_in"] - metrics["fade_out"]
    return metrics


def evaluate_pair_v2(clear: np.ndarray, hazy: np.ndarray, out: np.ndarray,
                     niqe_model: dict | None = None, cfg: dict | None = None,
                     data_range: float = 1.0, edge_operator: str = "sobel") -> dict[str, float]:
    """Full-reference v2 metrics: v1 + CIEDE2000 + NIQE-style + FADE-style."""
    metrics = evaluate_pair(clear, hazy, out, data_range, edge_operator)
    metrics["ciede2000"] = ciede2000(clear, out)
    metrics.update({
        k: v for k, v in no_reference_metrics_v2(hazy, out, niqe_model, cfg, edge_operator).items()
        if k in {"niqe_out", "niqe_in", "fade_in", "fade_out", "fade_reduction"}
    })
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
