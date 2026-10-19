# Results directory

All numbers in this folder are produced by the scripts; nothing is hand-edited.

| file | produced by | contents |
|---|---|---|
| `density_validation.csv` | `scripts/calibrate.py` | per-image score + features for the beta sweep |
| `density_validation_summary.json` | `scripts/calibrate.py` | overall / within-scene Spearman |
| `selector_classifier.json` | `scripts/calibrate.py` | classifier holdout accuracy |
| `tuning_grid.csv` | `scripts/tune_params.py` | every calibration configuration tried |
| `metrics_per_image.csv` | `scripts/run_eval.py` | one row per image × method |
| `metrics_summary.csv` | `scripts/run_eval.py` | mean/std/median per split / class / metric |
| `results_table.csv/.md` | `scripts/run_eval.py` | compact baseline-vs-adaptive table |
| `comparison.csv` | `scripts/run_eval.py` | paired diffs, win rates, Wilcoxon p-values |
| `evaluation_summary.md` | `scripts/run_eval.py` | human-readable summary |
| `runtime.csv`, `runtime_summary.csv` | `scripts/run_eval.py` | per-image and mean runtime |
| `key_numbers.json` | `scripts/run_eval.py` | machine-readable headline numbers |
| `ablations.csv/.md`, `ablations_per_image.csv` | `scripts/run_ablations.py` | ablation results |
| `figures/*.png` | `scripts/make_figures.py` | all report figures |
| `key_findings.md` | `scripts/finalize_report.py` | generated bullet-point findings |

`results/images/` contains cached qualitative outputs and is gitignored.
