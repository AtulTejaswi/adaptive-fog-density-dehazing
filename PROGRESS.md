# PROGRESS (live log - UPDATE THIS AFTER EVERY MEANINGFUL STEP)

Last updated: 2026-10-19
Last model/agent: DeepSeek V4.1 Flash (implementation session)

## Current status
Phase: 8 - Evaluation (in progress; parameters frozen)
Overall completion: 90%

## Phase checklist
| Phase | Name | Status |
|---|---|---|
| 0 | Setup | done |
| 1 | Data | done (542 SOTS pairs: 299 calib / 243 test; 48 RTTS-style; 64 beta sweep) |
| 2 | Preprocessing | done + tested |
| 3 | Fog density estimation | done (Spearman 0.898 overall, 0.995 within-scene) |
| 4 | Adaptive strategy selector | done (3-bin primary, continuous + classifier ablations) |
| 5 | Baseline + core DCP | done (fixed DCP + own guided filter) |
| 6 | Enhancement | done (Retinex, CLAHE, gray-world, individually switchable) |
| 7 | Full pipeline + tuning (freeze params) | done (tuned on calib; frozen tag) |
| 8 | Evaluation | running after freeze |
| 9 | Ablations | pending (script ready) |
| 10 | Figures, demo, report | figures/report pending final numbers; demo + report draft done |

## Key numbers (fill as they appear)
- Dataset sizes: calib=299, SOTS test=243, RTTS-style=48, density validation=64
- Density thresholds t1=0.3937, t2=0.5885
- Density vs beta Spearman: 0.898 overall, 0.995 within-scene mean
- Baseline PSNR/SSIM (SOTS): pending
- Adaptive PSNR/SSIM (SOTS): pending
- Avg runtime/image: pending

## Session log (newest first)
### 2026-10-19 - Implementation session
- Built the complete project: data download/splits, preprocessing, density estimator,
  rule/continuous/classifier selectors, DCP + guided filter, enhancement stack,
  adaptive pipeline, baseline, metrics, evaluation, ablations, figures, Streamlit demo.
- Real SOTS: 542 unique clear scenes, split by scene into 299 calib / 243 test.
- Calibrated density stats and tertile thresholds on calib only; beta sweep validated.
- Tuned per-class params on calib only; froze `config/tuned_params.json`.
- 46 pytest tests passing.

## Known issues / blockers
- Real RTTS images are not bundled; synthetic RTTS-style fallback is used unless the
  user drops images in `data/RTTS/`.

## Environment notes
- Windows 10/11, Python 3.12.4, OpenCV, scikit-image 0.26, scikit-learn, Streamlit.
- Data at `data/SOTS` (gitignored). Results and figures in `results/`.
