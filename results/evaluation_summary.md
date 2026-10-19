# Evaluation summary

Generated: 2026-10-19  
Splits: test_rtts, test_sots

## Results table (mean)

| split | class | method | contrast_improvement | edge_preservation | entropy_gain | psnr | ssim | total_ms |
|---|---|---|---|---|---|---|---|---|
| test_rtts | all | adaptive | 1.6954 | 2.6680 | 0.6545 |  |  | 209.3522 |
| test_rtts | all | baseline | 1.4648 | 1.9342 | 0.3871 |  |  | 86.6860 |
| test_rtts | heavy | adaptive | 2.0687 | 3.2133 | 1.0604 |  |  | 145.3660 |
| test_rtts | heavy | baseline | 1.7971 | 2.4858 | 0.8855 |  |  | 85.4115 |
| test_rtts | light | adaptive | 1.4318 | 2.0172 | 0.2449 |  |  | 299.3851 |
| test_rtts | light | baseline | 1.1905 | 1.3461 | -0.1887 |  |  | 89.4814 |
| test_rtts | moderate | adaptive | 1.3273 | 2.3959 | 0.3773 |  |  | 227.6036 |
| test_rtts | moderate | baseline | 1.1767 | 1.5889 | 0.1195 |  |  | 86.0474 |
| test_sots | all | adaptive | 1.3095 | 1.8484 | 0.4258 | 18.7750 | 0.8896 | 258.4771 |
| test_sots | all | baseline | 1.2406 | 1.3360 | 0.1929 | 15.7100 | 0.8263 | 88.8268 |
| test_sots | heavy | adaptive | 1.5378 | 1.9581 | 0.6102 | 16.5079 | 0.8672 | 151.5991 |
| test_sots | heavy | baseline | 1.4919 | 1.5858 | 0.4889 | 15.1354 | 0.8225 | 89.6816 |
| test_sots | light | adaptive | 1.1255 | 1.5760 | 0.1774 | 19.8208 | 0.9064 | 152.9092 |
| test_sots | light | baseline | 1.0658 | 1.2070 | -0.0151 | 16.5759 | 0.8399 | 89.2390 |
| test_sots | moderate | adaptive | 1.3156 | 2.0214 | 0.5232 | 19.4352 | 0.8902 | 432.6862 |
| test_sots | moderate | baseline | 1.2217 | 1.2759 | 0.1727 | 15.3221 | 0.8165 | 87.8328 |

## Paired comparison (adaptive - baseline)

| split | metric | n | baseline_mean | adaptive_mean | mean_diff | win_rate | p_value |
|---|---|---|---|---|---|---|---|
| test_rtts | entropy_gain | 48 | 0.3871 | 0.6545 | 0.2674 | 0.9792 | 0.0000 |
| test_rtts | contrast_improvement | 48 | 1.4648 | 1.6954 | 0.2306 | 1.0000 | 0.0000 |
| test_rtts | edge_preservation | 48 | 1.9342 | 2.6680 | 0.7337 | 1.0000 | 0.0000 |
| test_rtts | color_cast_out | 48 | 0.1240 | 0.0853 | -0.0387 | 0.0000 | 0.0000 |
| test_rtts | colorfulness_out | 48 | 0.2496 | 0.2228 | -0.0268 | 0.1250 | 0.0000 |
| test_sots | psnr | 243 | 15.7100 | 18.7750 | 3.0651 | 0.9630 | 0.0000 |
| test_sots | ssim | 243 | 0.8263 | 0.8896 | 0.0633 | 0.9012 | 0.0000 |
| test_sots | psnr_gain | 243 | -0.1603 | 2.9048 | 3.0651 | 0.9630 | 0.0000 |
| test_sots | ssim_gain | 243 | 0.0080 | 0.0712 | 0.0633 | 0.9012 | 0.0000 |
| test_sots | entropy_gain | 243 | 0.1929 | 0.4258 | 0.2330 | 0.9588 | 0.0000 |
| test_sots | contrast_improvement | 243 | 1.2406 | 1.3095 | 0.0689 | 0.7531 | 0.0000 |
| test_sots | edge_preservation | 243 | 1.3360 | 1.8484 | 0.5124 | 1.0000 | 0.0000 |
| test_sots | color_cast_out | 243 | 0.0376 | 0.0187 | -0.0189 | 0.0082 | 0.0000 |
| test_sots | colorfulness_out | 243 | 0.1873 | 0.1570 | -0.0303 | 0.1399 | 0.0000 |

## Runtime (mean, includes preprocessing)

| split | n | density_ms | dcp_ms | enhance_ms | total_ms | total_std_ms | fps |
|---|---|---|---|---|---|---|---|
| test_rtts | 48 | 29.1238 | 67.4823 | 92.3278 | 209.3522 | 113.6066 | 4.7766 |
| test_sots | 243 | 28.8480 | 68.1663 | 141.3383 | 258.4771 | 143.1628 | 3.8688 |

## Per-image data

See `metrics_per_image.csv`, `comparison.csv`, `results_table.csv`.
