"""Tune per-class dehazing parameters on the calib split ONLY.

Two-stage coordinate search per class:
  1) omega x t0 (3x3 = 9 runs)
  2) CLAHE clip x Retinex strength (3x3 = 9 runs)
Total 18 full-pipeline runs per class, well under the configured budget.
Objective = 0.50*SSIM + 0.30*min(PSNR/40,1) + 0.20*min(edge_ratio/1.25,1).
"""
from __future__ import annotations

import argparse
import copy
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import deep_update, load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import evaluate_pair  # noqa: E402
from src.pipeline import dehaze_adaptive  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402


def _objective(metrics: dict, cfg: dict) -> float:
    w_ssim = float(cfg.get("ssim_weight", 0.5))
    w_psnr = float(cfg.get("psnr_weight", 0.3))
    w_edge = float(cfg.get("edge_weight", 0.2))
    psnr_ref = float(cfg.get("psnr_reference", 40.0))
    ssim_term = float(metrics.get("ssim", 0.0))
    psnr_term = min(max(float(metrics.get("psnr", 0.0)) / psnr_ref, 0.0), 1.0)
    edge_term = min(max(float(metrics.get("edge_preservation", 0.0)) / 1.25, 0.0), 1.0)
    return w_ssim * ssim_term + w_psnr * psnr_term + w_edge * edge_term


