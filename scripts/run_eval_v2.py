"""v2 evaluation: fixed DCP, CAP, BCCR, v1 adaptive and v2 adaptive.

Identical preprocessing for every method.  Writes only ``results/v2_*`` files so
the v1 results stay untouched.  Also reports SOTS indoor/outdoor separately and
a clearly-labelled brightness/colour-match diagnostic.
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

from src.baseline import run  # noqa: E402
from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import (  # noqa: E402
    evaluate_pair_v2,
    no_reference_metrics_v2,
    paired_test,
    psnr,
)
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402

METHODS = ("dcp", "cap", "bccr", "v1", "v2")
METRICS = [
    "psnr", "ssim", "ciede2000", "niqe_out", "fade_out",
    "entropy_gain", "contrast_improvement", "edge_preservation",
    "color_cast_out", "colorfulness_out",
]
EXTRA = ["psnr_matched", "fade_in", "niqe_in"]


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


def _match_to_gt(image: np.ndarray, reference: np.ndarray) -> np.ndarray:
    """Per-channel mean/std match to GT (diagnostic only, never used as a result)."""
    out = image.copy()
    for c in range(3):
        mean_o, std_o = float(out[..., c].mean()), float(out[..., c].std())
        mean_r, std_r = float(reference[..., c].mean()), float(reference[..., c].std())
        out[..., c] = (out[..., c] - mean_o) / (std_o + 1e-6) * std_r + mean_r
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def main() -> int:
    parser = argparse.ArgumentParser(description="v2 comparison evaluation")
    parser.add_argument("--splits", nargs="*", default=["test_sots", "test_rtts"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    params = load_params()
    v2_params = load_v2_params(params)
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] in args.splits]
    if args.limit:
        records = records[: args.limit]
    niqe_model = load_json(params.get("paths", {}).get("niqe_model", "config/niqe_model.json"),
                           default=None)
    estimator = DensityEstimator.from_config(params)
    selector = AdaptiveSelector(params)
    results_dir = resolve_path("results")
    print(f"[v2-eval] {len(records)} images x {len(METHODS)} methods")

    rows = []
    for idx, rec in enumerate(records, start=1):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = None
        if rec.get("has_gt") and rec.get("clear"):
            clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        score = estimator.score(hazy)["score"]
        haze_class = selector.classify(score)
        for method in METHODS:
            active = v2_params if method == "v2" else params
            start = time.perf_counter()
            out, _ = run(method, hazy, active)
            runtime_ms = (time.perf_counter() - start) * 1000.0
            if clear is not None:
                metrics = evaluate_pair_v2(clear, hazy, out, niqe_model, params)
                metrics["psnr_matched"] = psnr(clear, _match_to_gt(out, clear))
            else:
                metrics = no_reference_metrics_v2(hazy, out, niqe_model, params)
            rows.append({
                "split": rec["split"],
                "group": rec.get("group"),
                "id": rec["id"],
                "method": method,
                "class": haze_class,
                "score": float(score),
                "runtime_ms": runtime_ms,
                **{k: metrics.get(k, np.nan) for k in METRICS + EXTRA},
            })
        if idx % 25 == 0 or idx == len(records):
            print(f"[v2-eval] {idx}/{len(records)}")

    df = pd.DataFrame(rows)
    df.to_csv(results_dir / "v2_metrics_per_image.csv", index=False)

    # ---------------- summary by split / group / method -------------------
    def summarize(group_cols):
        agg = {m: (m, "mean") for m in METRICS + ["psnr_matched", "runtime_ms"]}
        return (df.groupby(group_cols).agg(n=("id", "count"), **agg)
                .reset_index())

    overall = summarize(["split", "method"])
    by_group = summarize(["split", "group", "method"])
    overall.to_csv(results_dir / "v2_summary.csv", index=False)
    by_group.to_csv(results_dir / "v2_summary_by_group.csv", index=False)

    # compact results table (one row per split/method)
    cols = ["split", "method", "n", "psnr", "ssim", "ciede2000", "niqe_out",
            "fade_out", "entropy_gain", "contrast_improvement",
            "edge_preservation", "color_cast_out", "runtime_ms"]
    table = overall[[c for c in cols if c in overall.columns]].copy()
    table.to_csv(results_dir / "v2_results_table.csv", index=False)
    (results_dir / "v2_results_table.md").write_text(
        "# v2 comparison (test splits, identical preprocessing)\n\n"
        + _md(table) + "\n\n"
        + "Lower is better for CIEDE2000, NIQE and FADE; higher is better for the rest.\n",
        encoding="utf-8",
    )

    # ---------------- paired comparisons vs v2 ----------------------------
    comparisons = []
    for split in sorted(df["split"].unique()):
        split_df = df[df["split"] == split]
        for metric in ("psnr", "ssim", "ciede2000", "niqe_out", "fade_out",
                       "entropy_gain", "edge_preservation"):
            lower_better = metric in {"ciede2000", "niqe_out", "fade_out"}
            v2 = split_df[split_df.method == "v2"].set_index("id")[metric]
            for other in ("dcp", "cap", "bccr", "v1"):
                base = split_df[split_df.method == other].set_index("id")[metric]
                common = v2.index.intersection(base.index)
                if len(common) == 0:
                    continue
                a = v2.loc[common].to_numpy(dtype=float)
                b = base.loc[common].to_numpy(dtype=float)
                finite = np.isfinite(a) & np.isfinite(b)
                if not np.any(finite):
                    continue
                test = paired_test(a[finite], b[finite])
                improvement = (b[finite] - a[finite]) if lower_better else (a[finite] - b[finite])
                comparisons.append({
                    "split": split, "metric": metric, "v2_vs": other, "n": test["n"],
                    "lower_is_better": bool(lower_better),
                    "v2_mean": float(np.nanmean(a[finite])),
                    "other_mean": float(np.nanmean(b[finite])),
                    "mean_diff": test["mean_diff"],
                    "win_rate_better": float(np.mean(improvement > 0)),
                    "p_value": test.get("p_value", np.nan),
                })
    comparison = pd.DataFrame(comparisons)
    comparison.to_csv(results_dir / "v2_comparison.csv", index=False)

    # ---------------- brightness/colour diagnostic ------------------------
    diag = (df[df.split == "test_sots"].groupby("method")
            .agg(n=("id", "count"), psnr=("psnr", "mean"),
                 psnr_matched=("psnr_matched", "mean")).reset_index())
    diag["gain_from_match"] = diag["psnr_matched"] - diag["psnr"]
    diag.to_csv(results_dir / "v2_brightness_diagnostic.csv", index=False)

    # ---------------- key numbers + markdown ------------------------------
    def mean(split, method, metric):
        sub = df[(df.split == split) & (df.method == method)]
        return float(sub[metric].mean()) if not sub.empty else float("nan")

    key = {
        "created": date.today().isoformat(),
        "n_images": {s: int(df[df.split == s].id.nunique()) for s in sorted(df.split.unique())},
        "methods": list(METHODS),
        "test_sots": {m: {k: mean("test_sots", m, k) for k in
                          ("psnr", "ssim", "ciede2000", "niqe_out", "fade_out", "runtime_ms")}
                      for m in METHODS},
        "test_rtts": {m: {k: mean("test_rtts", m, k) for k in
                          ("entropy_gain", "contrast_improvement", "edge_preservation",
                           "niqe_out", "fade_out", "runtime_ms")}
                      for m in METHODS},
        "brightness_diagnostic": json.loads(diag.to_json(orient="records")),
        "note": "v2 params frozen at tag v2.0-frozen-params before this run.",
    }
    with open(results_dir / "v2_key_numbers.json", "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=2)
        fh.write("\n")

    lines = [
        "# v2 evaluation summary",
        "",
        f"Generated: {date.today().isoformat()}",
        "",
        "## Overall (mean per split / method)",
        "",
        _md(table),
        "",
        "## SOTS indoor / outdoor",
        "",
        _md(by_group[by_group.split == "test_sots"]),
        "",
        "## Paired comparison (v2 - other)",
        "",
        _md(comparison[comparison.split == "test_sots"]),
        "",
        "## Brightness/colour-match diagnostic (SOTS, diagnostic only)",
        "",
        _md(diag),
        "",
    ]
    (results_dir / "v2_evaluation_summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("[v2-eval] wrote results/v2_* files")
    print(_md(table))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
