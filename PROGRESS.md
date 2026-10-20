# PROGRESS (live log - UPDATE THIS AFTER EVERY MEANINGFUL STEP)

Last updated: 2026-10-20
Last model/agent: DeepSeek V4.1 Flash (v4 opt-in v2 upgrade session)

## Current status
Phase: 13 - opt-in v2 upgrade + honest comparison (MASTER_PROMPT_v4)
Overall completion: 100% (evaluation, ablations, density validation, figures, report)

## Phase checklist
| Phase | Name | Status |
|---|---|---|
| 0 | Setup | done (local git + GitHub remote `AtulTejaswi/adaptive-fog-density-dehazing`) |
| 1 | Data | done (542 SOTS pairs: 299 calib / 243 test; 72 real RTTS; 64 beta sweep) |
| 2 | Preprocessing | done + tested |
| 3 | Fog density estimation | done (Spearman 0.907 overall, 0.992 within-scene) |
| 4 | Adaptive strategy selector | done (3-bin primary, continuous + classifier ablations) |
| 5 | Baseline + core DCP | done (fixed DCP + own guided filter; fairness audited) |
| 6 | Enhancement | done (Retinex, blended CLAHE, gray-world, individually switchable) |
| 7 | Full pipeline + tuning (freeze params) | done; tagged `v0.1-frozen-params` before test |
| 8 | Evaluation | done (SOTS + 72-image real RTTS no-reference) |
| 9 | Ablations | done (10 variants, 243 SOTS test images) |
| 10 | Figures, demo, report | done (11 figures, Streamlit demo, report + slides) |
| 11 | v2 finalization (verify, close gaps, retag) | done (see `results/FINALIZATION_AUDIT.md`) |
| 12 | v3 end-to-end acceptance (clean env, data from scratch, full pipeline, edge cases, demo) | done (66 tests; see `results/FINALIZATION_AUDIT.md`) |
| 13 | v4 opt-in v2 upgrade (airlight/sky, local maps, CAP/BCCR, new metrics, honest v1-vs-v2) | done (83 tests; frozen at `v2.0-frozen-params`; see §9 of the report) |

## Key numbers
- Dataset sizes: calib=299, SOTS test=243, real RTTS=72, density validation=64
- Density thresholds t1=0.3937, t2=0.5885
- Density vs beta Spearman: 0.907 overall, 0.992 within-scene mean (min 0.939)
- Baseline PSNR/SSIM (SOTS): **15.71 dB / 0.8263**
- Adaptive PSNR/SSIM (SOTS): **18.78 dB / 0.8896**
- Paired improvement: +3.07 dB PSNR, +0.0633 SSIM; adaptive wins 96.3% (PSNR) / 90.1% (SSIM) of images; Wilcoxon p < 1e-30
- Per class (adaptive vs baseline): light +3.24 dB / +0.0665 SSIM; moderate +4.11 dB / +0.0737; heavy +1.37 dB / +0.0446
- No-reference real RTTS (72 images, no GT): entropy gain +0.325 (97.2% wins), contrast +0.173 (95.8%), edge ratio +0.477 (100%), colour cast 0.026 -> 0.013
- Avg runtime/image (SOTS, CPU, includes preprocessing): 256 ms (3.9 FPS); baseline 69 ms (varies by machine)
- Frozen parameters: light omega 0.86 / t0 0.35; moderate 0.94 / 0.30; heavy 0.94 / 0.20; CLAHE clip 1.5 strength 0.4; Retinex only moderate 0.35
- Ablation highlights: full 18.775 dB / 0.8896; no enhancement 17.771 / 0.8726;
  CLAHE only 18.184 / 0.8850; CLAHE+Retinex 19.304 / 0.8840 (PSNR/SSIM trade-off);
  density dark-only 18.477 / 0.8831; density + entropy 18.836 / 0.8901;
  continuous selector 18.800 / 0.8574; classifier 18.401 / 0.8780; 3-bin wins on SSIM
- Classifier holdout accuracy: 0.733 (ablation only; varies slightly with scikit-learn version)
- Baseline audit (20 SOTS images): current 15.44 dB, brightest-A 15.42, top-1% A 15.59,
  no guided filter 14.59, native resolution 17.02 -> baseline is not handicapped

