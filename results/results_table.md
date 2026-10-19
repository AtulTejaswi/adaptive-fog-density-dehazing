# Results — baseline vs adaptive

| split | class | method | psnr | ssim | entropy_gain | contrast_improvement | edge_preservation | total_ms |
|---|---|---|---|---|---|---|---|---|
| test_rtts | all | adaptive |  |  | 0.6545 | 1.6954 | 2.6680 | 209.3522 |
| test_rtts | all | baseline |  |  | 0.3871 | 1.4648 | 1.9342 | 86.6860 |
| test_rtts | heavy | adaptive |  |  | 1.0604 | 2.0687 | 3.2133 | 145.3660 |
| test_rtts | heavy | baseline |  |  | 0.8855 | 1.7971 | 2.4858 | 85.4115 |
| test_rtts | light | adaptive |  |  | 0.2449 | 1.4318 | 2.0172 | 299.3851 |
| test_rtts | light | baseline |  |  | -0.1887 | 1.1905 | 1.3461 | 89.4814 |
| test_rtts | moderate | adaptive |  |  | 0.3773 | 1.3273 | 2.3959 | 227.6036 |
| test_rtts | moderate | baseline |  |  | 0.1195 | 1.1767 | 1.5889 | 86.0474 |
| test_sots | all | adaptive | 18.7750 | 0.8896 | 0.4258 | 1.3095 | 1.8484 | 258.4771 |
| test_sots | all | baseline | 15.7100 | 0.8263 | 0.1929 | 1.2406 | 1.3360 | 88.8268 |
| test_sots | heavy | adaptive | 16.5079 | 0.8672 | 0.6102 | 1.5378 | 1.9581 | 151.5991 |
| test_sots | heavy | baseline | 15.1354 | 0.8225 | 0.4889 | 1.4919 | 1.5858 | 89.6816 |
| test_sots | light | adaptive | 19.8208 | 0.9064 | 0.1774 | 1.1255 | 1.5760 | 152.9092 |
| test_sots | light | baseline | 16.5759 | 0.8399 | -0.0151 | 1.0658 | 1.2070 | 89.2390 |
| test_sots | moderate | adaptive | 19.4352 | 0.8902 | 0.5232 | 1.3156 | 2.0214 | 432.6862 |
| test_sots | moderate | baseline | 15.3221 | 0.8165 | 0.1727 | 1.2217 | 1.2759 | 87.8328 |
