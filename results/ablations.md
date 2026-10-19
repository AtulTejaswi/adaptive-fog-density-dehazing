# Ablation study (test split means)

| variant | group | n | psnr | ssim | entropy_gain | contrast_improvement | edge_preservation | color_cast_out | runtime_ms |
|---|---|---|---|---|---|---|---|---|---|
| baseline_dcp | baseline | 243 | 15.7100 | 0.8263 | 0.1929 | 1.2406 | 1.3360 | 0.0376 | 69.1058 |
| adaptive_no_enh | component | 243 | 17.7705 | 0.8726 | 0.2428 | 1.3319 | 1.3835 | 0.0337 | 99.8213 |
| adaptive_clahe | component | 243 | 18.1839 | 0.8850 | 0.3697 | 1.3173 | 1.7287 | 0.0339 | 116.0220 |
| adaptive_clahe_retinex | component | 243 | 19.3042 | 0.8840 | 0.5337 | 1.3151 | 2.0560 | 0.0389 | 399.6646 |
| adaptive_full | component | 243 | 18.7750 | 0.8896 | 0.4258 | 1.3095 | 1.8484 | 0.0187 | 235.3790 |
| density_dc_only | density_features | 243 | 18.4767 | 0.8831 | 0.4121 | 1.2985 | 1.8218 | 0.0185 | 232.4757 |
| density_dc_entropy | density_features | 243 | 18.8355 | 0.8901 | 0.4276 | 1.3099 | 1.8496 | 0.0183 | 241.1430 |
| density_full | density_features | 243 | 18.7750 | 0.8896 | 0.4258 | 1.3095 | 1.8484 | 0.0187 | 235.8943 |
| selector_continuous | selector | 243 | 18.8002 | 0.8574 | 0.5385 | 1.2317 | 2.1860 | 0.0170 | 412.2332 |
| selector_classifier | selector | 243 | 18.4006 | 0.8780 | 0.4464 | 1.3053 | 1.8592 | 0.0201 | 294.0795 |
