"""Generate all report figures from saved results (and a few recomputed examples)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline import dehaze_baseline  # noqa: E402
from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb, write_rgb  # noqa: E402
from src.pipeline import dehaze_adaptive  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402

CLASSES = ("light", "moderate", "heavy")
CLASS_COLORS = {"light": "#4C9F70", "moderate": "#E3A72F", "heavy": "#B4436C"}


def _setup() -> None:
    plt.rcParams.update({
        "figure.dpi": 120,
        "savefig.dpi": 150,
        "font.size": 9,
        "axes.titlesize": 10,
        "axes.labelsize": 9,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
    })


def _image_cache(rec: dict, params: dict) -> dict:
    """Return hazy/clear/baseline/adaptive/transmission for one record."""
    hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
    clear = None
    if rec.get("has_gt") and rec.get("clear"):
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
    baseline, _ = dehaze_baseline(hazy, params)
    adaptive, info = dehaze_adaptive(hazy, params)
    return {
        "hazy": hazy, "clear": clear, "baseline": baseline,
        "adaptive": adaptive, "transmission": info["transmission"],
        "class": rec.get("class") or info["class"], "score": info["score"],
        "info": info, "id": rec["id"],
    }


def _show(ax, img, title, cmap=None):
    if img is None:
        ax.axis("off")
        return
    if img.ndim == 2:
        ax.imshow(img, cmap=cmap or "gray", vmin=0, vmax=1)
    else:
        ax.imshow(np.clip(img, 0, 1))
    ax.set_title(title, fontsize=8)
    ax.axis("off")


def figure_score_vs_beta(results: Path, figures: Path) -> None:
    path = results / "density_validation.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    summary_path = results / "density_validation_summary.json"
    summary = load_json(summary_path, default={}) if summary_path.exists() else {}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    ax = axes[0]
    for scene, group in df.groupby("scene"):
        group = group.sort_values("beta")
        ax.plot(group["beta"], group["score"], marker="o", lw=0.9, alpha=0.65,
                label=f"scene {scene}")
    mean_curve = df.groupby("beta")["score"].mean().sort_index()
    ax.plot(mean_curve.index, mean_curve.values, color="black", lw=2, marker="s",
            label="mean")
    ax.set_xlabel("haze coefficient beta")
    ax.set_ylabel("estimated fog-density score")
    ax.set_title("Score vs beta (same clear scene, increasing haze)")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(alpha=0.25)
    if summary:
        ax.text(0.02, 0.98,
                f"Spearman overall = {summary.get('spearman_overall', float('nan')):.3f}\n"
                f"within-scene mean = {summary.get('spearman_within_scene_mean', float('nan')):.3f}",
                transform=ax.transAxes, va="top", fontsize=8,
                bbox=dict(boxstyle="round", fc="white", ec="0.7"))
    ax.legend(fontsize=5, ncol=2, loc="lower right")
    # beta by class
    ax = axes[1]
    for cls in CLASSES:
        sub = df[df["class"] == cls]
        if sub.empty:
            continue
        ax.scatter(sub["beta"], sub["score"], s=18, alpha=0.75,
                   color=CLASS_COLORS[cls], label=cls)
    ax.set_xlabel("haze coefficient beta")
    ax.set_ylabel("fog-density score")
    ax.set_title("Score by ground-truth haze class")
    ax.set_ylim(-0.02, 1.02)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(figures / "score_vs_beta.png", bbox_inches="tight")
    plt.close(fig)


def figure_score_histogram(results: Path, figures: Path) -> None:
    path = results / "metrics_per_image.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    df = df[df["method"] == "adaptive"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.2))
    for ax, split in zip(axes, ["test_sots", "test_rtts"]):
        sub = df[df["split"] == split]
        if sub.empty:
            ax.axis("off")
            continue
        ax.hist(sub["score"], bins=20, color="#4C72B0", alpha=0.8, edgecolor="white")
        ax.set_title(f"Fog-density score distribution - {split}")
        ax.set_xlabel("score")
        ax.set_ylabel("images")
        ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(figures / "score_histograms.png", bbox_inches="tight")
    plt.close(fig)


def _pick_reps(records: list[dict], params: dict, per_class: int = 2) -> dict[str, list[dict]]:
    estimator = DensityEstimator.from_config(params)
    selector = AdaptiveSelector(params)
    picked: dict[str, list[dict]] = {c: [] for c in CLASSES}
    for rec in records:
        if not rec.get("has_gt"):
            continue
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        score = estimator.score(hazy)["score"]
        label = rec.get("class") or selector.classify(score)
        if len(picked[label]) < per_class:
            picked[label].append(rec)
        if all(len(v) >= per_class for v in picked.values()):
            break
    return picked


def figure_before_after(records: list[dict], params: dict, figures: Path,
                        per_class: int = 2) -> None:
    reps = _pick_reps(records, params, per_class)
    n_rows = sum(len(v) for v in reps.values())
    if n_rows == 0:
        return
    fig, axes = plt.subplots(n_rows, 4, figsize=(9, 2.3 * n_rows))
    if n_rows == 1:
        axes = np.expand_dims(axes, 0)
    row = 0
    for cls in CLASSES:
        for rec in reps[cls]:
            data = _image_cache(rec, params)
            _show(axes[row, 0], data["hazy"], f"{cls} - hazy\n(data)")
            _show(axes[row, 1], data["baseline"], "baseline DCP\n(fixed params)")
            _show(axes[row, 2], data["adaptive"], "adaptive\n(this work)")
            _show(axes[row, 3], data["clear"], "clear GT")
            row += 1
    fig.suptitle("Qualitative comparison by estimated haze class", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "before_after_by_class.png", bbox_inches="tight")
    plt.close(fig)


def figure_transmission(records: list[dict], params: dict, figures: Path) -> None:
    reps = _pick_reps(records, params, per_class=1)
    picked = [rec for cls in CLASSES for rec in reps[cls]]
    if not picked:
        return
    fig, axes = plt.subplots(len(picked), 3, figsize=(7.5, 2.3 * len(picked)))
    if len(picked) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(picked):
        data = _image_cache(rec, params)
        _show(axes[row, 0], data["hazy"], f"hazy - {data['class']}")
        _show(axes[row, 1], data["transmission"], "transmission t(x)",
              cmap="viridis")
        _show(axes[row, 2], data["adaptive"], "dehazed")
        axes[row, 1].text(0.02, 0.03, f"mean t = {data['info']['mean_transmission']:.2f}",
                          transform=axes[row, 1].transAxes, fontsize=7, color="white",
                          bbox=dict(boxstyle="round", fc="black", alpha=0.5))
    fig.suptitle("Estimated transmission maps", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "transmission_maps.png", bbox_inches="tight")
    plt.close(fig)


def figure_metrics_by_class(results: Path, figures: Path) -> None:
    path = results / "results_table.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    df = df[df["split"] == "test_sots"]
    if df.empty:
        return
    metrics = [("psnr", "PSNR (dB)"), ("ssim", "SSIM"),
               ("entropy_gain", "entropy gain (bits)"),
               ("edge_preservation", "edge preservation ratio")]
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.2))
    x = np.arange(len(CLASSES))
    width = 0.36
    for ax, (metric, label) in zip(axes, metrics):
        base_vals, adap_vals = [], []
        for cls in CLASSES:
            sub = df[df["class"] == cls]
            b = sub[sub["method"] == "baseline"][metric]
            a = sub[sub["method"] == "adaptive"][metric]
            base_vals.append(float(b.mean()) if not b.empty else np.nan)
            adap_vals.append(float(a.mean()) if not a.empty else np.nan)
        ax.bar(x - width / 2, base_vals, width, label="baseline", color="#8C8C8C")
        ax.bar(x + width / 2, adap_vals, width, label="adaptive", color="#4C72B0")
        ax.set_xticks(x)
        ax.set_xticklabels(CLASSES)
        ax.set_title(label)
        ax.grid(alpha=0.2, axis="y")
    axes[0].legend(fontsize=7)
    fig.suptitle("Metrics by estimated haze class (SOTS test)", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "metrics_by_class.png", bbox_inches="tight")
    plt.close(fig)


def figure_failures(results: Path, records: list[dict], params: dict, figures: Path) -> None:
    path = results / "metrics_per_image.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    adap = df[(df["split"] == "test_sots") & (df["method"] == "adaptive")].copy()
    if adap.empty:
        return
    adap = adap.sort_values("ssim").drop_duplicates("id").head(3)
    by_id = {rec["id"]: rec for rec in records}
    picked = [by_id[i] for i in adap["id"] if i in by_id]
    if not picked:
        return
    fig, axes = plt.subplots(len(picked), 4, figsize=(9, 2.3 * len(picked)))
    if len(picked) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(picked):
        data = _image_cache(rec, params)
        _show(axes[row, 0], data["hazy"], "hazy")
        _show(axes[row, 1], data["clear"], "clear GT")
        _show(axes[row, 2], data["baseline"], "baseline")
        _show(axes[row, 3], data["adaptive"],
              f"adaptive (SSIM={adap[adap['id'] == rec['id']]['ssim'].values[0]:.3f})")
    fig.suptitle("Failure cases (lowest adaptive SSIM; included honestly)", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "failure_cases.png", bbox_inches="tight")
    plt.close(fig)


def figure_rtts(results: Path, records: list[dict], params: dict, figures: Path) -> None:
    rtts = [r for r in records if r["split"] == "test_rtts"][:4]
    if not rtts:
        return
    fig, axes = plt.subplots(len(rtts), 3, figsize=(7.5, 2.2 * len(rtts)))
    if len(rtts) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(rtts):
        data = _image_cache(rec, params)
        _show(axes[row, 0], data["hazy"], f"real-style hazy ({data['class']})")
        _show(axes[row, 1], data["baseline"], "baseline")
        _show(axes[row, 2], data["adaptive"], "adaptive")
    fig.suptitle("No-reference RTTS-style examples", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "qualitative_rtts.png", bbox_inches="tight")
    plt.close(fig)


def figure_ablations(results: Path, figures: Path) -> None:
    path = results / "ablations.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    if df.empty:
        return
    metrics = [("psnr", "PSNR (dB)", "#4C72B0"), ("ssim", "SSIM", "#55A868"),
               ("entropy_gain", "entropy gain", "#C44E52")]
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, (metric, label, color) in zip(axes, metrics):
        sub = df.dropna(subset=[metric])
        ax.barh(sub["variant"], sub[metric], color=color, alpha=0.85)
        ax.set_title(label)
        ax.invert_yaxis()
        ax.grid(alpha=0.2, axis="x")
    fig.suptitle("Ablation study", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "ablations.png", bbox_inches="tight")
    plt.close(fig)


def figure_runtime(results: Path, figures: Path) -> None:
    path = results / "runtime_summary.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    if df.empty:
        return
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.bar(df["split"], df["total_ms"], color="#4C72B0", alpha=0.85)
    for i, value in enumerate(df["total_ms"]):
        ax.text(i, value, f"{value:.0f} ms\n({1000 / value:.1f} FPS)",
                ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("mean time per image (ms)")
    ax.set_title("Runtime (CPU, includes preprocessing)")
    ax.grid(alpha=0.2, axis="y")
    fig.tight_layout()
    fig.savefig(figures / "runtime.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate report figures")
    parser.add_argument("--splits", nargs="*", default=["test_sots", "test_rtts"])
    args = parser.parse_args()
    _setup()
    params = load_params()
    results = resolve_path(params.get("evaluation", {}).get("results_dir", "results"))
    figures = results / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] in args.splits]
    test_sots = [r for r in records if r["split"] == "test_sots"]

    figure_score_vs_beta(results, figures)
    figure_score_histogram(results, figures)
    if test_sots:
        figure_before_after(test_sots, params, figures, per_class=2)
        figure_transmission(test_sots, params, figures)
        figure_failures(results, test_sots, params, figures)
    figure_rtts(results, records, params, figures)
    figure_metrics_by_class(results, figures)
    figure_ablations(results, figures)
    figure_runtime(results, figures)
    print(f"[figures] wrote {len(list(figures.glob('*.png')))} figures to {figures}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
