"""Fit local density normalisation + class score centroids on calib ONLY.

Writes ``config/calibration_local.json``.  Never reads test_sots / test_rtts.
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import (  # noqa: E402
    DensityEstimator,
    fit_local_normalisation,
    local_feature_maps,
)
from src.io_utils import read_rgb  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

CLASSES = ("light", "moderate", "heavy")


def main() -> int:
    params = load_params()
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] == "calib"]
    if not records:
        raise SystemExit("No calib records; run scripts/prepare_data.py first")

    calibration = load_json(params.get("paths", {}).get("calibration", "config/calibration.json"),
                            default={}) or {}
    thresholds = calibration.get("thresholds", {})
    t1 = float(thresholds.get("t1", 0.33))
    t2 = float(thresholds.get("t2", 0.66))
    local_cfg = params.get("density", {}).get("local", {})
    estimator = DensityEstimator.from_config(params)

    print(f"[local-calib] {len(records)} calib images")
    maps = []
    scores = []
    for idx, rec in enumerate(records, start=1):
        image = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        feature_maps = local_feature_maps(image, local_cfg, params.get("density", {}))
        maps.append({key: value[::4, ::4].copy() for key, value in feature_maps.items()})
        scores.append(estimator.score(image)["score"])
        if idx % 50 == 0 or idx == len(records):
            print(f"[local-calib] {idx}/{len(records)}")

    stats = fit_local_normalisation(maps, params.get("density", {}), stride=1)
    score_array = np.asarray(scores, dtype=np.float64)
    labels = np.where(score_array < t1, "light",
                      np.where(score_array < t2, "moderate", "heavy"))
    centroids = {
        cls: float(score_array[labels == cls].mean())
        for cls in CLASSES if np.any(labels == cls)
    }
    payload = {
        "created": date.today().isoformat(),
        "n_calib": int(len(records)),
        "local_stats": stats,
        "class_score_centroids": centroids,
        "score_thresholds": {"t1": t1, "t2": t2},
        "class_counts": dict(Counter(labels.tolist())),
        "note": "Fitted on calib only. Used only when v2.local_density.enabled.",
    }
    path = resolve_path(params.get("paths", {}).get("calibration_local",
                                                   "config/calibration_local.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    print(f"[local-calib] centroids={centroids}")
    print(f"[local-calib] wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
