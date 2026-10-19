# PROGRESS (live log - UPDATE THIS AFTER EVERY MEANINGFUL STEP)

Last updated: 2026-10-19
Last model/agent: DeepSeek V4.1 Flash (v2 finalization session)

## Current status
Phase: 10 - Finalization / hardening (MASTER_PROMPT_v2)
Overall completion: 100% (verification in progress)

## Phase checklist
| Phase | Name | Status |
|---|---|---|
| 0 | Setup | done (local git + GitHub remote `AtulTejaswi/adaptive-fog-density-dehazing`) |
| 1 | Data | done (542 SOTS pairs: 299 calib / 243 test; 48 RTTS-style; 64 beta sweep) |
| 2 | Preprocessing | done + tested |
| 3 | Fog density estimation | done (Spearman 0.898 overall, 0.995 within-scene) |
| 4 | Adaptive strategy selector | done (3-bin primary, continuous + classifier ablations) |
| 5 | Baseline + core DCP | done (fixed DCP + own guided filter) |
| 6 | Enhancement | done (Retinex, blended CLAHE, gray-world, individually switchable) |
| 7 | Full pipeline + tuning (freeze params) | done; tagged `v0.1-frozen-params` before test |
| 8 | Evaluation | done |
| 9 | Ablations | done (10 variants, 243 SOTS test images) |
| 10 | Figures, demo, report | done (10 figures, Streamlit demo, report + slides) |

## Key numbers
- Dataset sizes: calib=299, SOTS test=243, RTTS-style=48, density validation=64
- Density thresholds t1=0.3937, t2=0.5885
- Density vs beta Spearman: 0.898 overall, 0.995 within-scene mean (min 0.976)
- Baseline PSNR/SSIM (SOTS): **15.71 dB / 0.8263**
- Adaptive PSNR/SSIM (SOTS): **18.78 dB / 0.8896**
- Paired improvement: +3.07 dB PSNR, +0.0633 SSIM; adaptive wins 96.3% (PSNR) / 90.1% (SSIM) of images; Wilcoxon p < 1e-30
- Per class (adaptive vs baseline): light +3.24 dB / +0.0665 SSIM; moderate +4.11 dB / +0.0737; heavy +1.37 dB / +0.0446
- No-reference RTTS-style: entropy gain +0.267, contrast improvement +0.231, edge ratio +0.734
- Avg runtime/image (SOTS, CPU, includes preprocessing): 260.7 ms (3.8 FPS); baseline 89.5 ms
- Frozen parameters: light omega 0.86 / t0 0.35; moderate 0.94 / 0.30; heavy 0.94 / 0.20; CLAHE clip 1.5 strength 0.4; Retinex only moderate 0.35
- Ablation highlights: full 18.775 dB / 0.8896; no enhancement 17.771 / 0.8726;
  CLAHE only 18.184 / 0.8850; CLAHE+Retinex 19.304 / 0.8840 (PSNR/SSIM trade-off);
  density dark-only 18.477 / 0.8831; density + entropy 18.836 / 0.8901;
  continuous selector 18.800 / 0.8574; classifier 18.419 / 0.8779

## Session log (newest first)
### 2026-10-19 - Implementation + evaluation session
- Built the complete project: data download/splits, preprocessing, density estimator,
  rule/continuous/classifier selectors, DCP + guided filter, enhancement stack,
  adaptive pipeline, baseline, metrics, evaluation, ablations, figures, Streamlit demo.
- Real SOTS: 542 unique clear scenes, split by scene into 299 calib / 243 test.
- Calibrated density stats and tertile thresholds on calib only; beta sweep validated
  (within-scene Spearman 0.995).
- Tuned per-class params on calib only with a constrained monotone search; froze
  `config/tuned_params.json` and tagged `v0.1-frozen-params` before testing.
- Test evaluation complete; 47 pytest tests pass.
- Ablations complete (10 variants); all 10 figures generated; report/README numbers
  filled from results and tags created.

## Known issues / blockers
- Real RTTS images are not bundled; synthetic RTTS-style fallback is used unless the
  user drops images in `data/RTTS/`.
- Cloud/model credits were limited; all tuning uses a small but documented grid.

## Environment notes
- Windows 10/11, Python 3.12.4, OpenCV, scikit-image 0.26, scikit-learn, Streamlit.
- Data at `data/SOTS` (gitignored). Results and figures in `results/`.
