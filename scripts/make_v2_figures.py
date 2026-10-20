"""Generate v2 report figures (written as results/figures/v2_*.png)."""
from __future__ import annotations

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

from src.baseline import run  # noqa: E402
from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.pipeline import dehaze_adaptive, dehaze_adaptive_v2  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402
from src.sky import sky_mask  # noqa: E402

CLASSES = ("light", "moderate", "heavy")


def _setup() -> None:
    plt.rcParams.update({"figure.dpi": 120, "savefig.dpi": 150, "font.size": 9,
                         "axes.titlesize": 10, "axes.labelsize": 9,
                         "figure.facecolor": "white", "axes.facecolor": "white"})


def _show(ax, img, title, cmap=None):
    if img is None:
        ax.axis("off")
        return
    if img.ndim == 2:
        ax.imshow(np.clip(img, 0, 1), cmap=cmap or "gray", vmin=0, vmax=1)
    else:
        ax.imshow(np.clip(img, 0, 1))
    ax.set_title(title, fontsize=8)
    ax.axis("off")


def _v2_a(params: dict, tuned: dict) -> dict:
    v2 = {"enabled": True,
          "airlight": {"method": "v2"},
          "sky": {"enabled": True, "t_floor": 0.25, "blend": 0.25},
          "local_density": {"enabled": False},
          "enhance": {"local_blend": False},
          "retinex": {"fast": False, "scale": 0.5}}
    tuned_v2 = tuned.get("v2", {})
    for key in ("sky", "airlight"):
        if isinstance(tuned_v2.get(key), dict):
            v2.setdefault(key, {}).update(tuned_v2[key])
    return v2


def figure_failure_cases(params: dict, tuned: dict, records: list[dict], figures: Path) -> None:
    path = resolve_path("results/metrics_per_image.csv")
    if not path.exists():
        return
    df = pd.read_csv(path)
    picked = (df[(df.split == "test_sots") & (df.method == "adaptive")]
              .sort_values("ssim").drop_duplicates("id").head(3))
    by_id = {rec["id"]: rec for rec in records}
    items = [by_id[i] for i in picked["id"] if i in by_id]
    if not items:
        return
    v2a = _v2_a(params, tuned)
    fig, axes = plt.subplots(len(items), 4, figsize=(9, 2.3 * len(items)))
    if len(items) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(items):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        v1, _ = dehaze_adaptive(hazy, params)
        out, info = dehaze_adaptive_v2(hazy, params, v2=v2a)
        _show(axes[row, 0], hazy, "hazy")
        _show(axes[row, 1], clear, "clear GT")
        _show(axes[row, 2], v1, "v1 adaptive")
        sky_px = int(info["sky_mask"].sum()) if info["sky_mask"] is not None else 0
        _show(axes[row, 3], out, f"v2-A (airlight+sky, sky px={sky_px})")
    fig.suptitle("v2 Phase A on the v1 failure cases", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "v2_failure_cases.png", bbox_inches="tight")
    plt.close(fig)


def figure_density_maps(params: dict, tuned: dict, records: list[dict], figures: Path) -> None:
    estimator = DensityEstimator.from_config(params)
    selector = AdaptiveSelector(params)
    v2_params = load_v2_params(params)
    picked = []
    for cls in CLASSES:
        for rec in records:
            if rec["split"] != "test_sots":
                continue
            hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
            if selector.classify(estimator.score(hazy)["score"]) == cls:
                picked.append((cls, rec, hazy))
                break
    if not picked:
        return
    fig, axes = plt.subplots(len(picked), 4, figsize=(9, 2.3 * len(picked)))
    if len(picked) == 1:
        axes = np.expand_dims(axes, 0)
    for row, (cls, rec, hazy) in enumerate(picked):
        score_map = estimator.score_map(hazy)
        omega_map, t0_map = selector.parameter_maps(score_map)
        _, info = dehaze_adaptive_v2(hazy, v2_params)
        mask = info["sky_mask"]
        _show(axes[row, 0], hazy, f"{cls} - hazy")
        _show(axes[row, 1], score_map, "local density (smoothed)", cmap="magma")
        _show(axes[row, 2], omega_map, "omega(x)", cmap="viridis")
        overlay = np.clip(hazy, 0, 1).copy()
        if mask is not None and mask.any():
            overlay[mask] = 0.5 * overlay[mask] + 0.5 * np.array([0.1, 0.8, 0.2])
        _show(axes[row, 3], overlay, "sky mask (green)")
    fig.suptitle("v2 local density, omega map and sky mask", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "v2_density_maps.png", bbox_inches="tight")
    plt.close(fig)