def _evaluate_config(images: list[dict], params: dict, force_class: str,
                     overrides: dict, estimator: DensityEstimator,
                     selector: AdaptiveSelector, obj_cfg: dict) -> dict:
    rows = []
    for item in images:
        out, _ = dehaze_adaptive(
            item["hazy"], params, selector=selector, estimator=estimator,
            force_class=force_class, overrides=overrides,
        )
        m = evaluate_pair(item["clear"], item["hazy"], out)
        m["objective"] = _objective(m, obj_cfg)
        rows.append(m)
    return {
        "n": len(rows),
        "psnr": float(np.mean([r["psnr"] for r in rows])),
        "ssim": float(np.mean([r["ssim"] for r in rows])),
        "edge_preservation": float(np.mean([r["edge_preservation"] for r in rows])),
        "entropy_gain": float(np.mean([r["entropy_gain"] for r in rows])),
        "objective": float(np.mean([r["objective"] for r in rows])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Tune adaptive params on calib only")
    parser.add_argument("--per-class", type=int, default=None, help="images per class")
    parser.add_argument("--quick", action="store_true", help="3 images/class and reduced grid")
    args = parser.parse_args()

    params = load_params()
    cfg = params.get("tuning", {})
    grid = cfg.get("grid", {})
    obj_cfg = cfg.get("objective", {})
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] == "calib" and r.get("has_gt")]
    if not records:
        raise SystemExit("No calib records with ground truth. Run prepare_data.py first.")

    estimator = DensityEstimator.from_config(params)
    # Tune from the human-readable defaults, not from a previous tuned file.
    selector = AdaptiveSelector(params, tuned={})
    limit = int(cfg.get("calib_limit", 60))
    per_class = args.per_class or max(4, limit // 3)
    if args.quick:
        per_class = 3

    by_class: dict[str, list[dict]] = {"light": [], "moderate": [], "heavy": []}
    for rec in records:
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        score = estimator.score(hazy)["score"]
        label = selector.classify(score)
        if len(by_class[label]) >= per_class:
            continue
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        by_class[label].append({"record": rec, "hazy": hazy, "clear": clear, "score": score})
    print("[tune] images per class:", {k: len(v) for k, v in by_class.items()})

    omegas = grid.get("omega", [0.75, 0.85, 0.95])
    t0s = grid.get("t0", [0.10, 0.20, 0.30])
    clips = grid.get("clahe_clip", [1.5, 2.0, 3.0])
    strengths = grid.get("retinex_strength", [0.0, 0.35, 0.60])
    if args.quick:
        omegas, t0s = omegas[::2], t0s[::2]
        clips, strengths = clips[::2], strengths[::2]

    all_rows = []
    best_by_class: dict[str, dict] = {}
    class_grids = cfg.get("class_grids", {})
    for label, items in by_class.items():
        if not items:
            continue
        print(f"[tune] class={label} n={len(items)}")
        base_cfg = selector.params_for_class(label)
        class_grid = class_grids.get(label, {})
        c_omegas = list(class_grid.get("omega", omegas))
        c_t0s = list(class_grid.get("t0", t0s))
        if args.quick:
            c_omegas, c_t0s = c_omegas[::2], c_t0s[::2]

        # stage 1: omega x t0
        stage1 = []
        for omega, t0 in itertools.product(c_omegas, c_t0s):
            overrides = {"omega": float(omega), "t0": float(t0)}
            metrics = _evaluate_config(items, params, label, overrides, estimator, selector, obj_cfg)
            row = {"class": label, "stage": "omega_t0", "omega": omega, "t0": t0,
                   "clahe_clip": base_cfg.get("clahe", {}).get("clip_limit"),
                   "retinex_strength": base_cfg.get("retinex", {}).get("strength", 0.0),
                   **metrics}
            stage1.append(row)
            all_rows.append(row)
        best1 = max(stage1, key=lambda r: r["objective"])
        print(f"  [stage1] omega={best1['omega']} t0={best1['t0']} obj={best1['objective']:.4f}")

        # stage 2: enhancement strengths at best omega/t0
        stage2 = []
        for clip, strength in itertools.product(clips, strengths):
            overrides = {
                "omega": float(best1["omega"]),
                "t0": float(best1["t0"]),
                "clahe": {"clip_limit": float(clip)},
                "retinex": {"enabled": bool(strength > 0.0), "strength": float(strength)},
            }
            metrics = _evaluate_config(items, params, label, overrides, estimator, selector, obj_cfg)
            row = {"class": label, "stage": "enhancement", "omega": best1["omega"],
                   "t0": best1["t0"], "clahe_clip": clip, "retinex_strength": strength, **metrics}
            stage2.append(row)
            all_rows.append(row)
        best2 = max(stage2, key=lambda r: r["objective"])
        print(f"  [stage2] clip={best2['clahe_clip']} retinex={best2['retinex_strength']} obj={best2['objective']:.4f}")

        best_by_class[label] = {
            "omega": float(best2["omega"]),
            "t0": float(best2["t0"]),
            "clahe": {"clip_limit": float(best2["clahe_clip"])},
            "retinex": {
                "enabled": bool(float(best2["retinex_strength"]) > 0.0),
                "strength": float(best2["retinex_strength"]),
            },
            "calibration_metrics": {
                "psnr": best2["psnr"], "ssim": best2["ssim"],
                "edge_preservation": best2["edge_preservation"],
                "entropy_gain": best2["entropy_gain"], "objective": best2["objective"],
                "n": best2["n"],
            },
        }

    results_dir = resolve_path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(all_rows).to_csv(results_dir / "tuning_grid.csv", index=False)
    tuned = {
        "created": datetime.now(timezone.utc).isoformat(),
        "tuned_on": "calib",
        "objective": obj_cfg,
        "budget_per_class": int(max(
            (len((class_grids.get(k, {})).get("omega", omegas)) *
             len((class_grids.get(k, {})).get("t0", t0s)))
            for k in ("light", "moderate", "heavy")
        ) + len(clips) * len(strengths)),
        "classes": best_by_class,
        "note": "Frozen before test evaluation. Only overrides are stored; defaults live in params.yaml.",
    }
    tuned_path = resolve_path(params.get("paths", {}).get("tuned_params", "config/tuned_params.json"))
    with open(tuned_path, "w", encoding="utf-8") as fh:
        json.dump(tuned, fh, indent=2)
        fh.write("\n")
    print(f"[tune] wrote {tuned_path}")
    print(f"[tune] grid rows: {len(all_rows)} -> results/tuning_grid.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
