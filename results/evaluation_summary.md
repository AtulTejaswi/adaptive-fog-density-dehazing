# Evaluation summary

Generated: 2026-10-20  
Splits: test_rtts, test_sots

## Results table (mean)

| split | class | method | contrast_improvement | edge_preservation | entropy_gain | psnr | ssim | total_ms |
|---|---|---|---|---|---|---|---|---|
| test_rtts | all | adaptive | 1.2376 | 1.6733 | 0.4165 |  |  | 184.2860 |
| test_rtts | all | baseline | 1.0648 | 1.1967 | 0.0912 |  |  | 93.6030 |
| test_rtts | heavy | adaptive | 1.5693 | 1.9917 | 0.9994 |  |  | 145.9313 |
| test_rtts | heavy | baseline | 1.4211 | 1.5967 | 0.7749 |  |  | 91.6385 |
| test_rtts | light | adaptive | 1.0358 | 1.3885 | 0.0992 |  |  | 148.0721 |
| test_rtts | light | baseline | 0.8918 | 0.9888 | -0.1971 |  |  | 95.4192 |
| test_rtts | moderate | adaptive | 1.3865 | 2.1562 | 0.5391 |  |  | 389.0011 |
| test_rtts | moderate | baseline | 1.0615 | 1.2441 | -0.0773 |  |  | 90.4050 |
| test_sots | all | adaptive | 1.3095 | 1.8484 | 0.4258 | 18.7750 | 0.8896 | 256.1686 |
| test_sots | all | baseline | 1.2406 | 1.3360 | 0.1929 | 15.7100 | 0.8263 | 87.1733 |
| test_sots | heavy | adaptive | 1.5378 | 1.9581 | 0.6102 | 16.5079 | 0.8672 | 148.3146 |
| test_sots | heavy | baseline | 1.4919 | 1.5858 | 0.4889 | 15.1354 | 0.8225 | 87.3722 |
| test_sots | light | adaptive | 1.1255 | 1.5760 | 0.1774 | 19.8208 | 0.9064 | 152.1749 |
| test_sots | light | baseline | 1.0658 | 1.2070 | -0.0151 | 16.5759 | 0.8399 | 88.7939 |
| test_sots | moderate | adaptive | 1.3156 | 2.0214 | 0.5232 | 19.4352 | 0.8902 | 429.6232 |
| test_sots | moderate | baseline | 1.2217 | 1.2759 | 0.1727 | 15.3221 | 0.8165 | 85.5335 |

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
| test_rtts | 72 | 23.9200 | 57.8186 | 65.7792 | 184.2860 | 98.6402 | 5.4263 |
| test_sots | 243 | 28.6927 | 67.7161 | 139.8677 | 256.1686 | 142.6126 | 3.9037 |

## Per-image data

See `metrics_per_image.csv`, `comparison.csv`, `results_table.csv`.
