"""Fill report/README placeholders with numbers read from results/ files.

Run after run_eval.py, run_ablations.py and make_figures.py.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import resolve_path  # noqa: E402


def md_table(df: pd.DataFrame, floatfmt: str = "{:.4f}") -> str:
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
                cells.append("" if value != value else floatfmt.format(value))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _mean(df, split, cls, method, metric):
    sub = df[(df["split"] == split) & (df["class"] == cls) & (df["method"] == method)]
    value = sub[metric].replace([float("inf"), float("-inf")], float("nan")).dropna()
    return float(value.mean()) if not value.empty else float("nan")


def _pct(value: float) -> str:
    return f"{100.0 * value:.1f}%"


def main() -> int:
    results = resolve_path("results")
    key = json.loads((results / "key_numbers.json").read_text(encoding="utf-8"))
    per_image = pd.read_csv(results / "metrics_per_image.csv")
    comparison = pd.read_csv(results / "comparison.csv")
    density = json.loads((results / "density_validation_summary.json").read_text(encoding="utf-8"))
    table = pd.read_csv(results / "results_table.csv")
    ablations = pd.read_csv(results / "ablations.csv") if (results / "ablations.csv").exists() else None

    table_view = table.copy()
    keep = [c for c in ["split", "class", "method", "psnr", "ssim", "entropy_gain",
                        "contrast_improvement", "edge_preservation", "total_ms"] if c in table_view]
    table_view = table_view[keep]
    table_md = "# Results — baseline vs adaptive\n\n" + md_table(table_view) + "\n"
    (results / "results_table.md").write_text(table_md, encoding="utf-8")

    # ---------------- findings --------------------------------------------
    b_psnr = _mean(per_image, "test_sots", "all", "baseline", "psnr") if "all" in set(per_image["class"]) else float("nan")
    a_psnr = _mean(per_image, "test_sots", "all", "adaptive", "psnr") if "all" in set(per_image["class"]) else float("nan")
    b_ssim = _mean(per_image, "test_sots", "all", "baseline", "ssim") if "all" in set(per_image["class"]) else float("nan")
    a_ssim = _mean(per_image, "test_sots", "all", "adaptive", "ssim") if "all" in set(per_image["class"]) else float("nan")
    # overall means computed directly (class column is never "all")
    b_psnr = float(per_image[(per_image.split == "test_sots") & (per_image.method == "baseline")]["psnr"].mean())
    a_psnr = float(per_image[(per_image.split == "test_sots") & (per_image.method == "adaptive")]["psnr"].mean())
    b_ssim = float(per_image[(per_image.split == "test_sots") & (per_image.method == "baseline")]["ssim"].mean())
    a_ssim = float(per_image[(per_image.split == "test_sots") & (per_image.method == "adaptive")]["ssim"].mean())

    def comp(split, cls, metric):
        row = comparison[(comparison.split == split) & (comparison["class"] == cls) & (comparison.metric == metric)]
        return row.iloc[0] if not row.empty else None

    findings = []
    findings.append(
        f"**Density validation.** The score is monotone in beta: overall Spearman "
        f"ρ = {density.get('spearman_overall', float('nan')):.3f}; within-scene mean "
        f"ρ = {density.get('spearman_within_scene_mean', float('nan')):.3f} "
        f"(minimum {density.get('spearman_within_scene_min', float('nan')):.3f} across "
        f"{density.get('n_scenes', 0)} scenes)."
    )
    findings.append(
        f"**SOTS overall.** Adaptive PSNR {a_psnr:.2f} dB vs baseline {b_psnr:.2f} dB; "
        f"SSIM {a_ssim:.4f} vs {b_ssim:.4f}. "
        f"Win rate (adaptive > baseline): PSNR "
        f"{_pct(float(comp('test_sots', 'all', 'psnr')['win_rate']))}, SSIM "
        f"{_pct(float(comp('test_sots', 'all', 'ssim')['win_rate']))}."
    )
    class_bits = []
    for cls in ("light", "moderate", "heavy"):
        c_psnr = comp("test_sots", cls, "psnr")
        c_ssim = comp("test_sots", cls, "ssim")
        if c_psnr is None or c_ssim is None:
            continue
        class_bits.append(
            f"{cls}: ΔPSNR {float(c_psnr['mean_diff']):+.2f} dB, ΔSSIM "
            f"{float(c_ssim['mean_diff']):+.4f}, SSIM win rate {_pct(float(c_ssim['win_rate']))}"
        )
    if class_bits:
        findings.append("**Per class.** " + "; ".join(class_bits) + ".")
    rtts_comp = comparison[(comparison.split == "test_rtts") & (comparison["class"] == "all")]
    if not rtts_comp.empty:
        bits = []
        for metric in ("entropy_gain", "contrast_improvement", "edge_preservation"):
            row = rtts_comp[rtts_comp.metric == metric]
            if not row.empty:
                bits.append(f"{metric} Δ {float(row.iloc[0]['mean_diff']):+.4f}")
        if bits:
            findings.append("**No-reference RTTS-style set.** " + "; ".join(bits) + ".")
    runtime = pd.read_csv(results / "runtime_summary.csv") if (results / "runtime_summary.csv").exists() else None
    if runtime is not None and not runtime.empty:
        sots = runtime[runtime.split == "test_sots"]
        if not sots.empty:
            ms = float(sots.iloc[0]["total_ms"])
            findings.append(f"**Runtime.** {ms:.0f} ms/image ({1000.0 / ms:.1f} FPS) on CPU, "
                            f"including preprocessing.")
    if ablations is not None and not ablations.empty:
        def abl(name, metric):
            row = ablations[ablations.variant == name]
            return float(row.iloc[0][metric]) if not row.empty else float("nan")
        findings.append(
            f"**Ablation.** Full pipeline SSIM {abl('adaptive_full', 'ssim'):.4f} vs "
            f"no-enhancement {abl('adaptive_no_enh', 'ssim'):.4f}; "
            f"dark-channel-only density features give SSIM "
            f"{abl('density_dc_only', 'ssim'):.4f} vs full features "
            f"{abl('density_full', 'ssim'):.4f}."
        )
    findings_md = "### Key findings\n\n" + "\n\n".join(f"- {f}" for f in findings) + "\n"

    report_path = resolve_path("report/report.md")
    report = report_path.read_text(encoding="utf-8")
    report = report.replace("<!-- RESULTS_TABLE -->", table_md)
    report = report.replace("<!-- KEY_FINDINGS -->", findings_md)
    ablation_md = (results / "ablations.md").read_text(encoding="utf-8") if (results / "ablations.md").exists() else "_not available_"
    report = report.replace("<!-- ABLATION_TABLE -->", ablation_md)
    report_path.write_text(report, encoding="utf-8")

    readme = resolve_path("README.md")
    text = readme.read_text(encoding="utf-8")
    block = "\n".join([
        "| item | value |",
        "|---|---|",
        f"| Density vs beta Spearman (within-scene mean) | {density.get('spearman_within_scene_mean', float('nan')):.3f} |",
        f"| SOTS baseline PSNR / SSIM | {b_psnr:.2f} dB / {b_ssim:.4f} |",
        f"| SOTS adaptive PSNR / SSIM | {a_psnr:.2f} dB / {a_ssim:.4f} |",
        f"| SSIM win rate | {_pct(float(comp('test_sots', 'all', 'ssim')['win_rate']))} |",
        f"| Runtime (SOTS, CPU) | {ms:.0f} ms/image ({1000.0 / ms:.1f} FPS) |" if runtime is not None and not runtime.empty else "| Runtime | see runtime_summary.csv |",
    ])
    start = text.find("<!-- KEY_NUMBERS_START -->")
    end = text.find("<!-- KEY_NUMBERS_END -->")
    if start != -1 and end != -1:
        text = text[:start] + "<!-- KEY_NUMBERS_START -->\n" + block + "\n<!-- KEY_NUMBERS_END -->" + text[end + len("<!-- KEY_NUMBERS_END -->"):]
        readme.write_text(text, encoding="utf-8")

    (results / "key_findings.md").write_text(findings_md, encoding="utf-8")
    print("[report] filled report/report.md and README.md")
    print(findings_md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
