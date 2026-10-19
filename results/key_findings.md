### Key findings

- **Density validation.** The score is monotone in beta: overall Spearman rho = 0.898; within-scene mean rho = 0.995 (minimum 0.976 across 8 scenes).

- **SOTS overall.** Adaptive PSNR 18.78 dB vs baseline 15.71 dB; SSIM 0.8896 vs 0.8263. Win rate (adaptive > baseline): PSNR 96.3%, SSIM 90.1%.

- **Per class.** light: delta PSNR +3.24 dB, delta SSIM +0.0665, SSIM win rate 90.6%; moderate: delta PSNR +4.11 dB, delta SSIM +0.0737, SSIM win rate 88.0%; heavy: delta PSNR +1.37 dB, delta SSIM +0.0446, SSIM win rate 92.4%.

- **No-reference RTTS-style set.** entropy_gain delta +0.2674; contrast_improvement delta +0.2306; edge_preservation delta +0.7337.

- **Runtime.** 258 ms/image (3.9 FPS) on CPU, including preprocessing.

- **Ablation.** Full pipeline SSIM 0.8896 vs no-enhancement 0.8726; dark-channel-only density features give SSIM 0.8831 vs full features 0.8896.
