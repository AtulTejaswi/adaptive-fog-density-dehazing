"""Evaluate baseline vs adaptive on the frozen test splits.

Outputs (all under results/):
  metrics_per_image.csv, metrics_summary.csv/.md, comparison.csv/.md,
  runtime.csv, key_numbers.json
Images for figures are cached under results/images/ (gitignored).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline import dehaze_baseline  # noqa: E402
from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.io_utils import read_rgb, write_rgb  # noqa: E402
from src.metrics import (  # noqa: E402
    bootstrap_ci,
    evaluate_pair,
    no_reference_metrics,
    paired_test,
    summarize,
)
from src.pipeline import dehaze_adaptive  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

METRICS = [
    "psnr", "ssim", "psnr_gain", "ssim_gain",
    "entropy_gain", "contrast_improvement", "edge_preservation",
    "color_cast_out", "colorfulness_out",
]
SUMMARY_METRICS = METRICS + ["preprocess_ms", "method_ms", "total_ms"]


def _df_to_md(df: pd.DataFrame, floatfmt: str = "{:.4f}") -> str:
    if df.empty:
        return "_empty_"
    cols = list(df.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |",
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


def _class_for(rec: dict, info: dict, split: str) -> str:
    if rec.get("class"):
        return str(rec["class"])
    return str(info.get("class", "unknown"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate baseline vs adaptive")
    parser.add_argument("--limit", type=int, default=None, help="limit images per split (debug)")
    parser.add_argument("--splits", nargs="*", default=["test_sots", "test_rtts"])
    parser.add_argument("--tag", default="main", help="suffix for output files")
    parser.add_argument("--no-visuals", action="store_true")
    args = parser.parse_args()

    params = load_params()
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    if not splits.get("records"):
        raise SystemExit("Missing data/splits.json; run scripts/prepare_data.py")
    limit = args.limit or params.get("evaluation", {}).get("limit_per_split")
    cfg_eval = params.get("evaluation", {})
    seed = int(params.get("project", {}).get("seed", 42))
    results_dir = resolve_path(params.get("evaluation", {}).get("results_dir", "results"))
    images_dir = results_dir / "images"
    results_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    runtime_rows = []
    selected_records = [r for r in splits["records"] if r["split"] in args.splits]
    total = len(selected_records)
    print(f"[eval] {total} records across {args.splits}")
    for idx, rec in enumerate(selected_records, start=1):
        split = rec["split"]
        split_records = [r for r in selected_records if r["split"] == split]
        split_index = split_records.index(rec)
        if limit is not None and split_index >= int(limit):
            continue

        t0 = time.perf_counter()
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        preprocess_ms = (time.perf_counter() - t0) * 1000.0
        clear = None
        if rec.get("has_gt") and rec.get("clear"):
            clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)

        adaptive, adaptive_info = dehaze_adaptive(hazy, params)
        baseline_start = time.perf_counter()
        baseline, _ = dehaze_baseline(hazy, params)
        baseline_ms = (time.perf_counter() - baseline_start) * 1000.0
        haze_class = _class_for(rec, adaptive_info, split)

        for method, out, method_ms in (
            ("baseline", baseline, baseline_ms),
            ("adaptive", adaptive, float(adaptive_info["timing_ms"]["total"])),
        ):
            if clear is not None:
                metrics = evaluate_pair(clear, hazy, out)
            else:
                metrics = no_reference_metrics(hazy, out)
            row = {
                "split": split,
                "id": rec["id"],
                "group": rec.get("group"),
                "source": rec.get("source"),
                "method": method,
                "score": float(adaptive_info["score"]),
                "class": haze_class,
                "beta": rec.get("beta"),
                "has_gt": bool(clear is not None),
                "preprocess_ms": preprocess_ms,
                "method_ms": method_ms,
                "total_ms": preprocess_ms + method_ms,
                **{k: metrics.get(k, np.nan) for k in METRICS},
            }
            rows.append(row)

        runtime_rows.append({
            "split": split, "id": rec["id"], "method": "adaptive",
            "score": adaptive_info["score"], "class": haze_class,
            "density_ms": adaptive_info["timing_ms"]["density"],
            "dcp_ms": adaptive_info["timing_ms"]["dcp"],
            "enhance_ms": adaptive_info["timing_ms"]["enhance"],
            "total_ms": adaptive_info["timing_ms"]["total"] + preprocess_ms,
        })

        if (not args.no_visuals and cfg_eval.get("save_visuals", True)
                and split_index < int(cfg_eval.get("visuals_per_split", 6))):
            out_dir = images_dir / split
            written = {"hazy": hazy, "baseline": baseline, "adaptive": adaptive}
            if clear is not None:
                written["clear"] = clear
            for name, image in written.items():
                write_rgb(out_dir / f"{rec['id']}__{name}.png", image)
        if idx % 25 == 0 or idx == total:
            print(f"[eval] {idx}/{total}")

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "metrics_per_image.csv", index=False)
    runtime_df = pd.DataFrame(runtime_rows)
    runtime_df.to_csv(results_dir / "runtime.csv", index=False)

    # ---------------- summaries -------------------------------------------
    summary_rows = []
    for split in sorted(df["split"].unique()):
        split_df = df[df["split"] == split]
        classes = ["all"] + [c for c in ("light", "moderate", "heavy") if c in set(split_df["class"])]
        for cls in classes:
            subset = split_df if cls == "all" else split_df[split_df["class"] == cls]
            for method in ("baseline", "adaptive"):
                m = subset[subset["method"] == method]
                if m.empty:
                    continue
                for metric in SUMMARY_METRICS:
                    values = m[metric].replace([np.inf, -np.inf], np.nan).dropna()
                    if values.empty:
                        continue
                    summary_rows.append({
                        "split": split, "class": cls, "method": method, "metric": metric,
                        "mean": float(values.mean()), "std": float(values.std(ddof=1)) if len(values) > 1 else 0.0,
                        "median": float(values.median()), "n": int(len(values)),
                    })
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(results_dir / "metrics_summary.csv", index=False)

    # key result table: one row per split/class/method
    key = summary[summary["metric"].isin(["psnr", "ssim", "entropy_gain",
                                          "contrast_improvement", "edge_preservation",
                                          "total_ms"])]
    pivot = key.pivot_table(index=["split", "class", "method"], columns="metric",
                            values="mean", aggfunc="first").reset_index()
    pivot.to_csv(results_dir / "results_table.csv", index=False)
    (results_dir / "results_table.md").write_text(
        "# Baseline vs adaptive (mean per split / haze class)\n\n" + _df_to_md(pivot) + "\n",
        encoding="utf-8",
    )

    # ---------------- paired comparison ------------------------------------
    comp_rows = []
    for split in sorted(df["split"].unique()):
        split_df = df[df["split"] == split]
        classes = ["all"] + [c for c in ("light", "moderate", "heavy") if c in set(split_df["class"])]
        for cls in classes:
            subset = split_df if cls == "all" else split_df[split_df["class"] == cls]
            base = subset[subset["method"] == "baseline"].set_index("id")
            adap = subset[subset["method"] == "adaptive"].set_index("id")
            common = base.index.intersection(adap.index)
            if len(common) == 0:
                continue
            for metric in METRICS:
                a = adap.loc[common, metric].to_numpy(dtype=float)
                b = base.loc[common, metric].to_numpy(dtype=float)
                test = paired_test(a, b)
                comp_rows.append({
                    "split": split, "class": cls, "metric": metric,
                    "n": test["n"],
                    "baseline_mean": float(np.nanmean(b)) if len(b) else np.nan,
                    "adaptive_mean": float(np.nanmean(a)) if len(a) else np.nan,
                    "mean_diff": test["mean_diff"],
                    "win_rate": test["win_rate"],
                    "p_value": test.get("p_value", np.nan),
                    **{k: test[k] for k in ("adaptive_wins", "baseline_wins", "ties")},
                })
    comparison = pd.DataFrame(comp_rows)
    comparison.to_csv(results_dir / "comparison.csv", index=False)

    # ---------------- runtime + key numbers --------------------------------
    runtime_summary = []
    for split in sorted(runtime_df["split"].unique()):
        sub = runtime_df[runtime_df["split"] == split]
        runtime_summary.append({
            "split": split, "n": len(sub),
            "density_ms": float(sub["density_ms"].mean()),
            "dcp_ms": float(sub["dcp_ms"].mean()),
            "enhance_ms": float(sub["enhance_ms"].mean()),
            "total_ms": float(sub["total_ms"].mean()),
            "total_std_ms": float(sub["total_ms"].std(ddof=1)) if len(sub) > 1 else 0.0,
            "fps": float(1000.0 / sub["total_ms"].mean()) if sub["total_ms"].mean() > 0 else np.nan,
        })
    runtime_summary = pd.DataFrame(runtime_summary)
    runtime_summary.to_csv(results_dir / "runtime_summary.csv", index=False)

    def _mean(split, method, metric):
        sub = df[(df["split"] == split) & (df["method"] == method)]
        return float(sub[metric].mean()) if not sub.empty else float("nan")

    key_numbers = {
        "created": date.today().isoformat(),
        "splits": sorted(df["split"].unique().tolist()),
        "n_images": {s: int(df[(df["split"] == s) & (df["method"] == "adaptive")].shape[0])
                     for s in sorted(df["split"].unique())},
        "baseline_sots": {"psnr": _mean("test_sots", "baseline", "psnr"),
                          "ssim": _mean("test_sots", "baseline", "ssim")},
        "adaptive_sots": {"psnr": _mean("test_sots", "adaptive", "psnr"),
                          "ssim": _mean("test_sots", "adaptive", "ssim")},
        "runtime_ms": json.loads(runtime_summary.to_json(orient="records")),
        "class_counts": {
            f"{split}|{cls}": int(count)
            for (split, cls), count in df[df["method"] == "adaptive"].groupby(["split", "class"]).size().items()
        },
        "density_validation": load_json("results/density_validation_summary.json", default={}),
        "classifier": load_json("results/selector_classifier.json", default={}),
    }

    with open(results_dir / "key_numbers.json", "w", encoding="utf-8") as fh:
        json.dump(key_numbers, fh, indent=2)
        fh.write("\n")

    # ---------------- markdown report --------------------------------------
    lines = [
        "# Evaluation summary",
        "",
        f"Generated: {date.today().isoformat()}  ",
        f"Splits: {', '.join(sorted(df['split'].unique()))}",
        "",
        "## Results table (mean)",
        "",
        _df_to_md(pivot),
        "",
        "## Paired comparison (adaptive - baseline)",
        "",
    ]
    comp_view = comparison[comparison["class"] == "all"][
        ["split", "metric", "n", "baseline_mean", "adaptive_mean", "mean_diff", "win_rate", "p_value"]
    ] if not comparison.empty else comparison
    lines.append(_df_to_md(comp_view))
    lines += ["", "## Runtime (mean, includes preprocessing)", "",
              _df_to_md(runtime_summary), "",
              "## Per-image data", "",
              "See `metrics_per_image.csv`, `comparison.csv`, `results_table.csv`."]
    (results_dir / "evaluation_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[eval] wrote results/metrics_per_image.csv ({len(df)} rows)")
    print(f"[eval] SOTS baseline PSNR={key_numbers['baseline_sots']['psnr']:.3f} "
          f"SSIM={key_numbers['baseline_sots']['ssim']:.4f}")
    print(f"[eval] SOTS adaptive PSNR={key_numbers['adaptive_sots']['psnr']:.3f} "
          f"SSIM={key_numbers['adaptive_sots']['ssim']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
