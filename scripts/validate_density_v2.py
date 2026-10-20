"""Validate global and local density against FADE, and test better density features.

- Spearman(density, FADE) on the 64-image density-validation sweep and the 72
  real RTTS images.
- A ridge regression of beta on density features, fitted on synthetic hazy
  versions of CALIB clear images only (known beta), then evaluated on the
  validation sweep; the fixed weighted score is the reference.
- Alternative contrast feature and feature-subset ablations.

Writes ``results/v2_density_validation.{json,md}``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator, extract_features  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import fade_fog_density  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.synthetic import apply_haze, make_depth  # noqa: E402

BETAS = (0.30, 0.60, 1.00, 1.50)


def _spearman(x, y) -> float:
    values = spearmanr(x, y).correlation
    return float(values) if np.isfinite(values) else float("nan")


def _saturation(img: np.ndarray) -> float:
    hsv = cv2.cvtColor((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), cv2.COLOR_RGB2HSV)
    return float(np.mean(hsv[..., 1])) / 255.0


def _feature_vector(img: np.ndarray, cfg: dict) -> list[float]:
    feats = extract_features(img, cfg)
    return [feats["dark_channel"], feats["entropy"], feats["contrast"], _saturation(img)]


def _fit_ridge(params: dict, splits: dict) -> tuple[object, int]:
    """Fit beta ~ features on synthetic hazy versions of CALIB clear images."""
    cfg = params.get("density", {})
    records = [r for r in splits["records"] if r["split"] == "calib" and r.get("clear")]
    rng = np.random.default_rng(int(params.get("project", {}).get("seed", 42)))
    # evenly spaced subset of calib clear scenes
    step = max(1, len(records) // 40)
    records = records[::step][:40]
    x, y = [], []
    for rec in records:
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        depth = make_depth(rng, clear.shape[0], clear.shape[1])
        airlight = rng.uniform(0.82, 0.95, size=3).astype(np.float32)
        for beta in BETAS:
            hazy, _ = apply_haze(clear, depth, beta, airlight, noise_sigma=0.004, rng=rng)
            x.append(_feature_vector(hazy, cfg))
            y.append(float(beta))
    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    model.fit(np.asarray(x), np.asarray(y))
    return model, len(y)


def main() -> int:
    params = load_params()
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    estimator = DensityEstimator.from_config(params)
    cfg = params.get("density", {})
    model, n_synthetic = _fit_ridge(params, splits)
    coef = model.named_steps["ridge"].coef_
    weights = {"dark_channel": float(coef[0]), "entropy": float(coef[1]),
               "contrast": float(coef[2]), "saturation": float(coef[3])}
    print(f"[density-v2] ridge fitted on {n_synthetic} synthetic calib images")

    def rows_for(split: str, with_beta: bool) -> pd.DataFrame:
        rows = []
        for rec in [r for r in splits["records"] if r["split"] == split]:
            image = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
            info = estimator.score(image)
            score_map = estimator.score_map(image)
            feats = extract_features(image, cfg)
            rows.append({
                "id": rec["id"],
                "scene": rec.get("scene", rec.get("group")),
                "beta": rec.get("beta"),
                "global": info["score"],
                "local_mean": float(score_map.mean()),
                "dc_only": float(info["normalised"]["dark_channel"]),
                "dc_entropy": float(
                    0.45 * info["oriented"]["dark_channel"] + 0.30 * info["oriented"]["entropy"]
                ) / 0.75,
                "contrast_std": feats["rms_contrast"],
                "ridge": float(model.predict([_feature_vector(image, cfg)])[0]),
                "fade": fade_fog_density(image, params),
            })
        return pd.DataFrame(rows)

    validation = rows_for("density_validation", True)
    rtts = rows_for("test_rtts", False)
    validation.to_csv(resolve_path("results/v2_density_validation.csv"), index=False)
    rtts.to_csv(resolve_path("results/v2_density_rtts.csv"), index=False)

    def correlations(df: pd.DataFrame, target: str) -> dict[str, float]:
        return {col: _spearman(df[col].tolist(), df[target].tolist())
                for col in ("global", "local_mean", "dc_only", "dc_entropy", "contrast_std", "ridge")}

    val_corr = correlations(validation, "beta")
    rtts_corr = correlations(rtts, "fade")
    within = {}
    for key in ("global", "local_mean", "ridge"):
        values = []
        for _, group in validation.groupby("scene"):
            if group["beta"].nunique() >= 3:
                values.append(_spearman(group[key].tolist(), group["beta"].tolist()))
        within[key] = float(np.nanmean(values)) if values else float("nan")

    delta = val_corr["ridge"] - val_corr["global"]
    conclusion = ("The ridge weights fitted on calib do not materially improve the beta "
                  "correlation" if delta <= 0.01 else
                  "The calib-fitted ridge weights improve the beta correlation")
    payload = {
        "n_validation": int(len(validation)),
        "n_rtts": int(len(rtts)),
        "validation_vs_beta": val_corr,
        "validation_within_scene_vs_beta": within,
        "rtts_vs_fade": rtts_corr,
        "ridge": {"alpha": 1.0, "weights": weights, "n_synthetic": n_synthetic,
                  "synthetic_betas": list(BETAS), "fitted_on": "calib_clear_synthetic"},
        "ridge_minus_global_validation": float(delta),
        "conclusion": conclusion,
        "note": "FADE is a simplified fixed-weight FADE-style index (documented in the report).",
    }
    out_json = resolve_path("results/v2_density_validation.json")
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    lines = [
        "# v2 density validation",
        "",
        f"- Validation sweep: {len(validation)} images (64 synthetic, known beta).",
        f"- Real RTTS: {len(rtts)} images (no beta; correlated with FADE-style density).",
        "",
        "| signal | Spearman vs beta (validation) | within-scene | Spearman vs FADE (RTTS) |",
        "|---|---|---|---|",
    ]
    for key in ("global", "local_mean", "dc_only", "dc_entropy", "contrast_std", "ridge"):
        lines.append(f"| {key} | {val_corr[key]:.3f} | "
                     f"{within.get(key, float('nan')):.3f} | {rtts_corr[key]:.3f} |")
    lines += ["", f"Ridge weights (standardised): {weights}", "", conclusion + "."]
    resolve_path("results/v2_density_validation.md").write_text("\n".join(lines) + "\n",
                                                               encoding="utf-8")
    print("[density-v2] validation:", {k: round(v, 3) for k, v in val_corr.items()})
    print("[density-v2] RTTS vs FADE:", {k: round(v, 3) for k, v in rtts_corr.items()})
    print("[density-v2]", conclusion)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
