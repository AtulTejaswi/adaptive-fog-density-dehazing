# Evaluation summary

Generated: 2026-10-19  
Splits: test_rtts, test_sots

## Results table (mean)

| split | class | method | contrast_improvement | edge_preservation | entropy_gain | psnr | ssim | total_ms |
|---|---|---|---|---|---|---|---|---|
| test_rtts | all | adaptive | 1.2376 | 1.6733 | 0.4165 |  |  | 205.9191 |
| test_rtts | all | baseline | 1.0648 | 1.1967 | 0.0912 |  |  | 111.0164 |
| test_rtts | heavy | adaptive | 1.5693 | 1.9917 | 0.9994 |  |  | 162.1244 |
| test_rtts | heavy | baseline | 1.4211 | 1.5967 | 0.7749 |  |  | 109.2555 |
| test_rtts | light | adaptive | 1.0358 | 1.3885 | 0.0992 |  |  | 166.5462 |
| test_rtts | light | baseline | 0.8918 | 0.9888 | -0.1971 |  |  | 111.9271 |
| test_rtts | moderate | adaptive | 1.3865 | 2.1562 | 0.5391 |  |  | 432.2989 |
| test_rtts | moderate | baseline | 1.0615 | 1.2441 | -0.0773 |  |  | 110.8238 |
| test_sots | all | adaptive | 1.3095 | 1.8484 | 0.4258 | 18.7750 | 0.8896 | 273.4861 |
| test_sots | all | baseline | 1.2406 | 1.3360 | 0.1929 | 15.7100 | 0.8263 | 95.2135 |
| test_sots | heavy | adaptive | 1.5378 | 1.9581 | 0.6102 | 16.5079 | 0.8672 | 159.2928 |
| test_sots | heavy | baseline | 1.4919 | 1.5858 | 0.4889 | 15.1354 | 0.8225 | 94.2812 |
| test_sots | light | adaptive | 1.1255 | 1.5760 | 0.1774 | 19.8208 | 0.9064 | 163.3359 |
| test_sots | light | baseline | 1.0658 | 1.2070 | -0.0151 | 16.5759 | 0.8399 | 94.6438 |
| test_sots | moderate | adaptive | 1.3156 | 2.0214 | 0.5232 | 19.4352 | 0.8902 | 457.1767 |
| test_sots | moderate | baseline | 1.2217 | 1.2759 | 0.1727 | 15.3221 | 0.8165 | 96.4087 |

## Paired comparison (adaptive - baseline)

| split | metric | n | baseline_mean | adaptive_mean | mean_diff | win_rate | p_value |
|---|---|---|---|---|---|---|---|
| test_rtts | entropy_gain | 72 | 0.0912 | 0.4165 | 0.3253 | 0.9722 | 0.0000 |
| test_rtts | contrast_improvement | 72 | 1.0648 | 1.2376 | 0.1728 | 0.9583 | 0.0000 |
| test_rtts | edge_preservation | 72 | 1.1967 | 1.6733 | 0.4767 | 1.0000 | 0.0000 |
| test_rtts | color_cast_out | 72 | 0.0263 | 0.0129 | -0.0134 | 0.0000 | 0.0000 |
| test_rtts | colorfulness_out | 72 | 0.1126 | 0.0931 | -0.0195 | 0.1111 | 0.0000 |
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
| test_rtts | 72 | 25.6624 | 61.9128 | 69.5633 | 205.9191 | 111.8503 | 4.8563 |
| test_sots | 243 | 31.2658 | 74.0650 | 147.6307 | 273.4861 | 151.4473 | 3.6565 |

## Per-image data

See `metrics_per_image.csv`, `comparison.csv`, `results_table.csv`.
