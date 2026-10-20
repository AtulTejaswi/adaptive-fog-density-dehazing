"""Profile the v1 and v2 pipelines stage-by-stage on 10 SOTS test images.

Writes ``results/v2_runtime_profile.csv`` (+ ``.json`` summary).  Test images are
used for timing only; no parameter is fitted here.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.io_utils import read_rgb  # noqa: E402
from src.pipeline import dehaze_adaptive, dehaze_adaptive_v2  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402


def main() -> int:
    params = load_params()
    v2_params = load_v2_params(params)
    splits = load_json(params.get("paths", {}).get("splits", "data/splits.json"), default={})
    records = [r for r in splits.get("records", []) if r["split"] == "test_sots"]
    if not records:
        raise SystemExit("No test_sots records; run scripts/prepare_data.py first")
    step = max(1, len(records) // 10)
    records = records[::step][:10]

    rows = []
    for rec in records:
        image = preprocess_array(read_rgb(resolve_path(rec["hazy"])), params)
        _, info1 = dehaze_adaptive(image, params)
        _, info2 = dehaze_adaptive_v2(image, v2_params)
        row = {"id": rec["id"]}
        for prefix, info in (("v1", info1), ("v2", info2)):
            for key, value in info["timing_ms"].items():
                row[f"{prefix}_{key}"] = float(value)
        rows.append(row)

    df = pd.DataFrame(rows)
    results = resolve_path("results")
    df.to_csv(results / "v2_runtime_profile.csv", index=False)
    keys = [c for c in df.columns if c != "id"]
    summary = {c: float(df[c].mean()) for c in keys}
    summary["n_images"] = int(len(df))
    with open(results / "v2_runtime_profile.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
        fh.write("\n")
    print(f"[profile] {len(df)} images")
    for key in keys:
        print(f"  {key:24s} {summary[key]:8.1f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
