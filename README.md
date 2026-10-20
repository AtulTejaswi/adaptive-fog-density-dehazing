# FogSense: An Intelligent Multi-Algorithm Framework for Adaptive Haze Removal

Course project for **Image Processing & Analysis (IPA)**. **FogSense** is a classical,
explainable multi-algorithm framework that first *estimates haze density* from image
statistics, then adapts the dehazing strength and enhancement strategy to that density.
It bundles an adaptive DCP pipeline plus fixed DCP, CAP and BCCR-style baselines behind
one interface, and compares them on SOTS (RESIDE, synthetic hazy/clear pairs) and a
72-image real-world RTTS no-reference set. "Intelligent" here means density-aware
rule-based adaptation, not a trained deep network.

No deep dehazing networks are used: every stage is classical image processing.

---

## Method (5 stages)

```
input image
   │
   ├─ 1. Preprocessing      resize long side 640, float32 [0,1], light bilateral denoise
   │
   ├─ 2. Density estimation dark-channel mean ↑, entropy ↓, contrast ↓
   │                         percentile-normalised on calib → score ∈ [0,1]
   │
   ├─ 3. Strategy selection light / moderate / heavy (tertiles of calib scores)
   │                         per-class omega, t0, guided-filter, CLAHE, Retinex
   │
   ├─ 4. Dehazing            DCP + guided filter + radiance recovery
   │                         then Retinex → CLAHE → gray-world (configurable)
   │
   └─ 5. Evaluation         PSNR/SSIM (SOTS), entropy gain / contrast / edge
                             preservation (all), runtime, ablations
```

Atmospheric scattering model:

```
I(x) = J(x) t(x) + A (1 - t(x)),      t(x) = exp(-beta d(x))
J(x) = (I(x) - A) / max(t(x), t0) + A
```

## Quick start

Reproduce the headline result in 3 steps:

```bash
# 1. data (SOTS + 72 real RTTS images)
python scripts/download_data.py && python scripts/download_rtts.py

# 2. fixed splits (SOTS + RTTS + beta sweep)
python scripts/prepare_data.py --no-download

# 3. calibrate -> tune -> evaluate -> ablate -> figures -> report -> tests
./run_all.ps1 --no-download
```

Or run the stages individually:

```bash
pip install -r requirements.txt
python scripts/download_data.py         # SOTS (RESIDE) download/extract
python scripts/download_rtts.py         # 72 real RTTS images (no-reference set)
python scripts/prepare_data.py --no-download   # splits (SOTS + RTTS + sweeps)
python scripts/calibrate.py             # density stats + thresholds (calib only)
python scripts/tune_params.py           # per-class params (calib only)
python scripts/run_eval.py              # baseline vs adaptive on test splits
python scripts/run_ablations.py         # component/feature/selector ablations
python scripts/make_figures.py          # all report figures
python scripts/audit_baseline.py        # baseline fairness diagnostics
python scripts/finalize_report.py       # fill report/README numbers from results/
python -m pytest                        # full test suite (83 tests)
```

Demo:

```bash
streamlit run app/app.py
```

## Data

* **SOTS / RESIDE** — 542 unique hazy/clear pairs from indoor + outdoor SOTS.
  Split by unique clear scene: **299 calib / 243 test**; no scene leaks between splits.
  Automatic source: `https://huggingface.co/datasets/desonglll/reside-SOTS` (SOTS.zip);
  `scripts/download_data.py` also prints manual instructions if the download fails.
* **RTTS** — **72 real-world hazy photographs** from RESIDE-beta (no ground truth),
  downloaded with `scripts/download_rtts.py` from the Hugging Face mirror
  `fuhao7i/RTTS` (Apache-2.0). The exact subset is fixed in
  `scripts/rtts_subset.txt`; no-reference metrics only. To use other images, drop them
  into `data/RTTS/` and re-run `prepare_data.py`. If `data/RTTS/` is empty the pipeline
  falls back to a synthetic RTTS-style set so the no-reference check still runs, and
  `data/splits.json` records which source was used.
* **Density validation** — 8 clear scenes × 8 beta values = 64 hazy images with known
  beta. Used only for the score-vs-beta check.
* **Selector training** — 180 labelled synthetic images for the classifier ablation.

Everything is reproducible from `config/params.yaml` + `data/splits.json`. Images are
gitignored; see `data/README.md`.

## Reproducibility rules

* Thresholds and parameters are fitted on the **calib** split only.
* Test sets are untouched until `config/tuned_params.json` is written and tagged
  `v0.1-frozen-params`.
* Every table/figure is generated from `results/` by `scripts/run_eval.py`,
  `scripts/run_ablations.py`, `scripts/make_figures.py` and
  `scripts/finalize_report.py`; the report's qualitative discussion is written by hand.

## Results

See:

* `results/results_table.md` — baseline vs adaptive, overall and per haze class.
* `results/evaluation_summary.md` — paired comparison + runtime (SOTS and real RTTS).
* `results/ablations.md` — ablation table.
* `results/baseline_audit_summary.csv` + `results/figures/baseline_sanity.png` —
  proof the fixed DCP baseline is not handicapped.
* `results/figures/` — qualitative grids (SOTS + real RTTS), transmission maps,
  score-vs-beta, metrics by class, failure cases.
* `results/FINALIZATION_AUDIT.md` — v1 + v2 verification record.
* `report/report.md` — full report.
* `report/FogSense_slides.pptx` — 22-slide presentation deck with speaker notes.
* `report/FogSense_report.pdf` — printable version of the report.