def figure_qualitative(params: dict, tuned: dict, records: list[dict], figures: Path) -> None:
    sots = [r for r in records if r["split"] == "test_sots"]
    indoor = [r for r in sots if r.get("group") == "indoor"][:1]
    outdoor = [r for r in sots if r.get("group") == "outdoor"][:1]
    rtts = [r for r in records if r["split"] == "test_rtts"][:2]
    picked = indoor + outdoor + rtts
    if not picked:
        return
    v2_params = load_v2_params(params)
    fig, axes = plt.subplots(len(picked), 6, figsize=(13, 2.2 * len(picked)))
    if len(picked) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(picked):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        dcp, _ = run("dcp", hazy, params)
        cap, _ = run("cap", hazy, params)
        bccr, _ = run("bccr", hazy, params)
        v1, _ = dehaze_adaptive(hazy, params)
        v2, _ = dehaze_adaptive_v2(hazy, v2_params)
        for col, (img, title) in enumerate([
            (hazy, "hazy"), (dcp, "DCP"), (cap, "CAP"), (bccr, "BCCR"),
            (v1, "v1 adaptive"), (v2, "v2 adaptive"),
        ]):
            _show(axes[row, col], img, f"{rec['split']} - {title}")
    fig.suptitle("v2 vs classical baselines and v1", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "v2_qualitative.png", bbox_inches="tight")
    plt.close(fig)


def figure_ablations(figures: Path) -> None:
    path = resolve_path("results/v2_ablations.csv")
    if not path.exists():
        return
    df = pd.read_csv(path)
    metrics = [("psnr", "PSNR (dB)"), ("ssim", "SSIM"), ("ciede2000", "CIEDE2000 (lower)"),
               ("niqe_out", "NIQE (lower)"), ("fade_out", "FADE (lower)")]
    fig, axes = plt.subplots(1, len(metrics), figsize=(16, 3.6))
    for ax, (metric, label) in zip(axes, metrics):
        if metric not in df:
            ax.axis("off")
            continue
        sub = df.dropna(subset=[metric])
        ax.barh(sub["variant"], sub[metric], color="#4C72B0", alpha=0.85)
        ax.set_title(label)
        ax.invert_yaxis()
        ax.grid(alpha=0.2, axis="x")
    fig.suptitle("v2 ablation: one step at a time", fontsize=11)
    fig.tight_layout()
    fig.savefig(figures / "v2_ablations.png", bbox_inches="tight")
    plt.close(fig)


def figure_density_validation(figures: Path) -> None:
    path = resolve_path("results/v2_density_validation.csv")
    if not path.exists():
        return
    df = pd.read_csv(path)
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4))
    for scene, group in df.groupby("scene"):
        group = group.sort_values("beta")
        axes[0].plot(group["beta"], group["local_mean"], marker="o", lw=0.9, alpha=0.6)
    mean_curve = df.groupby("beta")["local_mean"].mean().sort_index()
    axes[0].plot(mean_curve.index, mean_curve.values, color="black", lw=2, marker="s")
    axes[0].set_xlabel("beta")
    axes[0].set_ylabel("mean local density")
    axes[0].set_title("Local density vs beta (validation sweep)")
    axes[0].grid(alpha=0.25)
    axes[1].scatter(df["global"], df["local_mean"], s=16, alpha=0.75)
    axes[1].set_xlabel("global density score")
    axes[1].set_ylabel("mean local density")
    axes[1].set_title("Global vs local density")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(figures / "v2_density_validation.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    _setup()
    params = load_params()
    tuned = load_json(params.get("paths", {}).get("tuned_params_v2",
                                                  "config/tuned_params_v2.json"), default={})
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] in {"test_sots", "test_rtts"}]
    figures = resolve_path("results/figures")
    figures.mkdir(parents=True, exist_ok=True)
    figure_failure_cases(params, tuned, records, figures)
    figure_density_maps(params, tuned, records, figures)
    figure_qualitative(params, tuned, records, figures)
    figure_ablations(figures)
    figure_density_validation(figures)
    print(f"[v2-figures] wrote {len(list(figures.glob('v2_*.png')))} v2 figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
