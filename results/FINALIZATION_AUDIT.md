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
- `python -m pytest -q` passes (66 tests, after adding the v3 edge-case suite);
  `scripts/verify_setup.py` reports all dependencies present, splits `{calib 299,
  test_sots 243, test_rtts 72, selector_train 180, density_validation 64}`, and
  calibration/tuned params found.
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

---

# v3 end-to-end acceptance (MASTER_PROMPT_v3)

Date: 2026-10-20. Verification only: no method or parameter was changed, and the
frozen-params tag `v0.1-frozen-params` was not moved. All acceptance steps passed.

## 1. Clean environment
- Fresh virtual environment (`ipa-venv-v3`, Python 3.12.4) created and
  `pip install -r requirements.txt` completed (exit 0).
- `python scripts/verify_setup.py`: all dependencies present; splits
  `{calib 299, test_sots 243, test_rtts 72, selector_train 180, density_validation 64}`;
  calibration + frozen tuned params present.
- `python -m pytest -q`: 51 passed (before the edge-case suite). Final suite: 66 passed.

## 2. Data from scratch
- Deleted `data/SOTS` and `data/RTTS` (kept `splits.json`, `README.md`); the cached SOTS
  archive was removed first so the download path was exercised for real.
- `python scripts/download_data.py`: downloaded the SOTS archive fresh (434.7 MB),
  extracted it, found 542 unique SOTS pairs.
- `python scripts/download_rtts.py`: 72/72 real RTTS images downloaded.
- `python scripts/prepare_data.py --no-download`: reproduced the exact split counts
  (`{calib 299, test_sots 243, test_rtts 72, selector_train 180, density_validation 64}`)
  and `sources = {sots: real_sots, rtts: real_rtts}`.

## 3. Full pipeline
- `./run_all.ps1 --no-download` finished without errors (calibrate -> tune -> eval ->
  ablations -> figures -> baseline audit -> finalize -> tests).
- Calibration/validation reproduced: thresholds `t1=0.3937`, `t2=0.5885`;
  Spearman overall `0.907`, within-scene mean `0.992` (min 0.939).

## 4. Numbers vs report
- Headline reproduced exactly: baseline `15.7100 / 0.8263`, adaptive `18.7750 / 0.8896`
  (SOTS test, 243 pairs); PSNR +3.065 dB, SSIM +0.0633; win rates 96.3% / 90.1%.
- Per-class deltas, RTTS no-reference deltas (+0.325 entropy, +0.173 contrast,
  +0.477 edge), density correlations and every ablation row match `results/*.csv`.
- Spot-check of 13 numeric claims in `report/report.md` and `report/slides.md` against
  the CSVs: all consistent (slides intentionally omit the SSIM win-rate figure).
- Runtime regenerated as 256 ms/image (3.9 FPS) on SOTS vs ~69 ms for fixed DCP; prose,
  slides, README, PROGRESS and HANDOFF were updated to this machine-dependent value.

## 5. Edge-case tests
- Added `tests/test_edge_cases.py` (15 tests): 1-pixel, tiny non-square, very large
  (2000x3000), 2D grayscale, `HxWx1`, `HxWx4`, `uint8`, grayscale PNG and RGBA PNG files,
  pure white, pure black, haze-free, corrupt file, missing file, determinism, and
  shape/dtype/range/finite guarantees (adaptive and baseline).
- Bug fixed: `preprocess_array` now accepts `HxWx1` inputs and raises a clear
  `ValueError("Expected a 2D grayscale ...")` for any other channel count (previously a
  `HxWx1` array could crash downstream). No method/output change for normal 3-channel input.
- Full suite: 66 passed.

## 6. Demo smoke test
- `streamlit run app/app.py --server.headless true`: `/_stcore/health` returns `200 ok`,
  index returns `200`.
- App processing path exercised on one SOTS and one RTTS image: score, class
  (light omega 0.86 / t0 0.35), output shape/range `[0,1]`, entropy gain printed; no errors.

## 7. Repo / docs / tags
- `git status` clean; only intended files changed (new `tests/test_edge_cases.py` and
  `MASTER_PROMPT_v3.md`, hardened `src/preprocess.py`, refreshed configs/results/docs).
- No image data or secrets are tracked (`git ls-files data` -> `README.md`, `splits.json`
  only). `.gitignore` unchanged.
- `v0.1-frozen-params` remains on `ead40e6`; `v1.0` retagged on the final v3 commit.

## 8. Optional exports
- Skipped: the rubric format (PDF/PPTX, page limit) is still unknown (D-00/D-34). The
  Markdown report and slides are the source of truth and can be exported on request.

## Final report
1. Clean venv + install + `verify_setup` + tests: PASS.
2. Data deleted and rebuilt from scratch (fresh SOTS + 72 RTTS): PASS, counts 299/243/72/180/64.
3. Full `run_all.ps1`: PASS (no errors).
4. Numbers vs report/slides: PASS (headline + 13 spot-checks; only runtime updated).
5. Edge cases: PASS, 15 tests added, bug fixed in `preprocess_array`, 66 tests total.
6. Demo: PASS (health 200; app path OK on SOTS + RTTS).
7. Repo/docs/tags: PASS (`v1.0` moved, `v0.1-frozen-params` untouched, no data/secrets tracked).
8. Optional exports: skipped (rubric format unknown; D-00/D-34).
- Headline (unchanged): adaptive 18.78 dB / 0.8896 vs fixed DCP 15.71 dB / 0.8263.
- No further changes required unless the rubric asks for a specific report/slide format.

---

