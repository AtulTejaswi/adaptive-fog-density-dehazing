#!/usr/bin/env bash
# Full reproducible v2 run (Linux/macOS) - mirrors run_all_v2.ps1 step for step.
# v1 artifacts are left untouched; v2 writes results/v2_* files.
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
"$PYTHON" scripts/calibrate_local.py
"$PYTHON" scripts/fit_niqe_model.py
"$PYTHON" scripts/tune_params.py
"$PYTHON" scripts/tune_v2.py
"$PYTHON" scripts/run_eval_v2.py
"$PYTHON" scripts/profile_v2.py
"$PYTHON" scripts/run_ablations_v2.py
"$PYTHON" scripts/validate_density_v2.py
"$PYTHON" scripts/make_v2_figures.py
"$PYTHON" scripts/finalize_report_v2.py
"$PYTHON" -m pytest -q

echo "Done. See results/v2_* and report/report.md"
