# PLAN (phase-by-phase). Tick boxes as you finish. Mirror status in PROGRESS.md.

Rule: finish phases in order. Each phase ends with a git commit + PROGRESS.md update.

## Phase 0 - Setup
- [ ] Create repo structure (see README), `requirements.txt`, `.gitignore` (ignore `data/`, `*.zip`, `__pycache__`, large results)
- [ ] `config/params.yaml` skeleton (all thresholds/params live here, never hard-coded)
- [ ] Verify environment: `python -c "import cv2, skimage, sklearn"`; fix `pip install`
- [ ] Init git, connect remote GitHub repo, first push via `save_progress.sh`
Done when: fresh clone + `pip install -r requirements.txt` + `pytest` runs.

## Phase 1 - Data
- [ ] `scripts/download_data.py`: fetch SOTS (indoor + outdoor test), a training subset of RESIDE (ITS/OTS) for calibration, and RTTS subset. If auto-download is blocked, print exact manual instructions + expected folder layout in `data/README.md`.
- [ ] Validate pairing: every SOTS hazy image has a clear GT. Log counts.
- [ ] Fixed splits: `data/splits.json` -> `calib` (threshold tuning), `test_sots`, `test_rtts`. Never tune on test.
Done when: counts logged in PROGRESS.md (e.g. N calib, N SOTS, N RTTS).

## Phase 2 - Preprocessing (`src/preprocess.py`)
- [ ] Resize to standard size (default: long side 640, keep aspect; param in config)
- [ ] Normalize to float32 [0,1]
- [ ] Light denoise (bilateral or fastNlMeans, small strength; param)
- [ ] Unit test: shape, dtype, range
Done when: preprocess works on all datasets.

## Phase 3 - Fog density estimation (`src/density.py`)
- [ ] Features: (a) dark-channel mean (patch 15), (b) Shannon entropy of grayscale, (c) global contrast (Michelson and RMS)
- [ ] Normalization: min-max (or percentile) using stats from the `calib` split ONLY; store in `config/density_norm.json`
- [ ] Combine: haze score = weighted sum, with features oriented so higher = hazier
      (dark-channel mean up, entropy down, contrast down). Initial weights equal; then tune.
- [ ] Validate: on SOTS/RESIDE with known haze levels (or via synthetic haze of varying beta on clear images), score must rise monotonically with beta. Report Spearman correlation (target > 0.8).
- [ ] Figure: score vs beta, score histogram per dataset
Done when: correlation reported + figure saved to `results/density_validation.*`.

## Phase 4 - Adaptive strategy selection (`src/selector.py`)
- [ ] Thresholds t1, t2 -> light (<t1), moderate, heavy (>=t2). Initial: tertiles of calib score distribution.
- [ ] Per-class parameter sets in `config/params.yaml`:
      | class    | omega | t0   | patch | GF radius/eps | CLAHE clip | Retinex | gray-world |
      | light    | 0.70  | 0.30 | 15    | 40 / 1e-3     | 3.0 (dominant) | on  | on |
      | moderate | 0.85  | 0.20 | 15    | 60 / 1e-3     | 2.0        | optional | on |
      | heavy    | 0.95  | 0.10 | 11-15 | 60 / 1e-4     | 1.5        | off | on |
      (starting guesses; tune in Phase 7)
- [ ] Optional: shallow classifier (DecisionTree depth<=3 or LogReg) on the 3 features, labels from beta bins in synthetic data. Keep rule-based as primary; classifier is an ablation.
- [ ] Optional smooth variant: interpolate omega/t0 continuously from the density score (ablation "continuous vs 3-bin").
Done when: selector returns (class, params) for any image.

