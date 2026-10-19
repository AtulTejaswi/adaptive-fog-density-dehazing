# HANDOFF (overwrite at the end of every session; keep under 30 lines)

## State
Project complete and reproducible. Real SOTS: 299 calib / 243 test pairs, split by
unique clear scene. Parameters calibrated + tuned on calib only and frozen at tag
`v0.1-frozen-params` before testing. Test evaluation, 10-variant ablations, 10 figures,
report and README numbers are generated.

Key results (SOTS test): adaptive **18.78 dB / 0.8896** vs baseline **15.71 dB /
0.8263**; +3.07 dB, +0.0633 SSIM; 96.3% PSNR / 90.1% SSIM win rate. Density score vs
beta: overall Spearman 0.898, within-scene mean 0.995. Runtime ~260 ms/image (CPU).
Ablations: no-enh 17.77/0.8726; CLAHE 18.18/0.8850; CLAHE+Retinex 19.30/0.8840;
continuous selector 18.80/0.8574; classifier 18.42/0.8779.

## Do next (in order)
1. Open `results/evaluation_summary.md`, `results/results_table.md`,
   `results/ablations.md`, `report/report.md`, `report/slides.md`.
2. Demo: `streamlit run app/app.py`.
3. Optional: put real RTTS images in `data/RTTS/`, re-run
   `python scripts/prepare_data.py` then `run_eval.py` (no tuning needed).
4. If changing any data/parameters, re-run the full `./run_all.ps1` and re-tag.

## Gotchas
- Never tune on `test_sots` / `test_rtts`; thresholds/params are calib-only.
- `data/` images are gitignored; `data/splits.json` + `data/README.md` are committed.
- Real RTTS is not redistributed; the no-reference fallback is synthetic.
- Windows console is cp1252: avoid printing Greek symbols from scripts (files are UTF-8).

## Files touched last session
- All `src/`, `scripts/`, `tests/`, `app/`, `config/`, `results/` and `report/` files.
