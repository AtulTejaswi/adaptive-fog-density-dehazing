"""Build clean, presentation-specific figures from the committed results.

All numbers are read from ``results/``; the qualitative panels are regenerated
from the same frozen pipeline used by the evaluation scripts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline import run  # noqa: E402
from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

FIG = ROOT / "results" / "figures"
NAVY = "#0B1F33"
TEAL = "#0E7C86"
AMBER = "#D9822B"
CORAL = "#C8553D"
GRAY = "#6B7A8A"
LIGHT = "#E8EDF2"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
    "axes.edgecolor": "#C9D2DB",
    "axes.labelcolor": NAVY,
    "text.color": NAVY,
    "xtick.color": GRAY,
    "ytick.color": GRAY,
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})


def _load_record(records: dict[str, dict], name: str):
    rec = records[name]
    hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), PARAMS)
    clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), PARAMS)
    return rec, hazy, clear


def _panel(ax, image, title, subtitle=None):
    ax.imshow(np.clip(image, 0, 1))
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title(title, fontsize=11, pad=8, color=NAVY, fontweight="bold")
    if subtitle:
        ax.text(0.5, -0.06, subtitle, transform=ax.transAxes, ha="center",
                va="top", fontsize=8.5, color=GRAY)


def make_teaser(records):
    _, hazy, clear = _load_record(records, "sots_outdoor_0030")
    dcp, _ = run("dcp", hazy, PARAMS)
    v1, _ = run("v1", hazy, PARAMS)
    fig, axes = plt.subplots(2, 2, figsize=(7.4, 6.2))
    _panel(axes[0, 0], hazy, "Hazy input")
    _panel(axes[0, 1], dcp, "Fixed DCP", "same strength everywhere")
    _panel(axes[1, 0], v1, "FogSense (v1)", "density-adaptive, default")
    _panel(axes[1, 1], clear, "Clear ground truth", "SOTS outdoor")
    fig.tight_layout(pad=1.1, h_pad=1.6)
    fig.savefig(FIG / "slide_teaser.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_problem(records):
    _, light_h, _ = _load_record(records, "sots_outdoor_0171")
    _, heavy_h, _ = _load_record(records, "sots_outdoor_0072")
    variants = [
        ("Light haze", light_h, "DCP over-corrects"),
        ("Heavy haze", heavy_h, "DCP under-corrects"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 5.8))
    for r, (label, hazy, note) in enumerate(variants):
        dcp, _ = run("dcp", hazy, PARAMS)
        v1, _ = run("v1", hazy, PARAMS)
        _panel(axes[r, 0], hazy, f"{label} — input")
        _panel(axes[r, 1], dcp, "Fixed DCP")
        _panel(axes[r, 2], v1, "FogSense (v1)")
        axes[r, 0].text(-0.06, 0.5, label, transform=axes[r, 0].transAxes,
                        rotation=90, va="center", ha="right", fontsize=10,
                        color=TEAL, fontweight="bold")
        axes[r, 1].text(0.5, -0.10, note, transform=axes[r, 1].transAxes,
                        ha="center", va="top", fontsize=8.5, color=CORAL)
    fig.suptitle("One fixed correction strength cannot fit every haze level",
                 fontsize=12.5, fontweight="bold", color=NAVY, y=1.01)
    fig.tight_layout(pad=1.0, h_pad=1.9)
    fig.savefig(FIG / "slide_problem.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_qualitative():
    src = Image.open(FIG / "v2_qualitative.png")
    w, h = src.size
    # Keep the two SOTS rows (indoor + outdoor); the RTTS rows live in the report.
    crop = src.crop((0, 0, w, int(h * 0.505)))
    crop.save(FIG / "slide_qualitative.png")


def make_v2_delta():
    data = {
        "Overall (n=243)": (-0.3247, -0.0023),
        "Indoor (n=22)": (0.7465, 0.0118),
        "Outdoor (n=221)": (-0.4314, -0.0037),
    }
    labels = list(data)
    psnr = [v[0] for v in data.values()]
    ssim = [v[1] for v in data.values()]
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.6))
    for ax, vals, title, fmt in (
        (axes[0], psnr, "PSNR change (dB)", "{:+.2f}"),
        (axes[1], ssim, "SSIM change", "{:+.4f}"),
    ):
        colors = [TEAL if v >= 0 else CORAL for v in vals]
        y = np.arange(len(labels))
        ax.barh(y, vals, color=colors, height=0.55, alpha=0.92)
        ax.axvline(0, color=NAVY, lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, loc="left")
        ax.grid(axis="x", color="#E3E8EE", lw=0.8)
        ax.set_axisbelow(True)
        for yi, v in zip(y, vals):
            pad = 0.03 * max(abs(min(vals)), abs(max(vals)), 1e-6)
            ax.text(v + (pad if v >= 0 else -pad), yi, fmt.format(v),
                    va="center", ha="left" if v >= 0 else "right",
                    fontsize=9.5, color=NAVY, fontweight="bold")
        ax.set_xlim(min(vals) - 0.45 * max(abs(min(vals)), 0.1),
                    max(vals) + 0.45 * max(abs(max(vals)), 0.1))
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
    fig.suptitle("v2 minus v1: a real indoor gain, but an outdoor loss",
                 fontsize=12, fontweight="bold", color=NAVY, y=1.04)
    fig.tight_layout(pad=1.2)
    fig.savefig(FIG / "slide_v2_delta.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_ablations():
    a1 = pd.read_csv(ROOT / "results" / "ablations.csv")
    a2 = pd.read_csv(ROOT / "results" / "v2_ablations.csv")
    v1_order = ["baseline_dcp", "adaptive_no_enh", "adaptive_clahe",
                "adaptive_clahe_retinex", "adaptive_full"]
    v2_order = ["v1", "v2_airlight", "v2_airlight_sky", "v2_local_omega",
                "v2_local_enhance"]
    v1_labels = ["DCP", "No enh.", "CLAHE", "CLAHE+Ret.", "Full v1"]
    v2_labels = ["v1", "+airlight", "+sky", "+local ω", "+local enh."]
    a1 = a1.set_index("variant").loc[v1_order]
    a2 = a2.set_index("variant").loc[v2_order]
    fig, axes = plt.subplots(1, 4, figsize=(13.6, 4.3))
    specs = [
        (axes[0], a1["psnr"], v1_labels, "v1 ablation — PSNR (dB)", "{:.2f}", TEAL),
        (axes[1], a1["ssim"], v1_labels, "v1 ablation — SSIM", "{:.4f}", TEAL),
        (axes[2], a2["psnr"], v2_labels, "v2 ablation — PSNR (dB)", "{:.2f}", AMBER),
        (axes[3], a2["ssim"], v2_labels, "v2 ablation — SSIM", "{:.4f}", AMBER),
    ]
    for ax, vals, labels, title, fmt, color in specs:
        y = np.arange(len(labels))
        ax.barh(y, vals, color=color, alpha=0.9, height=0.62)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, loc="left", fontsize=10.5)
        ax.grid(axis="x", color="#E3E8EE", lw=0.8)
        ax.set_axisbelow(True)
        lo, hi = float(np.min(vals)), float(np.max(vals))
        span = max(hi - lo, 0.01)
        pad = 0.02 * span
        for yi, v in zip(y, vals):
            ax.text(v + pad, yi, fmt.format(v), va="center", ha="left",
                    fontsize=8.5, color=NAVY, fontweight="bold")
        ax.set_xlim(lo - 0.22 * span, hi + 0.28 * span)
        for spine in ("top", "right", "left"):
            ax.spines[spine].set_visible(False)
    fig.tight_layout(pad=1.1, w_pad=2.0)
    fig.savefig(FIG / "slide_ablations.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def make_runtime():
    data = [("CAP", 38.2, GRAY), ("DCP", 59.4, GRAY), ("BCCR", 83.1, GRAY),
            ("FogSense v1", 192.3, TEAL), ("FogSense v2", 561.7, AMBER)]
    labels = [d[0] for d in data]
    vals = [d[1] for d in data]
    colors = [d[2] for d in data]
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    y = np.arange(len(labels))
    ax.barh(y, vals, color=colors, alpha=0.92, height=0.6)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("milliseconds per 640-px image (CPU)")
    ax.grid(axis="x", color="#E3E8EE", lw=0.8)
    ax.set_axisbelow(True)
    for yi, v in zip(y, vals):
        ax.text(v + 12, yi, f"{v:.0f} ms", va="center", ha="left",
                fontsize=10, color=NAVY, fontweight="bold")
    ax.set_xlim(0, 680)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    ax.set_title("Runtime on SOTS (same run, identical preprocessing)",
                 loc="left", fontsize=11)
    fig.tight_layout(pad=1.0)
    fig.savefig(FIG / "slide_runtime.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    global PARAMS
    PARAMS = load_params()
    splits = load_json(PARAMS["paths"]["splits"])
    records = {r["id"]: r for r in splits["records"]}
    make_teaser(records)
    make_problem(records)
    make_qualitative()
    make_v2_delta()
    make_ablations()
    make_runtime()
    print("wrote slide assets to", FIG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
