"""Quick environment/data sanity check (no test-set evaluation)."""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REQUIRED = ["numpy", "cv2", "scipy", "skimage", "sklearn", "pandas",
            "matplotlib", "yaml", "streamlit", "pytest"]


def main() -> int:
    ok = True
    print("Dependencies:")
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "?")
            print(f"  [ok] {name:12s} {version}")
        except Exception as exc:
            ok = False
            print(f"  [missing] {name}: {exc}")
    splits = ROOT / "data" / "splits.json"
    if splits.exists():
        data = json.loads(splits.read_text(encoding="utf-8"))
        print("\nSplits:", data.get("counts"))
        print("Sources:", data.get("sources"))
    else:
        print("\n[missing] data/splits.json -> python scripts/prepare_data.py")
        ok = False
    calib = ROOT / "config" / "calibration.json"
    tuned = ROOT / "config" / "tuned_params.json"
    print("Calibration:", "present" if calib.exists() else "missing")
    print("Tuned params:", "present (frozen)" if tuned.exists() else "missing")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
