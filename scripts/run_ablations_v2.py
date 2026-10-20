"""v2 ablation: v1 -> +airlight_v2 -> +sky -> +local omega -> +local enhancement -> full v2.

One row per step with PSNR / SSIM / CIEDE2000 / NIQE / FADE / runtime.
Writes ``results/v2_ablations*``; v1 ablation files are untouched.
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import evaluate_pair_v2, no_reference_metrics_v2  # noqa: E402
from src.pipeline import dehaze_adaptive, dehaze_adaptive_v2  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

METRICS = ["psnr", "ssim", "ciede2000", "niqe_out", "fade_out",
           "entropy_gain", "contrast_improvement", "edge_preservation", "color_cast_out"]


def _md(df: pd.DataFrame, floatfmt: str = "{:.4f}") -> str:
    if df is None or df.empty:
        return "_not available_"
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


def _variants(params: dict, tuned: dict) -> list[dict]:
    base = copy.deepcopy(params.get("v2", {}))
    base.update({"enabled": True, "airlight": {"method": "v1"},
                 "sky": {"enabled": False},
                 "local_density": {"enabled": False},
                 "enhance": {"local_blend": False},
                 "retinex": {"fast": False, "scale": 0.5}})
    steps = []

    v = copy.deepcopy(base)
    steps.append({"name": "v1", "note": "v1 pipeline (no v2 features)", "v2": None})

    v = copy.deepcopy(base)
    v["airlight"]["method"] = "v2"
    steps.append({"name": "v2_airlight", "note": "+ connected/low-gradient airlight", "v2": v})

    v = copy.deepcopy(v)
    v["sky"] = {"enabled": True, "t_floor": 0.25, "blend": 0.25}
    steps.append({"name": "v2_airlight_sky", "note": "+ sky / white-object handling", "v2": v})

    v = copy.deepcopy(v)
    v["local_density"]["enabled"] = True
    steps.append({"name": "v2_local_omega", "note": "+ local omega/t0 maps", "v2": v})

    v = copy.deepcopy(v)
    v["enhance"]["local_blend"] = True
    v["enhance"]["floor"] = 0.0
    steps.append({"name": "v2_local_enhance", "note": "+ spatially blended enhancement", "v2": v})

    full = copy.deepcopy(v)
    tuned_v2 = tuned.get("v2", {})
    for key in ("airlight", "sky", "local_density", "enhance", "retinex"):
        if isinstance(tuned_v2.get(key), dict):
            full.setdefault(key, {}).update(copy.deepcopy(tuned_v2[key]))
    steps.append({"name": "v2_full", "note": "full v2 (frozen tuned config)", "v2": full})
    return steps


def main() -> int:
    parser = argparse.ArgumentParser(description="v2 ablation study")
    parser.add_argument("--splits", nargs="*", default=["test_sots"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    params = load_params()
    tuned = load_json(params.get("paths", {}).get("tuned_params_v2",
                                                  "config/tuned_params_v2.json"), default={})
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] in args.splits]
    if args.limit:
        records = records[: args.limit]
    model = load_json(params.get("paths", {}).get("niqe_model", "config/niqe_model.json"),
                      default=None)
    variants = _variants(params, tuned)
    print(f"[v2-ablation] {len(records)} images x {len(variants)} variants")

    rows = []
    for idx, rec in enumerate(records, start=1):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = None
        if rec.get("has_gt") and rec.get("clear"):
            clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        for variant in variants:
            start = time.perf_counter()
            if variant["v2"] is None:
                out, _ = dehaze_adaptive(hazy, params)
            else:
                out, _ = dehaze_adaptive_v2(hazy, params, v2=variant["v2"])
            runtime = (time.perf_counter() - start) * 1000.0
            metrics = (evaluate_pair_v2(clear, hazy, out, model, params)
                       if clear is not None else no_reference_metrics_v2(hazy, out, model, params))
            rows.append({
                "variant": variant["name"], "note": variant["note"],
                "split": rec["split"], "id": rec["id"],
                **{k: metrics.get(k, np.nan) for k in METRICS},
                "runtime_ms": runtime,
            })
        if idx % 25 == 0 or idx == len(records):
            print(f"[v2-ablation] {idx}/{len(records)}")

    df = pd.DataFrame(rows)
    results = resolve_path("results")
    df.to_csv(results / "v2_ablations_per_image.csv", index=False)
    summary = (df.groupby(["variant", "note"])
               .agg(n=("id", "count"),
                    **{k: (k, "mean") for k in METRICS},
                    runtime_ms=("runtime_ms", "mean"))
               .reset_index())
    order = {v["name"]: i for i, v in enumerate(variants)}
    summary["_order"] = summary["variant"].map(order)
    summary = summary.sort_values("_order").drop(columns="_order")
    summary.to_csv(results / "v2_ablations.csv", index=False)
    (results / "v2_ablations.md").write_text(
        "# v2 ablation (test split means)\n\n" + _md(summary) + "\n", encoding="utf-8")
    print("[v2-ablation] wrote results/v2_ablations.csv and v2_ablations.md")
    print(_md(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
