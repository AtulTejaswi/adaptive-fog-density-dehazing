# CONTEXT (static project definition)

## Project
Adaptive, fog-density-aware single-image dehazing. (IPA = Image Processing & Analysis course project.)

## Problem statement
Fog and haze scatter and attenuate light before it reaches a camera, reducing contrast,
distorting colors and hiding scene detail. Fixed-parameter dehazing (e.g. standalone Dark
Channel Prior, DCP) applies the same correction strength regardless of haze density, causing
over-correction (dark, unnatural) on light haze and under-correction on dense haze.
This project first ESTIMATES fog density, then ADAPTS the dehazing strategy and parameters
accordingly, giving more consistent and visually accurate results across haze conditions.

## Required methodology (from the submitted proposal - this is the requirement)
1. **Image acquisition & preprocessing**: RESIDE benchmark (synthetic hazy-clear pairs) and
   RTTS subset (real-world hazy). Resize to standard resolution, normalize, lightly denoise.
2. **Fog density estimation**: per-image haze-severity score from classical statistics:
   dark channel mean intensity, image entropy, global contrast (Michelson / RMS).
   Combine into a normalized fog-density score in [0, 1]. No ground truth needed.
3. **Adaptive strategy selection**: categorize into light / moderate / heavy haze.
   Rule-based selector (optionally a shallow trained classifier) picks dehazing parameters and
   enhancement strategy per category, e.g. stronger DCP for heavy haze, CLAHE/Retinex-dominant
   enhancement for light haze.
4. **Dehazing & enhancement**: DCP estimates transmission map and atmospheric light; refine
   with guided filter; recover scene radiance by inverting the atmospheric scattering model
   with density-adjusted params; then CLAHE contrast enhancement, optional Retinex-based
   illumination correction, gray-world color correction for residual color cast.
5. **Quality evaluation & comparison**: full-reference PSNR, SSIM on synthetic SOTS test set;
   no-reference metrics (entropy gain, contrast improvement, edge-preservation ratio) on
   real-world images without ground truth. Compare adaptive pipeline vs fixed-parameter DCP
   baseline. Record processing time for practical feasibility.

## Atmospheric scattering model
I(x) = J(x) t(x) + A (1 - t(x)),   t(x) = exp(-beta d(x))
Recover: J(x) = (I(x) - A) / max(t(x), t0) + A

## Deliverables (assumed; confirm with course rubric -> see DECISIONS.md D-00)
- Working code (reproducible) + evaluation tables + before/after figures
- Comparison: adaptive vs fixed DCP (and ablations)
- Report + presentation + optional demo app

## Tech stack (default)
Python 3.10+, OpenCV, NumPy, SciPy, scikit-image, scikit-learn (optional classifier),
pandas, matplotlib, PyYAML, Streamlit or Gradio (demo), pytest.
Classical image processing only; NO deep dehazing networks (keep it explainable, CPU-friendly).