### v2 (opt-in) key numbers
- v1 remains the default; with all v2 flags off the output is byte-identical to v1.0
  (`tests/test_v2_compat.py`); v2 parameters were frozen at `v2.0-frozen-params`
  before the first v2 test-split run.
- SOTS (243): v2 **18.4503 dB / 0.8873** vs v1 **18.7750 dB / 0.8896**
  (PSNR -0.3247 dB, p=0.0002; SSIM -0.0023, p=0.4416); CIEDE2000 9.3814 vs 9.5014
  (better), NIQE-style 1.7943 vs 1.6850 (worse), FADE-style 0.4007 vs 0.4051 (better).
- Indoor (22): v2 20.5578 / 0.8528 vs v1 19.8113 / 0.8410 (+0.75 dB / +0.0118).
  Outdoor (221): v2 18.2405 / 0.8907 vs v1 18.6719 / 0.8944 (-0.43 dB / -0.0037).
- Stronger baselines (SOTS): CAP 18.0912 / 0.7833, BCCR-style 16.0186 / 0.8309,
  fixed DCP 15.7100 / 0.8263. v2 vs CAP: +0.36 dB (p=0.0926) / +0.1040 SSIM.
- RTTS (72, no GT): v1 entropy +0.4165 / edge 1.6733 / colour cast 0.0129;
  v2 +0.3063 / 1.4729 / 0.0174; v2 FADE 0.4586 vs v1 0.4677; BCCR has the best
  NIQE/FADE (1.2476 / 0.4448) but the weakest detail gains.
- Ablation (SOTS, PSNR/SSIM): v1 18.7750/0.8896; +airlight 18.8786/0.8895;
  +sky 19.4101/0.8933; +local omega 18.5439/0.8815; +local enhancement
  18.4503/0.8873. The sky step is the only component that helps both; the local
  omega/t0 maps as tuned hurt, so full v2 ends below v1.
- Density validation: local mean vs beta 0.948 (global 0.907; within-scene 1.000);
  on RTTS vs FADE: global 0.933, local mean 0.817, calib-fitted ridge 0.969
  (ridge is an experiment, not shipped).
- Runtime (SOTS, same run): v2 562 ms vs v1 192 ms vs DCP 59 ms; local density is
  the main extra cost. Fast Retinex was rejected on calib (-0.31 dB / -0.0042 SSIM
  for ~40 ms).
- Honest conclusion: the v2 upgrades did not generalise to the aggregate SOTS
  average; v1 stays the recommended default. The v2-light variant (airlight+sky)
  would be +0.64 dB / +0.0037 vs v1, but choosing it after the test ablation would
  be test-set tuning, so it is reported only as future work.

## Session log (newest first)
### 2026-10-20 - v4 opt-in v2 upgrade session
- Branch `v2-upgrade` off `main` (`0073830`); tags `v0.1-frozen-params` and `v1.0`
  untouched. Full suite 83 tests pass; v1 byte-identical compatibility test included.
- Implemented v2 airlight (connected + low-gradient candidates), quad-tree alternative,
  conservative sky mask, local density maps, per-pixel omega/t0, spatially blended
  enhancement, CAP + BCCR-style baselines, CIEDE2000 + NIQE-style + FADE-style.
- Calib-only fitting: `calibration_local.py` (299 calib), `fit_niqe_model.py`
  (299 calib clear), `tune_v2.py` (36 calib, 12/class; 29 with sky). Wrote
  `config/calibration_local.json`, `config/niqe_model.json`, `config/tuned_params_v2.json`,
  `results/v2_tuning_grid.csv`. Tagged `v2.0-frozen-params` before any v2 test run.
- Full v2 evaluation (315 images x 5 methods) + ablation (243 x 6) + density validation
  (64 sweep / 72 RTTS) + runtime profile (10 images). All numbers reproduced from
  `results/v2_*`; figures in `results/figures/v2_*.png`.
- Result: v2 is **not** an aggregate win over v1 (18.4503/0.8873 vs 18.7750/0.8896);
  it helps indoor and CIEDE2000, hurts outdoor; CAP is a much stronger baseline than
  fixed DCP. The sky step alone is +0.64 dB / +0.0037, but the local maps as tuned
  lose 0.87 dB / 0.0119 SSIM. Reported honestly; v1 remains the default.
