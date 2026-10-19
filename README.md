# Adaptive, Fog-Density-Aware Single-Image Dehazing

Course project for **Image Processing & Analysis (IPA)**. A classical, explainable
pipeline that first *estimates haze density* from image statistics, then adapts the
dehazing strength and enhancement strategy to that density. The adaptive pipeline is
compared against a fixed-parameter Dark Channel Prior (DCP) baseline on SOTS
(RESIDE, synthetic hazy/clear pairs) and a 72-image real-world RTTS no-reference set.

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
python -m pytest                        # full test suite (51 tests)
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
* `results/FINALIZATION_AUDIT.md` — v2 verification record (A–E).
* `report/report.md` — full report draft.

Key numbers (regenerated by the scripts):

<!-- KEY_NUMBERS_START -->
| item | value |
|---|---|
| Density vs beta Spearman (within-scene mean) | 0.992 |
| SOTS baseline PSNR / SSIM | 15.71 dB / 0.8263 |
| SOTS adaptive PSNR / SSIM | 18.78 dB / 0.8896 |
| SSIM win rate | 90.1% |
| Runtime (SOTS, CPU) | 273 ms/image (3.7 FPS) |
<!-- KEY_NUMBERS_END -->

## Project layout

```
config/params.yaml         every tunable value (no magic numbers in src/)
config/calibration.json    fitted normalisation + thresholds (calib only)
config/tuned_params.json   frozen per-class parameters (calib only)
src/
  preprocess.py            resize / denoise / float conversion
  density.py               features, normalisation, fog-density score
  selector.py              3-bin rule selector, continuous + classifier variants
  dcp.py                   atmospheric light, transmission, radiance recovery
  guided_filter.py         own box-filter guided filter (no opencv-contrib)
  enhance.py               Retinex, CLAHE, gray-world
  baseline.py              fixed-parameter DCP baseline
  pipeline.py              full adaptive pipeline
  metrics.py               PSNR, SSIM, no-reference metrics, significance tests
  synthetic.py             scattering-model data generator
scripts/
  download_data.py         SOTS download/extract + pair discovery
  download_rtts.py         72-image real RTTS subset (RESIDE-beta)
  rtts_subset.txt          fixed RTTS file manifest
  prepare_data.py          splits + RTTS/beta-sweep generation
  calibrate.py             density stats, thresholds, classifier
  tune_params.py           two-stage per-class tuning
  run_eval.py              baseline vs adaptive evaluation
  run_ablations.py         ablations
  make_figures.py          report figures
  audit_baseline.py        baseline fairness diagnostics
  finalize_report.py       fill report/README placeholders from results/
  verify_setup.py          dependency / data / config sanity check
app/app.py                 Streamlit demo
tests/                     pytest suite
report/                    report + slides
results/                   CSVs + figures
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
