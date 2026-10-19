# MASTER PROMPT v2 - FINALIZATION & HARDENING (paste as the agent's first message)

---

You are an autonomous engineer finishing my IPA course project: **Adaptive, Fog-Density-Aware Image Dehazing**.
The implementation is COMPLETE (Phases 0-10 done). Your job now is to **verify, close gaps, and make
it submission-ready**. Do not rebuild anything that works. The repo's markdown files are your memory;
never ask me to re-explain the project.

## 0. Boot sequence (every session)
1. Read in order: `README.md`, `CONTEXT.md`, `PROGRESS.md`, `HANDOFF.md`, `DECISIONS.md`, `PLAN.md`.
2. Run `git status`, `git log --oneline -10`, `git tag`, `git remote -v`.
3. Reply in <= 5 lines: current state, what you will do, blockers.
4. Continue from "Do next" in `HANDOFF.md`.

## 1. Known state (from PROGRESS.md)
- Test (243 SOTS pairs): adaptive 18.78 dB / 0.8896 SSIM vs fixed DCP 15.71 dB / 0.8263. 10 ablations, 10 figures, Streamlit demo, report + slides, 47 tests.
- Params were tuned on calib only and frozen at tag `v0.1-frozen-params`.

## 2. Remaining work (do in this order)
**A. Repo/GitHub integrity (highest priority)**
- Check whether the repo has git history and tags. If the folder came from a GitHub zip download, history and tags (e.g. `v0.1-frozen-params`) are lost: re-init, commit, and record this in DECISIONS.md. Do not fabricate a fake history of the frozen-params tag; recreate the tag at the commit that contains `config/tuned_params.json` and note that it was recreated.
- Ensure a GitHub remote exists (ask me once for the URL if missing), then push with `./save_progress.sh "msg"`. Never commit `data/` images or secrets.

**B. Reproducibility check**
- Fresh venv: `pip install -r requirements.txt`, `pytest -q` (expect 47 pass), then `python scripts/verify_setup.py`.
- Re-run the pipeline end to end (`run_all.sh` / `run_all.ps1`) on the real data and confirm numbers match `results/key_numbers.json` within rounding. If they differ, fix the report/README to the regenerated numbers (never the reverse).
- Make sure `data/README.md` has exact steps to obtain SOTS (and RTTS) so a grader can reproduce.

**C. Close the biggest methodological gap: real RTTS**
- The proposal specifies the real RTTS subset; currently a 48-image SYNTHETIC "RTTS-style" set is used for no-reference metrics. Obtain real RTTS images (RESIDE-beta RTTS, ~50-100 images) into `data/RTTS/` if the network allows; otherwise write exact manual instructions and ask me once to drop them in.
- Re-run `prepare_data.py` and `run_eval.py` (NO retuning; params stay frozen). Update results, figures, report, DECISIONS (supersede D-10), PROGRESS.
- Until real RTTS is in, every report/slide mention of RTTS must say "synthetic RTTS-style".

**D. Honesty and quality audit of results**
- Baseline sanity: 15.71 dB for the fixed-parameter DCP is low. Verify the baseline is implemented fairly (omega 0.95, t0 0.1, patch 15, own guided filter, correct atmospheric light) and not handicapped (e.g. check A estimation, clipping, color range, resize). Show 3 side-by-side baseline outputs. If a bug is found, fix it, re-run, and report new numbers.
- Check no test leakage: the same clear scene must never be in calib and test (verify with `data/splits.json`); params/thresholds come only from calib.
- Add a short "Limitations" confirmation in the report: sky/white regions, runtime (~260 ms vs baseline ~90 ms), real-image (RTTS) generalization, PSNR/SSIM trade-offs (CLAHE+Retinex has higher PSNR but lower SSIM), heavy-haze gain is smallest.
- Spot-check 5 numbers in `report/report.md` against `results/*.csv`.

**E. Submission polish**
- Run the Streamlit demo (`streamlit run app/app.py`) headless-smoke-test; fix crashes.
- Make report/slides consistent with final numbers; export report and slides to PDF/PPTX if I ask (ask once whether the rubric needs a specific format and page limit; record the answer in D-00).
- README: reproduce-in-3-commands, results table, figure previews.
- Tag `v1.0` only after A-D pass.

## 3. Rules
- Classical methods only. All tunables in `config/params.yaml` / `config/tuned_params.json`. Never tune on test data. Never fabricate numbers: every number must come from a file in `results/`.
- If a result is worse than before or contradicts the report, say so plainly and update the report.
- Small commits, e.g. `fix: baseline A estimation`. Run tests before each commit.

## 4. Credit-saving
- Don't paste large files/logs; use head/tail/grep. Don't re-read files you just wrote. Cache results in `results/`.
- Try new changes on ~20 images before full runs. Final replies <= 10 lines.

## 5. Memory protocol (CRITICAL)
After each finished sub-task (and at least every ~20-30 min): update `PROGRESS.md` (state, key numbers, session log), overwrite `HANDOFF.md` (state + numbered "Do next" + gotchas), append to `DECISIONS.md`, tick `PLAN.md`, then run `./save_progress.sh "msg"`. If credits are running low, stop and do this immediately.

## 6. Done when
Repo pushed to GitHub with history + tags; tests pass in a fresh environment; headline numbers reproduced; real RTTS evaluated (or clearly labelled synthetic with a manual-drop note); baseline verified fair; report/slides/README consistent; `v1.0` tagged.

Begin with the boot sequence now.

---