Key numbers (regenerated by the scripts):

<!-- KEY_NUMBERS_START -->
| item | value |
|---|---|
| Density vs beta Spearman (within-scene mean) | 0.992 |
| SOTS baseline PSNR / SSIM | 15.71 dB / 0.8263 |
| SOTS adaptive PSNR / SSIM | 18.78 dB / 0.8896 |
| SSIM win rate | 90.1% |
| Runtime (SOTS, CPU) | 256 ms/image (3.9 FPS) |
<!-- KEY_NUMBERS_END -->

<!-- V2_NUMBERS_START -->
| item | value |
|---|---|
| v2 vs v1 SOTS PSNR / SSIM | 18.45 dB / 0.8873 vs 18.78 dB / 0.8896 |
| v2 vs CAP SOTS PSNR / SSIM | +0.36 dB / +0.1040 |
| v2 SOTS CIEDE2000 / NIQE / FADE | 9.381 / 1.794 / 0.401 |
| v2 runtime (SOTS, CPU) | 562 ms/image (same run: v1 192 ms) |
| Local density vs beta (validation) | 0.948 |
<!-- V2_NUMBERS_END -->

## v2 upgrade (opt-in)

v1.0 remains the default. A v2 pipeline adds an opt-in atmospheric-light/sky stage,
local (per-pixel) density maps, spatially blended enhancement, two stronger classical
baselines (CAP, BCCR-style) and CIEDE2000/NIQE-style/FADE-style metrics. Every feature is
behind a config flag; with all flags off the output is byte-identical to v1.0
(`tests/test_v2_compat.py`). Reproduce with:

```bash
./run_all_v2.ps1 --no-download
```

See `report/report.md` §9 and `results/v2_*` for the comparison and ablation.

## Project layout

```
config/params.yaml         every tunable value (no magic numbers in src/)
config/calibration.json    fitted normalisation + thresholds (calib only)
config/calibration_local.json  local-density stats + class centroids (calib only)
config/tuned_params.json   frozen per-class parameters (calib only)
config/tuned_params_v2.json    frozen opt-in v2 choices (calib only)
config/niqe_model.json     NIQE-style MVG fitted on calib clear images
src/
  preprocess.py            resize / denoise / float conversion
  density.py               features, normalisation, global + local density
  selector.py              3-bin rule selector, continuous + classifier variants
  dcp.py                   atmospheric light (v1/v2/quadtree), transmission, radiance
  sky.py                   conservative sky / white-object mask
  guided_filter.py         own box-filter guided filter (no opencv-contrib)
  enhance.py               Retinex, CLAHE, gray-world
  baseline.py              fixed DCP, CAP, BCCR-style baselines
  pipeline.py              full adaptive pipeline (v1 and opt-in v2)
  metrics.py               PSNR, SSIM, CIEDE2000, NIQE-style, FADE-style
  synthetic.py             scattering-model data generator
scripts/
  download_data.py         SOTS download/extract + pair discovery
  download_rtts.py         72-image real RTTS subset (RESIDE-beta)
  rtts_subset.txt          fixed RTTS file manifest
  prepare_data.py          splits + RTTS/beta-sweep generation
  calibrate.py             density stats, thresholds, classifier
  calibrate_local.py       local-density normalisation + class centroids
  fit_niqe_model.py        fit the NIQE-style model on calib clear images
  tune_params.py           two-stage per-class tuning (v1)
  tune_v2.py               calib-only v2 stage search
  run_eval.py              baseline vs adaptive evaluation (v1)
  run_eval_v2.py           v2 + CAP/BCCR + new metrics, indoor/outdoor
  run_ablations.py         v1 ablations
  run_ablations_v2.py      stepwise v1 -> v2 ablation
  validate_density_v2.py   global/local/ridge density vs beta and FADE
  profile_v2.py            stage-by-stage runtime profile
  make_figures.py          v1 report figures
  make_v2_figures.py       v2 figures (failure cases, maps, ablation, density)
  audit_baseline.py        baseline fairness diagnostics
  finalize_report.py       fill v1 report/README placeholders from results/
  finalize_report_v2.py    fill the v2 report/slides/README blocks
  verify_setup.py          dependency / data / config sanity check
app/app.py                 Streamlit demo (v2 toggle + density maps)
tests/                     pytest suite (incl. v2 compatibility/features)
report/                    report + slides
results/                   CSVs + figures
run_all.ps1                reproducible v1 run
run_all_v2.ps1             reproducible v2 run (v1 artifacts untouched)
```

## Limitations

DCP assumes a dark channel; large sky regions, white objects, night haze and
noise amplification remain failure modes. CLAHE/Retinex can increase noise in
very dense haze. The 72-image RTTS set has no clear ground truth, so the
no-reference results indicate detail/contrast trends rather than a fidelity
benchmark.

## References

* He, Sun, Tang. *Single Image Haze Removal Using Dark Channel Prior.* CVPR 2009.
* He, Sun, Tang. *Guided Image Filtering.* ECCV 2010.
* Zuiderveld. *Contrast Limited Adaptive Histogram Equalization.* 1994.
* Jobson, Rahman, Woodell. *Multiscale Retinex.* 1997.
* Li et al. *Benchmarking Single-Image Dehazing and Beyond.* IEEE TIP 2019 (RESIDE/SOTS).