- Report §9, slides 16-18, README v2 block, DECISIONS D-35..D-41, this log and
  `results/FINALIZATION_AUDIT.md` updated. Final tag `v2.0` after the commit.

### 2026-10-20 - v3 end-to-end acceptance session
- Boot + git verified (`main` clean, tags `v0.1-frozen-params` / `v1.0`, remote OK).
- 1. Fresh Python 3.12.4 venv + `requirements.txt` + `verify_setup.py` + 51 tests pass.
- 2. Deleted `data/SOTS` / `data/RTTS` and rebuilt from scratch: fresh SOTS download
  (434.7 MB) + `download_rtts.py` (72 images) + `prepare_data.py`. Counts: 299/243/72/180/64.
- 3. `run_all.ps1 --no-download` finished without errors.
- 4. Numbers reproduced exactly: baseline 15.710/0.8263, adaptive 18.775/0.8896,
  per-class deltas, RTTS +0.325/+0.173/+0.477, density 0.907/0.992, ablation rows.
  Runtime updated to 256 ms/image (machine-dependent).
- 5. Added `tests/test_edge_cases.py` (15 tests: tiny/1-px, large, grayscale, HxWx1,
  RGBA, pure white/black, haze-free, corrupt/missing, determinism, shape/range).
  Fixed `preprocess_array` to accept HxWx1 and raise a clear error for bad shapes.
- 6. Demo: streamlit headless health 200; app path checked on one SOTS + one RTTS image.
- 7. Repo clean and pushed; `v1.0` moved to the final commit; `v0.1-frozen-params` untouched.
- 66 pytest tests pass.

### 2026-10-19 - v2 finalization / hardening session
- Boot: re-read README/CONTEXT/PROGRESS/HANDOFF/DECISIONS/PLAN, verified git
  history, tags and remote.
- A. Repo integrity verified; `MASTER_PROMPT_v2.md` committed; remote pushed.
- B. Fresh-venv reproducibility: clean Python 3.12.4 venv, `pytest`, `verify_setup.py`
  and a full pipeline rerun reproduced baseline 15.710/0.8263 and adaptive
  18.775/0.8896.
- C. Obtained 72 real RESIDE-beta RTTS images via `scripts/download_rtts.py` +
  fixed manifest; found and fixed a Windows `data/RTTS` vs `data/rtts` duplicate bug
  (144 -> 72 records); re-ran prepare/eval without retuning.
- D. Added `scripts/audit_baseline.py` (baseline fairness) and
  `tests/test_splits_leakage.py` (scene-disjoint splits, no RTTS GT, calib-only tuning).
- E. Regenerated 11 figures, refreshed report/README/slides with real RTTS and audit
  numbers, retagged `v1.0` at the verified commit.
- 51 pytest tests pass (before the v3 edge-case suite; 66 now).

### 2026-10-19 - Implementation + evaluation session
- Built the complete project: data download/splits, preprocessing, density estimator,
  rule/continuous/classifier selectors, DCP + guided filter, enhancement stack,
  adaptive pipeline, baseline, metrics, evaluation, ablations, figures, Streamlit demo.
- Real SOTS: 542 unique clear scenes, split by scene into 299 calib / 243 test.
- Calibrated density stats and tertile thresholds on calib only; beta sweep validated.
- Tuned per-class params on calib only with a constrained monotone search; froze
  `config/tuned_params.json` and tagged `v0.1-frozen-params` before testing.
- Test evaluation complete; ablations, figures, report and README numbers generated.

## Known issues / blockers
- None blocking. RTTS images are gitignored; re-download with `scripts/download_rtts.py`.
- The optional classifier ablation retrains per environment, so its holdout accuracy
  varies slightly with scikit-learn version (0.756 -> 0.733); the rule-based selector
  (the headline method) is deterministic.
- Haze class on SOTS is estimated from the density score (SOTS has no per-image beta
  label), so per-class results use an operational definition, not ground truth.

## Environment notes
- Windows 10/11, Python 3.12.4, OpenCV 5.0.0, scikit-image 0.26, scikit-learn 1.9,
  Streamlit, pytest 9.
- Data at `data/SOTS` and `data/RTTS` (gitignored). Results and figures in `results/`.
