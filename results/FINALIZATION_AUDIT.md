# v2 finalization audit (MASTER_PROMPT_v2)

Date: 2026-10-19. This file records the A–E verification requested in
`MASTER_PROMPT_v2.md`. No method or parameter was rebuilt; the frozen-params
boundary was preserved.

## A. Repo / GitHub integrity
- Remote: `https://github.com/AtulTejaswi/adaptive-fog-density-dehazing` (private).
- Local history preserved; `save_progress.sh` commits and pushes.
- Tags: `v0.1-frozen-params` (parameters frozen before any test evaluation) and
  `v1.0` (final verified deliverables, retagged on the final commit).
- `.gitignore` excludes `data/*` images, `results/images/` and caches; only
  `data/splits.json`, `data/README.md`, code, configs, CSVs and figures are committed.
  No secrets or large binaries are tracked.

## B. Fresh-environment reproducibility
- Clean virtual environment created in a temp folder (Python 3.12.4) and
  `pip install -r requirements.txt` completed.
- `python -m pytest -q` passes (51 tests); `scripts/verify_setup.py` reports all
  dependencies present, splits `{calib 299, test_sots 243, test_rtts 72,
  selector_train 180, density_validation 64}`, and calibration/tuned params found.
- Full pipeline (`run_all.ps1 --no-download`) rerun reproduced the headline numbers:
  - baseline SOTS PSNR/SSIM: `15.7100 / 0.8263`
  - adaptive SOTS PSNR/SSIM: `18.7750 / 0.8896`
- Environment note: the optional classifier ablation retrains from the synthetic
  selector set, so its accuracy varies slightly with scikit-learn version
  (0.756 -> 0.733). The headline rule-based selector is deterministic.

## C. Real RTTS no-reference set
- 72 real-world RTTS photographs (RESIDE-beta, no ground truth) obtained from the
  Hugging Face mirror `fuhao7i/RTTS` (Apache-2.0; 4322 images upstream).
- Reproducible acquisition: `scripts/download_rtts.py` + fixed manifest
  `scripts/rtts_subset.txt`; images land in `data/RTTS/` (gitignored).
- `prepare_data.py` detected 72 images (`sources.rtts = "real_rtts"`); the dehazing
  parameters were **not** retuned.
- A Windows-only duplicate bug (case-insensitive `data/RTTS` == `data/rtts`) was found
  and fixed: records are de-duplicated by `os.path.normcase(resolve(path))`.
- No-reference results over 72 images (adaptive vs baseline, paired):
  - entropy gain `+0.325` (win rate 97.2%, p = 2.3e-13)
  - RMS contrast improvement `+0.173` (95.8%)
  - Sobel edge-preservation ratio `+0.477` (100%)
  - colour cast `0.0263 -> 0.0129` (lower is better)
  See `results/comparison.csv` (`split = test_rtts`) and `results/ablations.md`.

## D. Baseline fairness + leakage
- `scripts/audit_baseline.py` (20 evenly spaced SOTS test images) writes
  `results/baseline_audit.csv`, `results/baseline_audit_summary.csv` and
  `results/figures/baseline_sanity.png`.
  - current baseline PSNR 15.44 / SSIM 0.8330
  - brightest dark-channel pixel 15.42 / 0.8332
  - top-1% mean atmospheric light 15.59 / 0.8342
  - no guided filter 14.59 / 0.7752
  - native resolution 17.02 / 0.8546
  - interpretation: the atmospheric-light estimator and guided filter help the
    baseline; the shared 640-px preprocessing costs ~1.6 dB for both methods, so the
    paired comparison is fair.
- `tests/test_splits_leakage.py` guards: calib/test scenes disjoint, split counts
  consistent, RTTS has no ground truth, `tuned_params.json` declares `tuned_on=calib`.

## E. Docs / figures / tags
- `report/report.md` and `report/slides.md` updated for the real RTTS set and the
  baseline audit; `README.md` documents the three-step data build.
- Figures regenerated under `results/figures/` (including `baseline_sanity.png`).
- Tag policy: `v0.1-frozen-params` stays on its original commit (`ead40e6`) and is not
  moved. The clean-venv rerun wrote a new `config/tuned_params.json` with exactly the
  same selected values (light 0.86/0.35, moderate 0.94/0.30, heavy 0.94/0.20); only the
  `created` timestamp differs, which is noted here. `v1.0` is retagged on the final
  verified commit after A–D pass.
