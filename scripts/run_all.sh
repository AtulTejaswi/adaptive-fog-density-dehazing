#!/usr/bin/env bash
# Full reproducible v1 run (Linux/macOS) - mirrors run_all.ps1 step for step.
# Safe to re-run; existing data and results are reused/cached.
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHON="${PYTHON:-.venv/bin/python}"
if [ ! -x "$PYTHON" ]; then
  echo "error: $PYTHON not found. Create the venv first:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

"$PYTHON" scripts/prepare_data.py "$@"
"$PYTHON" scripts/calibrate.py
"$PYTHON" scripts/tune_params.py
"$PYTHON" scripts/run_eval.py
"$PYTHON" scripts/run_ablations.py
"$PYTHON" scripts/make_figures.py
"$PYTHON" scripts/audit_baseline.py
"$PYTHON" scripts/finalize_report.py
"$PYTHON" -m pytest -q

echo "Done. See results/ and report/report.md"