## Phase 5 - Baseline & core DCP (`src/dcp.py`, `src/guided_filter.py`, `src/baseline.py`)
- [ ] Dark channel; atmospheric light from top 0.1% brightest dark-channel pixels
- [ ] Transmission t = 1 - omega * darkchannel(I/A)
- [ ] Guided filter refinement (implement own or `cv2.ximgproc.guidedFilter`; fallback to own box-filter version so no contrib dependency)
- [ ] Radiance recovery with t0 floor
- [ ] `baseline.py`: fixed-parameter DCP (omega=0.95, t0=0.1, patch 15, GF 60/1e-4), no enhancement. This is THE baseline.
- [ ] Sanity: runs on 10 images, outputs visually dehazed
Done when: baseline outputs saved for all test sets.

## Phase 6 - Enhancement (`src/enhance.py`)
- [ ] CLAHE on L channel (LAB), clip/tile from params
- [ ] Retinex (single-scale or MSRCR; keep single-scale for speed, flag for MSR)
- [ ] Gray-world color correction
- [ ] Each function togglable via params so ablations are one-line config changes

## Phase 7 - Full adaptive pipeline (`src/pipeline.py`) + tuning
- [ ] `dehaze_adaptive(img) -> (out, info)` where info = score, class, params, timing
- [ ] Tune per-class params on `calib` split only (small grid search, objective: SSIM on synthetic + sanity no-reference metrics). Log the grid + chosen values in DECISIONS.md.
- [ ] Freeze params in config; tag git `v0.1-frozen-params` BEFORE touching test sets
Done when: params frozen and tagged.

## Phase 8 - Evaluation (`src/metrics.py`, `scripts/run_eval.py`)
- [ ] Full-reference on SOTS: PSNR, SSIM (skimage), for baseline vs adaptive
- [ ] No-reference on RTTS (and SOTS too): entropy gain, contrast improvement (RMS/Michelson ratio out/in), edge-preservation ratio (e.g. Sobel/Canny edge-energy out/in)
- [ ] Runtime per image (mean +- std, at fixed resolution, CPU model noted)
- [ ] Results broken down by haze class (light/moderate/heavy) - this is the KEY result: baseline over-corrects light, under-corrects heavy; adaptive should win or tie in each bin
- [ ] Stats: mean, std, paired t-test or Wilcoxon, win-rate
- [ ] Outputs: `results/metrics_*.csv`, summary table (markdown)

## Phase 9 - Ablations (each = one row in a table)
- [ ] Baseline DCP
- [ ] Adaptive DCP only (no enhancement)
- [ ] + CLAHE
- [ ] + Retinex
- [ ] + gray-world (= full)
- [ ] Features: dark-channel only vs +entropy vs +contrast (full)
- [ ] 3-bin vs continuous vs classifier selector

## Phase 10 - Figures, demo, report
- [ ] Figures: before/after grids per class, transmission maps, failure cases (be honest, include 2-3), score-vs-beta plot, bar charts of metrics by class
- [ ] Demo app `app/app.py` (upload image -> shows score, class, params, baseline vs adaptive side by side)
- [ ] Report sections: Introduction, Related work (DCP, guided filter, CLAHE, Retinex), Method (5 stages), Experiments, Results, Ablations, Limitations (sky regions, white objects, night haze, noise amplification), Conclusion
- [ ] Slides
- [ ] README with reproduce-in-3-commands instructions
- [ ] Final: tag `v1.0`, clean repo, results CSVs committed

## Risk register
| Risk | Mitigation |
|---|---|
| RESIDE/RTTS download blocked or huge | Use small subsets (SOTS ~500 + ~300 calib + ~100 RTTS); manual-download instructions |
| Density score not monotonic with haze | Reweight features; add percentile normalization; report honestly |
| Adaptive not better than baseline on all metrics | Report per-class; analyze why; PSNR/SSIM are not the only story, include no-ref metrics |
| Sky/white regions break DCP | Cap transmission floor, sky-aware A; list under limitations |
| Out of agent credits mid-phase | Update PROGRESS.md + HANDOFF.md every ~30 min of work and at every commit |
