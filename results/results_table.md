# Results — baseline vs adaptive

| split | class | method | psnr | ssim | entropy_gain | contrast_improvement | edge_preservation | total_ms |
|---|---|---|---|---|---|---|---|---|
| test_rtts | all | adaptive |  |  | 0.4165 | 1.2376 | 1.6733 | 184.2860 |
| test_rtts | all | baseline |  |  | 0.0912 | 1.0648 | 1.1967 | 93.6030 |
| test_rtts | heavy | adaptive |  |  | 0.9994 | 1.5693 | 1.9917 | 145.9313 |
| test_rtts | heavy | baseline |  |  | 0.7749 | 1.4211 | 1.5967 | 91.6385 |
| test_rtts | light | adaptive |  |  | 0.0992 | 1.0358 | 1.3885 | 148.0721 |
| test_rtts | light | baseline |  |  | -0.1971 | 0.8918 | 0.9888 | 95.4192 |
| test_rtts | moderate | adaptive |  |  | 0.5391 | 1.3865 | 2.1562 | 389.0011 |
| test_rtts | moderate | baseline |  |  | -0.0773 | 1.0615 | 1.2441 | 90.4050 |
| test_sots | all | adaptive | 18.7750 | 0.8896 | 0.4258 | 1.3095 | 1.8484 | 256.1686 |
| test_sots | all | baseline | 15.7100 | 0.8263 | 0.1929 | 1.2406 | 1.3360 | 87.1733 |
| test_sots | heavy | adaptive | 16.5079 | 0.8672 | 0.6102 | 1.5378 | 1.9581 | 148.3146 |
| test_sots | heavy | baseline | 15.1354 | 0.8225 | 0.4889 | 1.4919 | 1.5858 | 87.3722 |
| test_sots | light | adaptive | 19.8208 | 0.9064 | 0.1774 | 1.1255 | 1.5760 | 152.1749 |
| test_sots | light | baseline | 16.5759 | 0.8399 | -0.0151 | 1.0658 | 1.2070 | 88.7939 |
| test_sots | moderate | adaptive | 19.4352 | 0.8902 | 0.5232 | 1.3156 | 2.0214 | 429.6232 |
| test_sots | moderate | baseline | 15.3221 | 0.8165 | 0.1727 | 1.2217 | 1.2759 | 85.5335 |
