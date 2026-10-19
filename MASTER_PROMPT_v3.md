# MASTER PROMPT v3 - END-TO-END ACCEPTANCE & SUBMISSION (paste as the agent's first message)

---

You are an autonomous engineer doing the final acceptance pass on my IPA course project:
**Adaptive, Fog-Density-Aware Image Dehazing**. The method is implemented, tuned, frozen and
evaluated (Phases 0-11 done, tags `v0.1-frozen-params` and `v1.0`). The repo's markdown files
are your memory; never ask me to re-explain the project.

**This is VERIFICATION ONLY. Do NOT retune parameters or change the method.** If you find a bug,
fix it, re-run affected steps, and report the new numbers honestly.

## 0. Boot sequence
1. Read in order: `README.md`, `CONTEXT.md`, `PROGRESS.md`, `HANDOFF.md`, `DECISIONS.md`, `results/FINALIZATION_AUDIT.md`.
2. Run `git status`, `git log --oneline -10`, `git tag`, `git remote -v`.
3. Reply in <= 5 lines: current state, what you will do, blockers. Then start.

## 1. Acceptance steps (do in order; save progress after each)
**1. Clean environment**
- Fresh venv, `pip install -r requirements.txt`, then `python scripts/verify_setup.py` and `python -m pytest -q`. Expect 51 passing tests; report the count.

**2. Data from scratch**
- Delete image folders `data/SOTS` and `data/RTTS` (keep `splits.json`, `README.md`).
- Rebuild: `python scripts/download_data.py`, `python scripts/download_rtts.py`, `python scripts/prepare_data.py --no-download`.
- Confirm `data/splits.json`: calib 299, test_sots 243, test_rtts 72, selector_train 180, density_validation 64; calib and test scenes disjoint.
- If a download is blocked, don't loop: record exact manual steps in `data/README.md`, tell me once, continue with steps that don't need it.

**3. Full pipeline**
- Run `run_all` (`.ps1` on Windows, `.sh` otherwise): calibration, density validation, evaluation, ablations, figures, runtime. It must finish without errors.

**4. Numbers must match**
- Compare `results/key_numbers.json` with `PROGRESS.md` and `report/report.md`: SOTS baseline 15.71 dB / 0.8263, adaptive 18.78 dB / 0.8896; per-class results; real RTTS entropy +0.325, contrast +0.173, edge +0.477; ablation rows; density Spearman 0.907 overall / 0.992 within-scene; runtime.
- Rounding-level differences are fine (runtime varies by machine). Anything else: update the docs to the regenerated numbers (never the reverse) and log it in DECISIONS.md.
- Spot-check at least 10 numbers in `report/report.md` and `report/slides.md` against `results/*.csv`.

**5. Edge cases (add tests if missing)**
- Tiny image, very large image, grayscale, 4-channel PNG, pure white, pure black, haze-free image, corrupt file.
- Each must work or fail with a clear message; no silent crash, no NaN/inf. Output stays in [0,1] with the input's shape. Same input twice gives identical output (determinism).

**6. Demo**
- Smoke-test `streamlit run app/app.py` headless (or import-test). With one SOTS and one RTTS image it must show score, class, parameters and baseline vs adaptive output without errors.

**7. Repo and docs**
- `git status` clean; tags `v0.1-frozen-params` and `v1.0` present; no data images or secrets tracked.
- Follow the README reproduce steps literally; fix any step that fails.
- If anything changed: update `PROGRESS.md`, `HANDOFF.md`, `DECISIONS.md`, run `./save_progress.sh "e2e acceptance"`. Move `v1.0` only if results or docs changed, and note it in DECISIONS.md. Never move `v0.1-frozen-params`.

**8. Optional exports (only if I give a required format; otherwise skip)**
- Export `report/report.md` to PDF/DOCX and `report/slides.md` to PPTX; check every figure renders and the page limit is met. Record format and limit in D-00.

## 2. Rules
- Classical methods only. Never tune on test data. Never fabricate numbers: every figure comes from a file in `results/`.
- If a result is worse than before or contradicts the report, say so plainly and correct the report.
- Small commits with clear messages. Run tests before each commit.

## 3. Credit-saving
- Don't paste large files/logs; use head/tail/grep. Don't re-read files you just wrote. Cache results in `results/`.
- If credits run low: do steps 1, 3, 4, 7 first; then 2, 5, 6. Stop and save progress (memory protocol) before running out.
- Final replies <= 10 lines.

## 4. Memory protocol (CRITICAL)
After each finished step (and at least every ~20-30 min): update `PROGRESS.md` (state, key numbers, session log), overwrite `HANDOFF.md` (state + numbered "Do next" + gotchas), append to `DECISIONS.md`, then run `./save_progress.sh "msg"`.

## 5. Final report (<= 15 lines, also appended as a new section in `results/FINALIZATION_AUDIT.md`)
Pass/fail for steps 1-7, test count, any number that changed, any bug fixed, anything still open.

## 6. Done when
Fresh-environment tests pass, data rebuilds from scratch, the full pipeline runs, headline numbers reproduce, edge cases are handled, the demo runs, the repo is clean and pushed with both tags, and the final report is written.

Begin with the boot sequence now.

---
