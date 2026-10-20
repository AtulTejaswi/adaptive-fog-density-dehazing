# v2 ablation (test split means)

| variant | note | n | psnr | ssim | ciede2000 | niqe_out | fade_out | entropy_gain | contrast_improvement | edge_preservation | color_cast_out | runtime_ms |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | v1 pipeline (no v2 features) | 243 | 18.7750 | 0.8896 | 9.5014 | 1.6850 | 0.4051 | 0.4258 | 1.3095 | 1.8484 | 0.0187 | 228.0575 |
| v2_airlight | + connected/low-gradient airlight | 243 | 18.8786 | 0.8895 | 9.4457 | 1.7225 | 0.4045 | 0.4361 | 1.3232 | 1.8583 | 0.0181 | 240.7161 |
| v2_airlight_sky | + sky / white-object handling | 243 | 19.4101 | 0.8933 | 8.9904 | 1.8043 | 0.4067 | 0.4167 | 1.3577 | 1.8507 | 0.0173 | 268.6254 |
| v2_local_omega | + local omega/t0 maps | 243 | 18.5439 | 0.8815 | 9.6375 | 1.8966 | 0.4061 | 0.4095 | 1.3265 | 1.8601 | 0.0179 | 666.2347 |
| v2_local_enhance | + spatially blended enhancement | 243 | 18.4503 | 0.8873 | 9.3814 | 1.7943 | 0.4007 | 0.3202 | 1.3307 | 1.5837 | 0.0244 | 679.6421 |
| v2_full | full v2 (frozen tuned config) | 243 | 18.4503 | 0.8873 | 9.3814 | 1.7943 | 0.4007 | 0.3202 | 1.3307 | 1.5837 | 0.0244 | 678.1471 |
