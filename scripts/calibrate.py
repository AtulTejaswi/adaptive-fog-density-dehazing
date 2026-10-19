"""Fit density normalisation + selector thresholds on the calib split ONLY.

Also validates the density score against known beta on the synthetic beta
sweep and trains the optional shallow classifier (ablation).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import (  # noqa: E402
    DensityEstimator,
    calibrate,
    extract_features,
    spearman_correlation,
)
from src.io_utils import read_rgb  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import train_classifier  # noqa: E402


def _load_splits(path: str | Path) -> dict:
    with open(resolve_path(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate density stats and thresholds")
    parser.add_argument("--limit", type=int, default=None, help="limit calibration images (debug)")
    args = parser.parse_args()

    params = load_params()
    splits = _load_splits(params.get("paths", {}).get("splits", "data/splits.json"))
    calib_records = [r for r in splits["records"] if r["split"] == "calib"]
    if args.limit:
        calib_records = calib_records[: args.limit]
    if not calib_records:
        raise SystemExit("No calib records. Run scripts/prepare_data.py first.")

    print(f"[calibrate] loading {len(calib_records)} calibration images")
    images = []
    for rec in calib_records:
        images.append(preprocess_array(read_rgb(resolve_path(rec["hazy"])), params))

    result = calibrate(params, images)
    stats = result["density_stats"]
    estimator = DensityEstimator(cfg=params.get("density", {}), stats=stats)
    scores = np.asarray([estimator.score(img)["score"] for img in images], dtype=np.float64)
    t1, t2 = np.percentile(scores, [33.3333, 66.6667])
    if t2 <= t1:
        t1, t2 = float(np.min(scores)), float(np.max(scores))
    thresholds = {"t1": float(t1), "t2": float(t2)}

    labels = ["light" if s < t1 else ("moderate" if s < t2 else "heavy") for s in scores]
    payload = {
        "created": date.today().isoformat(),
        "n_calib": int(len(images)),
        "density_stats": stats,
        "thresholds": thresholds,
        "score_stats": {
            "mean": float(scores.mean()),
            "std": float(scores.std(ddof=1)),
            "min": float(scores.min()),
            "max": float(scores.max()),
            "p25": float(np.percentile(scores, 25)),
            "p50": float(np.percentile(scores, 50)),
            "p75": float(np.percentile(scores, 75)),
        },
        "class_counts": dict(Counter(labels)),
        "weights": params.get("density", {}).get("weights", {}),
        "note": "Fitted on calib only. Never refit on test_sots/test_rtts.",
    }
    calib_path = resolve_path(params.get("paths", {}).get("calibration", "config/calibration.json"))
    calib_path.parent.mkdir(parents=True, exist_ok=True)
    with open(calib_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(f"[calibrate] thresholds t1={t1:.4f} t2={t2:.4f}; classes={payload['class_counts']}")
    print(f"[calibrate] wrote {calib_path}")

    # ---------------- density validation: score vs beta --------------------
    val_records = [r for r in splits["records"] if r["split"] == "density_validation"]
    rows = []
    for rec in val_records:
        img = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        feature_info = estimator.score(img)
        rows.append({
            "id": rec["id"],
            "scene": rec.get("scene", rec.get("group")),
            "beta": rec.get("beta"),
            "class": rec.get("class"),
            "score": feature_info["score"],
            **{f"f_{k}": v for k, v in feature_info["features"].items()},
        })
    if rows:
        df = pd.DataFrame(rows)
        out_csv = resolve_path("results/density_validation.csv")
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out_csv, index=False)
        overall = spearman_correlation(df["beta"].tolist(), df["score"].tolist())
        per_scene = []
        for scene, group in df.groupby("scene"):
            if group["beta"].nunique() >= 3:
                per_scene.append(spearman_correlation(group["beta"].tolist(), group["score"].tolist()))
        summary = {
            "n": int(len(df)),
            "n_scenes": int(df["scene"].nunique()),
            "spearman_overall": float(overall),
            "spearman_within_scene_mean": float(np.nanmean(per_scene)) if per_scene else None,
            "spearman_within_scene_min": float(np.nanmin(per_scene)) if per_scene else None,
            "monotonic_scenes": int(np.sum(np.asarray(per_scene) > 0.8)) if per_scene else 0,
        }
        with open(resolve_path("results/density_validation_summary.json"), "w", encoding="utf-8") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
        print(f"[validate] Spearman overall={summary['spearman_overall']:.3f}, "
              f"within-scene mean={summary['spearman_within_scene_mean']:.3f}")

    # ---------------- optional classifier (ablation) -----------------------
    train_records = [r for r in splits["records"] if r["split"] == "selector_train"]
    if train_records:
        features, labels = [], []
        for rec in train_records:
            img = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
            info = estimator.score(img)
            features.append([
                info["normalised"]["dark_channel"],
                info["normalised"]["entropy"],
                info["normalised"]["contrast"],
            ])
            labels.append(rec.get("class") or "moderate")
        trained = train_classifier(np.asarray(features), labels, params)
        classifier_info = {
            "n_train": len(train_records),
            "classes": trained["classes"],
            "holdout_accuracy": trained["accuracy"],
            "model": params.get("paths", {}).get("selector_classifier", "config/selector_classifier.joblib"),
        }
        with open(resolve_path("results/selector_classifier.json"), "w", encoding="utf-8") as fh:
            json.dump(classifier_info, fh, indent=2)
            fh.write("\n")
        print(f"[classifier] holdout accuracy={trained['accuracy']:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
