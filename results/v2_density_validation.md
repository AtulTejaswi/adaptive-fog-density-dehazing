# v2 density validation

- Validation sweep: 64 images (64 synthetic, known beta).
- Real RTTS: 72 images (no beta; correlated with FADE-style density).

| signal | Spearman vs beta (validation) | within-scene | Spearman vs FADE (RTTS) |
|---|---|---|---|
| global | 0.907 | 0.992 | 0.933 |
| local_mean | 0.948 | 1.000 | 0.817 |
| dc_only | 0.928 | nan | 0.762 |
| dc_entropy | 0.917 | nan | 0.904 |
| contrast_std | -0.780 | nan | -0.611 |
| ridge | 0.925 | 1.000 | 0.969 |

Ridge weights (standardised): {'dark_channel': 0.22122944680109635, 'entropy': 0.007072142179958993, 'contrast': -0.16958633091145414, 'saturation': -0.019248195889944402}

Local density gives the best beta correlation on the validation sweep (0.948 vs 0.907 global); calib-fitted ridge weights improve over the global score (0.925) but not over the local mean. On RTTS (FADE), ridge correlates best (0.969) while the local mean is weaker (0.817).
