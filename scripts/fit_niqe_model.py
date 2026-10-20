"""Fit the NIQE-style pristine model on CALIB clear images only.

Writes ``config/niqe_model.json``.  Test-split images are never used.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.metrics import fit_niqe_model  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402


def main() -> int:
    params = load_params()
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", [])
               if r["split"] == "calib" and r.get("has_gt") and r.get("clear")]
    if not records:
        raise SystemExit("No calib clear images; run scripts/prepare_data.py first")

    print(f"[niqe] fitting pristine model on {len(records)} calib clear images")
    images = [preprocess_array(read_rgb(resolve_path(rec["clear"])), params)
              for rec in records]
    reg = float(params.get("metrics", {}).get("niqe", {}).get("reg", 1e-3))
    model = fit_niqe_model(images, reg=reg)
    model.update({"created": date.today().isoformat(), "fit_on": "calib_clear",
                  "note": "NIQE-style MSCN multivariate Gaussian, fitted on calib only."})
    path = resolve_path(params.get("paths", {}).get("niqe_model", "config/niqe_model.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(model, fh, indent=2)
        fh.write("\n")
    print(f"[niqe] wrote {path} ({model['n_images']} images, {model['n_features']} features)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