# v2 upgrade audit (MASTER_PROMPT_v4)

## 1. Branch, tags, compatibility
- Branch `v2-upgrade` created off `main` (`0073830`). `v0.1-frozen-params` (`ead40e6`)
  and `v1.0` are untouched.
- Every new feature is behind `params.v2.*`; `config/params.yaml` still defaults to v1.
  `tests/test_v2_compat.py` (4 tests) proves the flags-off path is byte-identical to v1
  (`array_equal`) and that scalar/array omega/t0 agree.
- Full suite: **83 passed** (66 v1 + 4 compat + 13 v2 features).

## 2. Calib-only fitting and freeze
- `scripts/calibrate_local.py` -> `config/calibration_local.json` (299 calib images,
  class centroids light 0.2710 / moderate 0.4919 / heavy 0.7058).
- `scripts/fit_niqe_model.py` -> `config/niqe_model.json` (299 calib clear images).
- `scripts/tune_v2.py` -> `config/tuned_params_v2.json` +
  `results/v2_tuning_grid.csv` (36 calib, 12/class; 29 with sky).
- Frozen at tag **`v2.0-frozen-params`** before the first v2 test-split run. No test
  image was used for any fit, threshold, or selection.

## 3. Frozen choices
- airlight = v2 (connected + low-gradient candidates; quadtree rejected on calib).
- sky `t_floor=0.25`, `blend=0.25`.
- local density enabled; local enhancement blend enabled with `floor=0.0`.
- Retinex fast = false (rejected: -0.31 dB / -0.0042 SSIM for ~40 ms).

## 4. Test evaluation (315 images x 5 methods)
- SOTS (243): v2 18.4503 / 0.8873 vs v1 18.7750 / 0.8896; CIEDE2000 9.3814 vs
  9.5014; NIQE-style 1.7943 vs 1.6850; FADE-style 0.4007 vs 0.4051.
- Paired v2-vs-v1: PSNR -0.3247 (p=0.0002), SSIM -0.0023 (p=0.4416),
  CIEDE2000 -0.1201 (p=0.2341), NIQE +0.1094 (p=0.0541), FADE -0.0044 (p=0.0005).
- Indoor (22): v2 20.5578 / 0.8528 vs v1 19.8113 / 0.8410 (+0.75 dB / +0.0118).
  Outdoor (221): v2 18.2405 / 0.8907 vs v1 18.6719 / 0.8944 (-0.43 dB / -0.0037).
- Strong baselines: CAP 18.0912 / 0.7833, BCCR-style 16.0186 / 0.8309, DCP
  15.7100 / 0.8263. v2 vs CAP: +0.3591 dB (p=0.0926), +0.1040 SSIM.
- RTTS (72, no GT): v1 entropy +0.4165 / edge 1.6733 / cast 0.0129; v2 +0.3063 /
  1.4729 / 0.0174; v2 FADE 0.4586 vs v1 0.4677; BCCR best NIQE/FADE
  (1.2476 / 0.4448).
- Brightness/colour-match diagnostic: v2 matched PSNR 22.2552 vs v1 21.8847
  (+0.37 dB), i.e. part of the raw gap is a global brightness/colour shift.
  Diagnostic only, never a headline.

## 5. Ablation (SOTS, 243 x 6)
- v1 18.7750/0.8896; +airlight 18.8786/0.8895; +sky 19.4101/0.8933;
  +local omega 18.5439/0.8815; +local enhancement 18.4503/0.8873; full 18.4503/0.8873.
- The sky step is the only component that improves both PSNR and SSIM (+0.53 dB /
  +0.0038 over airlight). Local omega/t0 as tuned loses 0.87 dB / 0.0119 SSIM.
  The v2-light variant (airlight+sky) is +0.64 dB / +0.0037 vs v1, but selecting it
  after the test ablation would be test tuning, so it is future work only.

## 6. Density validation (64 sweep / 72 RTTS)
- vs beta: global 0.907, local mean 0.948, dc_only 0.928, dc_entropy 0.917,
  contrast_std -0.780 (raw contrast, sign flips in the score), ridge 0.925.
- within-scene: global 0.992, local mean 1.000, ridge 1.000.
- RTTS vs FADE: global 0.933, local mean 0.817, dc_only 0.762, dc_entropy 0.904,
  contrast_std -0.611, ridge 0.969.
- Ridge improves over the *global* score but not the local mean on beta; it is an
  experiment, not the shipped estimator.

## 7. Runtime profile (10 SOTS images)
- v1: density 25.8 / dcp 61.3 / enhance 133.9 / total 222.1 ms.
- v2: density 26.5 / local density 405.5 / dcp 90.0 / enhance 133.8 / total 667.7 ms.
- End-to-end eval (243): v2 561.7 ms vs v1 192.3 ms vs DCP 59.4 ms.

## 8. Honest conclusion
- v2 does **not** beat v1 on aggregate SOTS PSNR/SSIM and is ~2.9x slower. It improves
  CIEDE2000, indoor scenes, and the sky failure cases; CAP narrows the PSNR advantage
  over fixed DCP. v1 remains the recommended default. No number in the report was
  fabricated; all v2 numbers come from `results/v2_*`.

## 9. Repo / docs / tags
- Report §9, slides 16-18, README v2 block, DECISIONS D-35..D-41, PROGRESS and
  HANDOFF updated. Figures in `results/figures/v2_*.png`.
- `v0.1-frozen-params` and `v1.0` untouched; `v2.0-frozen-params` on the freeze
  commit; final `v2.0` on the deliverable commit.
