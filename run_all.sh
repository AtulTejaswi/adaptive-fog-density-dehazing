#!/usr/bin/env bash
# Full reproducible run (Linux/macOS). Safe to re-run; results are cached.
set -e
cd "$(dirname "$0")"
python scripts/prepare_data.py "$@"
python scripts/calibrate.py
python scripts/tune_params.py
python scripts/run_eval.py
python scripts/run_ablations.py
python scripts/make_figures.py
python scripts/finalize_report.py
python -m pytest -q
echo "Done. See results/ and report/report.md"
