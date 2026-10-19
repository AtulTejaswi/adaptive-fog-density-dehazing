"""Ablation study: one row per configuration (component / feature / selector).

All rows are evaluated on the frozen test splits.  Results -> results/ablations.*
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline import dehaze_baseline  # noqa: E402
from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import evaluate_pair, no_reference_metrics  # noqa: E402
from src.pipeline import dehaze_adaptive  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402

VARIANTS = [
    {"name": "baseline_dcp", "kind": "baseline", "group": "baseline"},
    {"name": "adaptive_no_enh", "kind": "adaptive", "group": "component",
     "use_enhancement": False},
    {"name": "adaptive_clahe", "kind": "adaptive", "group": "component",
     "enhancement_switches": {"retinex": False, "gray_world": False}},
    {"name": "adaptive_clahe_retinex", "kind": "adaptive", "group": "component",
     "enhancement_switches": {"gray_world": False},
     "overrides": {"retinex": {"enabled": True, "strength": 0.35}}},
    {"name": "adaptive_full", "kind": "adaptive", "group": "component"},
    {"name": "density_dc_only", "kind": "adaptive", "group": "density_features",
     "feature_mask": {"entropy": False, "contrast": False}},
    {"name": "density_dc_entropy", "kind": "adaptive", "group": "density_features",
     "feature_mask": {"contrast": False}},
    {"name": "density_full", "kind": "adaptive", "group": "density_features"},
    {"name": "selector_continuous", "kind": "adaptive", "group": "selector", "mode": "continuous"},
    {"name": "selector_classifier", "kind": "adaptive", "group": "selector", "mode": "classifier"},
]

METRICS = ["psnr", "ssim", "entropy_gain", "contrast_improvement",
           "edge_preservation", "color_cast_out", "total_ms"]


def _df_to_md(df: pd.DataFrame, floatfmt: str = "{:.4f}") -> str:
    if df.empty:
        return "_empty_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |",
             "|" + "|".join(["---"] * len(cols)) + "|"]
    for _, row in df.iterrows():
        cells = []
        for col in cols:
            value = row[col]
            if isinstance(value, float):
                cells.append("" if not np.isfinite(value) else floatfmt.format(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ablation study")
    parser.add_argument("--splits", nargs="*", default=["test_sots"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    params = load_params()
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] in args.splits]
    if args.limit:
        by_split = {}
        limited = []
        for rec in records:
            n = by_split.get(rec["split"], 0)
            if n < args.limit:
                limited.append(rec)
                by_split[rec["split"]] = n + 1
        records = limited
    print(f"[ablation] {len(records)} records, {len(VARIANTS)} variants")

    rows = []
    estimator = DensityEstimator.from_config(params)
    selector = AdaptiveSelector(params)
    for idx, rec in enumerate(records):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = None
        if rec.get("has_gt") and rec.get("clear"):
            clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        density = estimator.score(hazy)
        main_class = rec.get("class") or selector.classify(density["score"], density["normalised"])
        for variant in VARIANTS:
            if variant["kind"] == "baseline":
                start = time.perf_counter()
                out, _ = dehaze_baseline(hazy, params)
                runtime = (time.perf_counter() - start) * 1000.0
                label = main_class
            else:
                out, info = dehaze_adaptive(
                    hazy, params,
                    mode=variant.get("mode"),
                    feature_mask=variant.get("feature_mask"),
                    enhancement_switches=variant.get("enhancement_switches"),
                    use_enhancement=variant.get("use_enhancement", True),
                    overrides=variant.get("overrides"),
                )
                runtime = info["timing_ms"]["total"]
                label = rec.get("class") or info.get("class", main_class)
            metrics = (evaluate_pair(clear, hazy, out) if clear is not None
                       else no_reference_metrics(hazy, out))
            rows.append({
                "variant": variant["name"],
                "group": variant["group"],
                "split": rec["split"],
                "id": rec["id"],
                "class": label,
                **{k: metrics.get(k, np.nan) for k in METRICS},
                "runtime_ms": runtime,
            })
        if idx % 25 == 0:
            print(f"  {idx}/{len(records)}")

    df = pd.DataFrame(rows)
    results_dir = resolve_path("results")
    results_dir.mkdir(parents=True, exist_ok=True)
    df.to_csv(results_dir / "ablations_per_image.csv", index=False)

    summary = (df.groupby(["variant", "group"]).agg(
        n=("id", "count"),
        psnr=("psnr", "mean"), ssim=("ssim", "mean"),
        entropy_gain=("entropy_gain", "mean"),
        contrast_improvement=("contrast_improvement", "mean"),
        edge_preservation=("edge_preservation", "mean"),
        color_cast_out=("color_cast_out", "mean"),
        runtime_ms=("runtime_ms", "mean"),
    ).reset_index())
    summary.to_csv(results_dir / "ablations.csv", index=False)

    order = {v["name"]: i for i, v in enumerate(VARIANTS)}
    summary["_order"] = summary["variant"].map(order)
    summary = summary.sort_values("_order").drop(columns="_order")
    (results_dir / "ablations.md").write_text(
        "# Ablation study (test split means)\n\n" + _df_to_md(summary) + "\n",
        encoding="utf-8",
    )
    print("[ablation] wrote results/ablations.csv and ablations.md")
    print(_df_to_md(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
