"""Tune the v2-only knobs on the calib split ONLY, with a noise/halo penalty.

Stages:
  1. atmospheric-light method (v1 / v2 / quadtree)
  2. sky t-floor and blend (only on calib images that actually contain sky)
  3. local-enhancement floor (with local density enabled)
  4. fast Retinex on/off (kept only if quality is not materially worse)

Writes ``config/tuned_params_v2.json``.  Never touches test_sots / test_rtts.
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

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import evaluate_pair  # noqa: E402
from src.pipeline import dehaze_adaptive_v2  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402
from src.selector import AdaptiveSelector  # noqa: E402
from src.sky import gradient_magnitude, sky_mask  # noqa: E402

CLASSES = ("light", "moderate", "heavy")


def _penalty(hazy: np.ndarray, out: np.ndarray) -> float:
    """Noise/halo proxy: extra gradient energy in flat regions of the input."""
    grad_in = gradient_magnitude(hazy)
    grad_out = gradient_magnitude(out)
    flat = grad_in <= np.percentile(grad_in, 20)
    if not np.any(flat):
        return 0.0
    ratio = float(np.mean(grad_out[flat])) / (float(np.mean(grad_in[flat])) + 1e-6)
    return float(np.clip((ratio - 1.0) / 2.0, 0.0, 1.0))


def _objective(metrics: dict, cfg: dict) -> float:
    ssim_term = float(metrics.get("ssim", 0.0))
    psnr_term = min(max(float(metrics.get("psnr", 0.0)) / float(cfg.get("psnr_reference", 40.0)), 0.0), 1.0)
    edge_term = min(max(float(metrics.get("edge_preservation", 0.0)) / 1.25, 0.0), 1.0)
    return (float(cfg.get("ssim_weight", 0.5)) * ssim_term
            + float(cfg.get("psnr_weight", 0.3)) * psnr_term
            + float(cfg.get("edge_weight", 0.2)) * edge_term
            - 0.10 * float(metrics.get("penalty", 0.0)))


def _evaluate(images: list[dict], params: dict, v2: dict, obj_cfg: dict) -> dict:
    rows = []
    for item in images:
        out, info = dehaze_adaptive_v2(item["hazy"], params, v2=v2)
        metrics = evaluate_pair(item["clear"], item["hazy"], out)
        metrics["penalty"] = _penalty(item["hazy"], out)
        metrics["objective"] = _objective(metrics, obj_cfg)
        metrics["ms"] = float(info["timing_ms"]["total"])
        rows.append(metrics)
    return {
        "n": len(rows),
        "psnr": float(np.mean([r["psnr"] for r in rows])),
        "ssim": float(np.mean([r["ssim"] for r in rows])),
        "edge_preservation": float(np.mean([r["edge_preservation"] for r in rows])),
        "penalty": float(np.mean([r["penalty"] for r in rows])),
        "objective": float(np.mean([r["objective"] for r in rows])),
        "ms": float(np.mean([r["ms"] for r in rows])),
    }


def _base_v2(params: dict) -> dict:
    v2 = copy.deepcopy(params.get("v2", {}))
    v2["airlight"]["method"] = "v1"
    v2["sky"]["enabled"] = False
    v2["local_density"]["enabled"] = False
    v2["enhance"]["local_blend"] = False
    v2["retinex"]["fast"] = False
    return v2


def main() -> int:
    parser = argparse.ArgumentParser(description="Tune v2 knobs on calib only")
    parser.add_argument("--per-class", type=int, default=12)
    args = parser.parse_args()

    params = load_params()
    cfg = params.get("tuning", {})
    obj_cfg = dict(cfg.get("objective", {}))
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] == "calib" and r.get("has_gt")]
    if not records:
        raise SystemExit("No calib records with ground truth")

    estimator = DensityEstimator.from_config(params)
    selector = AdaptiveSelector(params)
    by_class: dict[str, list[dict]] = {c: [] for c in CLASSES}
    for rec in records:
        hazy = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        label = selector.classify(estimator.score(hazy)["score"])
        if len(by_class[label]) >= args.per_class:
            continue
        clear = preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
        by_class[label].append({"id": rec["id"], "hazy": hazy, "clear": clear})
    images = [item for cls in CLASSES for item in by_class[cls]]
    print(f"[tune-v2] {len(images)} calib images: "
          f"{ {c: len(v) for c, v in by_class.items()} }")

    sky_cfg = params.get("v2", {}).get("sky", {})
    sky_images = [item for item in images
                  if sky_mask(item["hazy"], sky_cfg).mean() >= 0.01]
    print(f"[tune-v2] images with sky: {len(sky_images)}")

    log: dict[str, list[dict]] = {}

    # stage 1: airlight
    stage1 = []
    for method in ("v1", "v2", "quadtree"):
        v2 = _base_v2(params)
        v2["airlight"]["method"] = method
        metrics = _evaluate(images, params, v2, obj_cfg)
        stage1.append({"method": method, **metrics})
        print(f"  [airlight] {method:8s} obj={metrics['objective']:.4f} "
              f"psnr={metrics['psnr']:.2f} ssim={metrics['ssim']:.4f}")
    log["airlight"] = stage1
    best_method = max(stage1, key=lambda r: r["objective"])["method"]

    # stage 2: sky floor / blend
    sky_result = {"t_floor": float(sky_cfg.get("t_floor", 0.35)),
                  "blend": float(sky_cfg.get("blend", 0.35)), "enabled": False}
    stage2 = []
    if len(sky_images) >= 3:
        for t_floor, blend in itertools.product((0.25, 0.35, 0.45), (0.0, 0.25, 0.5)):
            v2 = _base_v2(params)
            v2["airlight"]["method"] = best_method
            v2["sky"].update({"enabled": True, "t_floor": float(t_floor), "blend": float(blend)})
            metrics = _evaluate(sky_images, params, v2, obj_cfg)
            stage2.append({"t_floor": t_floor, "blend": blend, **metrics})
        best_sky = max(stage2, key=lambda r: r["objective"])
        sky_result = {"enabled": True, "t_floor": float(best_sky["t_floor"]),
                      "blend": float(best_sky["blend"])}
        print(f"  [sky] t_floor={sky_result['t_floor']} blend={sky_result['blend']} "
              f"obj={best_sky['objective']:.4f}")
    else:
        print("  [sky] too few calib images with sky; keeping it disabled")
    log["sky"] = stage2

    # stage 3: local density + local enhancement floor
    stage3 = []
    for floor in (0.0, 0.30, 0.50):
        v2 = _base_v2(params)
        v2["airlight"]["method"] = best_method
        v2["sky"].update(sky_result)
        v2["local_density"]["enabled"] = True
        v2["enhance"].update({"local_blend": True, "floor": float(floor)})
        metrics = _evaluate(images, params, v2, obj_cfg)
        stage3.append({"floor": floor, **metrics})
        print(f"  [local] floor={floor:.2f} obj={metrics['objective']:.4f} "
              f"psnr={metrics['psnr']:.2f} ssim={metrics['ssim']:.4f} "
              f"ms={metrics['ms']:.0f}")
    log["local"] = stage3
    best_floor = max(stage3, key=lambda r: r["objective"])["floor"]

    # stage 4: fast retinex
    def final_v2(fast: bool) -> dict:
        v2 = _base_v2(params)
        v2["airlight"]["method"] = best_method
        v2["sky"].update(sky_result)
        v2["local_density"]["enabled"] = True
        v2["enhance"].update({"local_blend": True, "floor": float(best_floor)})
        v2["retinex"]["fast"] = bool(fast)
        return v2

    stage4 = []
    for fast in (False, True):
        metrics = _evaluate(images, params, final_v2(fast), obj_cfg)
        stage4.append({"fast": bool(fast), **metrics})
        print(f"  [retinex] fast={fast} obj={metrics['objective']:.4f} ms={metrics['ms']:.0f}")
    log["retinex"] = stage4
    slow = next(r for r in stage4 if not r["fast"])
    fast = next(r for r in stage4 if r["fast"])
    # Keep fast Retinex only if it does not lose quality at all.
    use_fast = bool(fast["objective"] > slow["objective"] + 1e-6 and fast["ms"] < slow["ms"])

    chosen = final_v2(use_fast)
    chosen["sky"] = {**chosen.get("sky", {}), **sky_result}
    payload = {
        "created": datetime.now(timezone.utc).isoformat(),
        "tuned_on": "calib",
        "objective": obj_cfg,
        "penalty": "0.10 * extra gradient energy in flat regions (noise/halo proxy)",
        "n_images": len(images),
        "n_sky_images": len(sky_images),
        "v2": {
            "enabled": True,
            "airlight": {"method": best_method},
            "sky": {"enabled": bool(sky_result.get("enabled", False)),
                    "t_floor": float(sky_result.get("t_floor", 0.35)),
                    "blend": float(sky_result.get("blend", 0.35))},
            "local_density": {"enabled": True},
            "enhance": {"local_blend": True, "floor": float(best_floor)},
            "retinex": {"fast": bool(use_fast), "scale": 0.5},
        },
        "stage_log": log,
        "note": "Frozen before the first v2 test-split run. v1 defaults in params.yaml are unchanged.",
    }
    out = resolve_path(params.get("paths", {}).get("tuned_params_v2",
                                                   "config/tuned_params_v2.json"))
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")
    pd.DataFrame(stage1 + stage2 + stage3 + stage4).to_csv(
        resolve_path("results/v2_tuning_grid.csv"), index=False)
    print(f"[tune-v2] wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
