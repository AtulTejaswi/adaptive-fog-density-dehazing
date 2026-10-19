# HANDOFF (overwrite at the end of every session; keep under 30 lines)

## State
Project complete, verified and reproducible. Real SOTS: 299 calib / 243 test pairs,
split by unique clear scene. Parameters calibrated + tuned on calib only and frozen at
tag `v0.1-frozen-params` before testing. Real 72-image RTTS no-reference set is used
(via `scripts/download_rtts.py` + `scripts/rtts_subset.txt`). A clean-venv rerun
reproduced the headline numbers; baseline fairness is audited by
`scripts/audit_baseline.py`; leakage is guarded by `tests/test_splits_leakage.py`.

Key results (SOTS test): adaptive **18.78 dB / 0.8896** vs baseline **15.71 dB /
0.8263**; +3.07 dB, +0.0633 SSIM; 96.3% PSNR / 90.1% SSIM win rate. Density score vs
beta: overall Spearman 0.907, within-scene mean 0.992. Runtime ~273 ms/image (CPU).
Real 72-image RTTS: entropy gain +0.325, contrast +0.173, edge ratio +0.477 vs baseline.
Ablations: no-enh 17.77/0.8726; CLAHE 18.18/0.8850; CLAHE+Retinex 19.30/0.8840;
continuous selector 18.80/0.8574; classifier 18.40/0.8780.

## Do next (in order)
1. Open `results/evaluation_summary.md`, `results/results_table.md`,
   `results/ablations.md`, `results/baseline_audit_summary.csv`, `report/report.md`,
   `report/slides.md`.
2. Demo: `streamlit run app/app.py`.
3. Data rebuild: `python scripts/download_data.py`, `python scripts/download_rtts.py`,
   `python scripts/prepare_data.py --no-download` (no tuning needed).
4. If changing any data/parameters, re-run the full `./run_all.ps1` and re-tag.

## Gotchas
- Never tune on `test_sots` / `test_rtts`; thresholds/params are calib-only.
- `data/` images are gitignored; `data/splits.json` + `data/README.md` are committed.
- RTTS images are gitignored; re-download with `scripts/download_rtts.py`. The
  synthetic RTTS-style fallback stays available when `data/RTTS/` is empty.
- Windows console is cp1252: avoid printing Greek symbols from scripts (files are UTF-8).
- On Windows `data/RTTS` and `data/rtts` are the same folder; `prepare_data.py`
  de-duplicates by real path.

## Files touched last session
- All `src/`, `scripts/`, `tests/`, `app/`, `config/`, `results/` and `report/` files.
