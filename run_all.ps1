# Full reproducible run (Windows PowerShell). Safe to re-run.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python scripts/prepare_data.py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/calibrate.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/tune_params.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/run_eval.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/run_ablations.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/make_figures.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/finalize_report.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. See results/ and report/report.md"
