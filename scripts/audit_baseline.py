"""Baseline fairness / sanity audit.

Checks that the fixed DCP baseline is not accidentally handicapped by the
atmospheric-light estimator, guided filter, or preprocessing.  It does not
change the headline baseline; it only reports diagnostics and creates a
three-example visual check.

Outputs:
  results/baseline_audit.csv
  results/baseline_audit_summary.csv
  results/figures/baseline_sanity.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.dcp import atmospheric_light, dark_channel, dcp_dehaze, recover_radiance, transmission_map  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import evaluate_pair  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402


def _run_with_airlight(img: np.ndarray, airlight: np.ndarray, omega: float,
                       t0: float, patch: int, radius: int, eps: float):
    t = transmission_map(img, airlight, omega=omega, patch_size=patch,
                         guided_radius=radius, guided_eps=eps, t_min=t0)
    out = recover_radiance(img, airlight, t, t0=t0)
    return out, t


def _summary(df: pd.DataFrame) -> pd.DataFrame:
    return (df.groupby("variant", sort=False)
            .agg(n=("id", "count"), psnr=("psnr", "mean"), ssim=("ssim", "mean"),
                 mean_A=("mean_A", "mean"), mean_t=("mean_t", "mean"),
                 clipped_fraction=("clipped_fraction", "mean"))
            .reset_index())


def _figure(records: list[dict], params: dict, results: Path, figures: Path) -> None:
    """Three examples: one per estimated class, hazy / baseline / clear GT."""
    metrics = pd.read_csv(results / "metrics_per_image.csv")
    metrics = metrics[(metrics["split"] == "test_sots") & (metrics["method"] == "adaptive")]
    picked_ids = []
    for cls in ("light", "moderate", "heavy"):
        sub = metrics[metrics["class"] == cls]
        if not sub.empty:
            picked_ids.append(str(sub.iloc[0]["id"]))
    by_id = {str(r["id"]): r for r in records}
    picked = [by_id[i] for i in picked_ids if i in by_id]
    if not picked:
        return
    fig, axes = plt.subplots(len(picked), 3, figsize=(7.6, 2.5 * len(picked)))
    if len(picked) == 1:
        axes = np.expand_dims(axes, 0)
    for row, rec in enumerate(picked):
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        out, _ = dcp_dehaze(
            hazy,
            omega=float(params["dehaze"]["baseline"]["omega"]),
            t0=float(params["dehaze"]["baseline"]["t0"]),
            patch_size=int(params["dehaze"]["baseline"]["patch_size"]),
            guided_radius=int(params["dehaze"]["baseline"]["guided_filter"]["radius"]),
            guided_eps=float(params["dehaze"]["baseline"]["guided_filter"]["eps"]),
        )
        m = evaluate_pair(clear, hazy, out)
        for ax, img, title in (
            (axes[row, 0], hazy, "hazy input"),
            (axes[row, 1], out, f"fixed DCP baseline\nPSNR {m['psnr']:.2f} dB, SSIM {m['ssim']:.3f}"),
            (axes[row, 2], clear, "clear ground truth"),
        ):
            ax.imshow(np.clip(img, 0, 1))
            ax.set_title(title, fontsize=8)
            ax.axis("off")
    fig.suptitle("Baseline sanity check: fixed DCP (omega 0.95, t0 0.10, GF 60/1e-4)", fontsize=10)
    fig.tight_layout()
    fig.savefig(figures / "baseline_sanity.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the fixed DCP baseline")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    params = load_params()
    splits = load_json(params["paths"]["splits"], default={})
    all_test = [r for r in splits.get("records", []) if r["split"] == "test_sots"]
    if args.limit and 0 < args.limit < len(all_test):
        idxs = sorted(set(int(i) for i in np.linspace(0, len(all_test) - 1, args.limit)))
        records = [all_test[i] for i in idxs]
    else:
        records = all_test
    cfg = params["dehaze"]["baseline"]
    gf = cfg["guided_filter"]
    omega, t0, patch = float(cfg["omega"]), float(cfg["t0"]), int(cfg["patch_size"])
    radius, eps = int(gf["radius"]), float(gf["eps"])

    rows = []
    for rec in records:
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)

        variants = {}

        # Current baseline.
        out, info = dcp_dehaze(hazy, omega=omega, t0=t0, patch_size=patch,
                               guided_radius=radius, guided_eps=eps)
        variants["current"] = (out, info["airlight"], info["transmission"])

        # Brightest dark-channel pixel instead of the top-0.1% mean.
        dark = dark_channel(hazy, patch)
        flat = dark.reshape(-1)
        idx = int(np.argmax(flat))
        a_bright = np.clip(hazy.reshape(-1, 3)[idx], 0, 1).astype(np.float32)
        out_b, t_b = _run_with_airlight(hazy, a_bright, omega, t0, patch, radius, eps)
        variants["brightest_dark_pixel"] = (out_b, a_bright, t_b)

        # Top-1% mean atmospheric light (less sensitive to a dark outlier).
        a_top1 = atmospheric_light(hazy, dark, patch, top_percent=1.0)
        out_1, t_1 = _run_with_airlight(hazy, a_top1, omega, t0, patch, radius, eps)
        variants["top_1pct_mean"] = (out_1, a_top1, t_1)

        # No guided filter (diagnostic: how much refinement matters).
        out_g, info_g = dcp_dehaze(hazy, omega=omega, t0=t0, patch_size=patch,
                                   guided_radius=0, guided_eps=eps)
        variants["no_guided_filter"] = (out_g, info_g["airlight"],
                                        info_g["transmission"])

        # No resize/denoise: checks whether preprocessing is the cause of a low score.
        hazy_native = read_rgb(resolve_path(rec["hazy"]))
        clear_native = read_rgb(resolve_path(rec["clear"]))
        if hazy_native.shape == clear_native.shape:
            out_n, info_n = dcp_dehaze(hazy_native, omega=omega, t0=t0, patch_size=patch,
                                       guided_radius=radius, guided_eps=eps)
            n_metrics = evaluate_pair(clear_native, hazy_native, out_n)
            rows.append({
                "id": rec["id"], "variant": "native_no_resize",
                "psnr": n_metrics["psnr"], "ssim": n_metrics["ssim"],
                "mean_A": float(np.mean(info_n["airlight"])),
                "mean_t": float(np.mean(info_n["transmission"])),
                "min_t": float(np.min(info_n["transmission"])),
                "clipped_fraction": float(np.mean((out_n <= 0) | (out_n >= 1))),
            })

        for name, (out_v, a_v, t_v) in variants.items():
            m = evaluate_pair(clear, hazy, out_v)
            rows.append({
                "id": rec["id"], "variant": name,
                "psnr": m["psnr"], "ssim": m["ssim"],
                "mean_A": float(np.mean(a_v)), "mean_t": float(np.mean(t_v)),
                "min_t": float(np.min(t_v)),
                "clipped_fraction": float(np.mean((out_v <= 0) | (out_v >= 1))),
            })

    df = pd.DataFrame(rows)
    results = resolve_path("results")
    results.mkdir(exist_ok=True)
    df.to_csv(results / "baseline_audit.csv", index=False)
    summary = _summary(df)
    summary.to_csv(results / "baseline_audit_summary.csv", index=False)
    figures = results / "figures"
    figures.mkdir(exist_ok=True)
    _figure(all_test, params, results, figures)
    print(summary.to_string(index=False))
    print(f"[audit] wrote {results / 'baseline_audit.csv'} and figures/baseline_sanity.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
