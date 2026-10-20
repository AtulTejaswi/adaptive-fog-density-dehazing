# HANDOFF (overwrite at the end of every session; keep under 30 lines)

## State
Project complete: v1.0 is the reproducible default, plus an **opt-in v2** upgrade
(MASTER_PROMPT_v4) on branch `v2-upgrade`. v1 tags `v0.1-frozen-params` / `v1.0` are
untouched. v2 params were frozen at `v2.0-frozen-params` before the first v2 test run;
final deliverable tag `v2.0`. 83 tests pass, including a bit-exact flags-off v1
compatibility test (`tests/test_v2_compat.py`). v2 is **not** an aggregate win over v1:
SOTS 18.45 dB / 0.8873 vs 18.78 / 0.8896; it helps indoor (+0.75 dB / +0.0118) and
CIEDE2000 and hurts the 221 outdoor pairs. CAP is a strong PSNR baseline (18.09 / 0.7833)
vs fixed DCP (15.71 / 0.8263). The sky step alone is +0.64 dB / +0.0037; the local
omega/t0 maps as tuned lose 0.87 dB / 0.0119 SSIM. v1 stays the recommended default.

## Do next
1. Read report §9, `results/v2_*`, `results/v2_key_findings.md`.
2. Demo: `streamlit run app/app.py` (v2 toggle, local-density/sky maps).
3. Full v2 run: `./run_all_v2.ps1 --no-download`; v1 run: `./run_all.ps1`.
4. Tests: `python -m pytest -q` (83). Do not retune v2 on test; refit on calib and re-tag.

## Gotchas
- Never tune on `test_sots` / `test_rtts`; v2 artifacts are calib-only.
- NIQE-style / FADE-style are proxies, not the official learned models.
- v2 local density is the main cost (~405 ms/image); v2 total 562 ms vs v1 192 ms.
- CAP is real; BCCR is a documented simplified version (boundary constraint + GF).
- Windows cp1252 console: avoid printing Greek symbols; files are UTF-8.
- `data/` images are gitignored; `data/splits.json` + `data/README.md` are committed.

## Files touched last session
`src/{sky,dcp,density,selector,pipeline,baseline,metrics,config,enhance}.py`, `app/app.py`,
`config/{calibration_local,niqe_model,tuned_params_v2}.json`, `scripts/*v2*`,
`scripts/profile_v2.py`, `run_all_v2.ps1`, `tests/test_v2_*.py`, `report/*`,
`README.md`, `PROGRESS.md`, `DECISIONS.md`, `HANDOFF.md`, `results/v2_*`.
