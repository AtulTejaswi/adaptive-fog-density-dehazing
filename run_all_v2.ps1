# Full reproducible v2 run (Windows PowerShell). v1 artifacts are untouched.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

python scripts/prepare_data.py @args
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/calibrate.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/calibrate_local.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/fit_niqe_model.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/tune_params.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/tune_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/run_eval_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/profile_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/run_ablations_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/validate_density_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/make_v2_figures.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python scripts/finalize_report_v2.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python -m pytest -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Done. See results/v2_* and report/report.md"
