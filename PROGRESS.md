# PROGRESS (live log - UPDATE THIS AFTER EVERY MEANINGFUL STEP)

Last updated: 2026-10-20
Last model/agent: DeepSeek V4.1 Flash (v3 end-to-end acceptance session)

## Current status
Phase: 12 - v3 end-to-end acceptance (MASTER_PROMPT_v3)
Overall completion: 100% (acceptance complete)

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

## Session log (newest first)
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
