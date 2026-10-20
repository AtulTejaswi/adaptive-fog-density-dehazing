"""Stage 2: fog-density estimation from classical statistics.

Three complementary features are extracted per image:

* dark-channel mean  (higher  -> hazier)
* Shannon entropy    (lower   -> hazier, detail is washed out)
* global contrast    (lower   -> hazier; RMS + Michelson)

Each feature is min-max normalised with percentiles fitted on the ``calib``
split only, oriented so that larger always means hazier, and combined into a
single fog-density score in [0, 1].  No ground-truth haze labels are needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np
from skimage.filters.rank import entropy as rank_entropy
from skimage.morphology import disk

from .config import load_json, resolve_path
from .guided_filter import guided_filter
from .io_utils import to_uint8


# ---------------------------------------------------------------------------
# Features
# ---------------------------------------------------------------------------
def grayscale(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img.astype(np.float32)
    return (
        0.299 * img[..., 0] + 0.587 * img[..., 1] + 0.114 * img[..., 2]
    ).astype(np.float32)


def dark_channel(img: np.ndarray, patch_size: int = 15) -> np.ndarray:
    """Per-pixel dark channel: min over RGB, then a minimum filter."""
    patch_size = int(patch_size)
    if patch_size % 2 == 0:
        patch_size += 1
    patch_size = max(1, patch_size)
    if img.ndim == 2:
        min_rgb = img.astype(np.float32)
    else:
        min_rgb = np.min(img[..., :3], axis=2).astype(np.float32)
    kernel = np.ones((patch_size, patch_size), dtype=np.uint8)
    # Erosion with a rectangular kernel is a minimum filter.
    return cv2.erode(min_rgb, kernel, borderType=cv2.BORDER_REFLECT)


def dark_channel_mean(img: np.ndarray, patch_size: int = 15) -> float:
    return float(np.mean(dark_channel(img, patch_size)))


def shannon_entropy(img: np.ndarray, bins: int = 256) -> float:
    gray = np.clip(grayscale(img), 0.0, 1.0)
    hist, _ = np.histogram(gray, bins=int(bins), range=(0.0, 1.0))
    p = hist.astype(np.float64)
    total = p.sum()
    if total <= 0:
        return 0.0
    p = p[p > 0] / total
    return float(-np.sum(p * np.log2(p)))


def michelson_contrast(img: np.ndarray, percentiles: Iterable[float] = (5, 95)) -> float:
    gray = np.clip(grayscale(img), 0.0, 1.0)
    lo, hi = np.percentile(gray, list(percentiles))
    return float((hi - lo) / (hi + lo + 1e-6))


def rms_contrast(img: np.ndarray) -> float:
    return float(np.std(grayscale(img)))


def global_contrast(img: np.ndarray, percentiles: Iterable[float] = (5, 95)) -> float:
    """Average of normalised RMS and Michelson contrast (both in ~[0, 1])."""
    return float(0.5 * (rms_contrast(img) + michelson_contrast(img, percentiles)))


def extract_features(img: np.ndarray, cfg: dict) -> dict[str, float]:
    """Raw (un-normalised) density features for one image."""
    patch = int(cfg.get("patch_size", 15))
    bins = int(cfg.get("entropy_bins", 256))
    pct = cfg.get("contrast_percentiles", [5, 95])
    gray = np.clip(grayscale(img), 0.0, 1.0)
    lo, hi = np.percentile(gray, list(pct))
    return {
        "dark_channel": dark_channel_mean(img, patch),
        "entropy": shannon_entropy(img, bins),
        "contrast": 0.5 * (float(np.std(gray)) + float((hi - lo) / (hi + lo + 1e-6))),
        "rms_contrast": float(np.std(gray)),
        "michelson_contrast": float((hi - lo) / (hi + lo + 1e-6)),
    }


# ---------------------------------------------------------------------------
# Normalisation + score
# ---------------------------------------------------------------------------
DEFAULT_STATS = {
    "dark_channel": {"low": 0.02, "high": 0.75},
    "entropy": {"low": 3.5, "high": 8.0},
    "contrast": {"low": 0.04, "high": 0.45},
}


def fit_normalisation(feature_rows: list[dict], cfg: dict) -> dict:
    """Percentile normalisation stats fitted on the calibration split."""
    norm = cfg.get("normalization", {})
    low_p = float(norm.get("low_percentile", 2))
    high_p = float(norm.get("high_percentile", 98))
    stats: dict[str, dict[str, float]] = {}
    for key in ("dark_channel", "entropy", "contrast"):
        values = np.asarray([row[key] for row in feature_rows], dtype=np.float64)
        lo = float(np.percentile(values, low_p))
        hi = float(np.percentile(values, high_p))
        if hi <= lo:
            hi = lo + 1e-6
        stats[key] = {"low": lo, "high": hi}
    return stats


def normalise_feature(value: float, key: str, stats: dict) -> float:
    s = stats.get(key, DEFAULT_STATS[key])
    lo, hi = float(s["low"]), float(s["high"])
    if hi <= lo:
        return 0.0
    return float(np.clip((value - lo) / (hi - lo), 0.0, 1.0))


@dataclass
class DensityEstimator:
    """Turns an RGB image into a fog-density score in [0, 1]."""

    cfg: dict
    stats: dict[str, dict[str, float]] = field(default_factory=dict)
    local_stats: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.stats:
            self.stats = dict(DEFAULT_STATS)
        if not self.local_stats:
            self.local_stats = dict(DEFAULT_LOCAL_STATS)

    @classmethod
    def from_config(cls, params: dict, stats_path: str | None = None,
                    local_stats_path: str | None = None) -> "DensityEstimator":
        path = stats_path or params.get("paths", {}).get("calibration", "config/calibration.json")
        calib = load_json(path, default=None)
        stats = (calib or {}).get("density_stats") or dict(DEFAULT_STATS)
        local_path = local_stats_path or params.get("paths", {}).get(
            "calibration_local", "config/calibration_local.json")
        local_calib = load_json(local_path, default=None)
        local_stats = (local_calib or {}).get("local_stats") or dict(DEFAULT_LOCAL_STATS)
        return cls(cfg=params.get("density", {}), stats=stats, local_stats=local_stats)

    def normalise(self, features: dict[str, float]) -> dict[str, float]:
        return {
            key: normalise_feature(features[key], key, self.stats)
            for key in ("dark_channel", "entropy", "contrast")
        }

    def score(self, img: np.ndarray, feature_mask: dict | None = None) -> dict:
        raw = extract_features(img, self.cfg)
        norm = self.normalise(raw)
        weights = dict(self.cfg.get("weights", {}))
        mask = feature_mask if feature_mask is not None else self.cfg.get("features", {})
        for key in ("dark_channel", "entropy", "contrast"):
            if mask is not None and not mask.get(key, True):
                weights[key] = 0.0
        total = sum(max(0.0, float(v)) for v in weights.values())
        if total <= 0:
            total = 1.0
            weights = {"dark_channel": 1.0, "entropy": 0.0, "contrast": 0.0}
            norm = {"dark_channel": 0.5, "entropy": 0.5, "contrast": 0.5}
        oriented = {
            "dark_channel": norm["dark_channel"],          # high -> hazy
            "entropy": 1.0 - norm["entropy"],              # low  -> hazy
            "contrast": 1.0 - norm["contrast"],            # low  -> hazy
        }
        value = sum(float(weights[k]) * oriented[k] for k in weights) / total
        return {
            "score": float(np.clip(value, 0.0, 1.0)),
            "features": raw,
            "normalised": norm,
            "oriented": oriented,
            "weights": weights,
        }

    def score_map(self, img: np.ndarray, local_cfg: dict | None = None,
                  feature_mask: dict | None = None) -> np.ndarray:
        """Per-pixel fog-density map in [0, 1], smoothly guided-filtered."""
        local_cfg = dict(local_cfg or self.cfg.get("local", {}))
        maps = local_feature_maps(img, local_cfg, self.cfg)
        norm: dict[str, np.ndarray] = {}
        for key in ("dark_channel", "entropy", "contrast"):
            s = self.local_stats.get(key, DEFAULT_LOCAL_STATS[key])
            lo, hi = float(s["low"]), float(s["high"])
            norm[key] = (np.clip((maps[key] - lo) / (hi - lo + 1e-9), 0.0, 1.0)
                         if hi > lo else np.zeros_like(maps[key]))
        weights = dict(self.cfg.get("weights", {}))
        mask = feature_mask if feature_mask is not None else self.cfg.get("features", {})
        for key in ("dark_channel", "entropy", "contrast"):
            if mask is not None and not mask.get(key, True):
                weights[key] = 0.0
        total = sum(max(0.0, float(v)) for v in weights.values()) or 1.0
        oriented = {
            "dark_channel": norm["dark_channel"],
            "entropy": 1.0 - norm["entropy"],
            "contrast": 1.0 - norm["contrast"],
        }
        score = sum(float(weights[k]) * oriented[k] for k in weights) / total
        radius = int(local_cfg.get("smooth_radius", 15))
        if radius > 0:
            score = guided_filter(grayscale(img), score.astype(np.float32),
                                  radius=radius, eps=float(local_cfg.get("smooth_eps", 1e-3)))
        return np.clip(score, 0.0, 1.0).astype(np.float32)

    def __call__(self, img: np.ndarray) -> float:
        return self.score(img)["score"]


# ---------------------------------------------------------------------------
# v2: local (spatially varying) density
# ---------------------------------------------------------------------------
DEFAULT_LOCAL_STATS = {
    "dark_channel": {"low": 0.02, "high": 0.65},
    "entropy": {"low": 1.5, "high": 6.0},
    "contrast": {"low": 0.01, "high": 0.18},
}


def local_feature_maps(img: np.ndarray, local_cfg: dict | None = None,
                       feature_cfg: dict | None = None) -> dict[str, np.ndarray]:
    """Sliding-window dark channel, entropy and contrast maps.

    Dark channel and RMS contrast use box filters (O(1) per pixel); entropy
    uses a rank-filter over a disk of radius ``window // 2``.
    """
    local_cfg = local_cfg or {}
    feature_cfg = feature_cfg or {}
    window = int(local_cfg.get("window", 31))
    if window % 2 == 0:
        window += 1
    window = max(3, window)
    patch = int(feature_cfg.get("patch_size", 15))
    gray = np.clip(grayscale(img), 0.0, 1.0).astype(np.float32)

    dark = dark_channel(img, patch)
    dark_mean = cv2.blur(dark, (window, window), borderType=cv2.BORDER_REFLECT)

    mean = cv2.blur(gray, (window, window), borderType=cv2.BORDER_REFLECT)
    mean_sq = cv2.blur(gray * gray, (window, window), borderType=cv2.BORDER_REFLECT)
    local_std = np.sqrt(np.maximum(mean_sq - mean * mean, 0.0))

    radius = max(1, window // 2)
    local_entropy = rank_entropy(to_uint8(gray), disk(radius)).astype(np.float32)

    return {
        "dark_channel": dark_mean.astype(np.float32),
        "entropy": local_entropy,
        "contrast": local_std.astype(np.float32),
    }


def fit_local_normalisation(maps: list[dict[str, np.ndarray]], cfg: dict,
                            stride: int = 3) -> dict:
    """Percentile normalisation for local features, fitted on calib only."""
    norm = cfg.get("normalization", {})
    low_p = float(norm.get("low_percentile", 2))
    high_p = float(norm.get("high_percentile", 98))
    stats: dict[str, dict[str, float]] = {}
    for key in ("dark_channel", "entropy", "contrast"):
        values = np.concatenate([m[key][::stride, ::stride].reshape(-1) for m in maps])
        lo = float(np.percentile(values, low_p))
        hi = float(np.percentile(values, high_p))
        if hi <= lo:
            hi = lo + 1e-6
        stats[key] = {"low": lo, "high": hi}
    return stats


def calibrate_local(params: dict, images: list[np.ndarray]) -> dict:
    """Fit local normalisation stats on the calibration split."""
    if not images:
        raise ValueError("Local calibration requires at least one image")
    cfg = params.get("density", {})
    local_cfg = cfg.get("local", {})
    maps = [local_feature_maps(img, local_cfg, cfg) for img in images]
    return {"local_stats": fit_local_normalisation(maps, cfg), "n_images": len(images)}


def calibrate(params: dict, images: list[np.ndarray]) -> dict:
    """Fit normalisation statistics from calibration images."""
    if not images:
        raise ValueError("Calibration requires at least one image")
    cfg = params.get("density", {})
    rows = [extract_features(img, cfg) for img in images]
    stats = fit_normalisation(rows, cfg)
    return {"density_stats": stats, "n_images": len(images)}


def spearman_correlation(x: list[float], y: list[float]) -> float:
    from scipy.stats import spearmanr

    if len(x) < 3:
        return float("nan")
    return float(spearmanr(x, y).correlation)
