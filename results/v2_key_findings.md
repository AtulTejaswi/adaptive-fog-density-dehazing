### v2 key findings

- **v2 is not an aggregate win over v1.** SOTS PSNR -0.32 dB (p = 0.0002), SSIM -0.0023 (p = 0.4416), CIEDE2000 -0.120 (lower better), NIQE +0.109 (lower better), FADE -0.0044 (lower better). v1 remains the default.

- **Indoor vs outdoor.** v2 helps indoor (+0.75 dB / +0.0118 SSIM, n = 22) and hurts outdoor (-0.43 dB / -0.0037 SSIM, n = 221).

- **Stronger baseline.** CAP reaches 18.09 dB / 0.7833; v2's advantage over CAP is +0.36 dB PSNR (p = 0.0926, not significant at 0.05) and +0.1040 SSIM.

- **RTTS.** v1 leads on entropy gain (0.4165 vs 0.3063) and edge preservation (1.6733 vs 1.4729); v2 has lower FADE (0.4586 vs 0.4677) but higher NIQE.

- **Density.** Local density is the best beta signal on the validation sweep (0.948 vs 0.907 global); on RTTS, global density and the calib-fitted ridge weights correlate better with FADE (0.933 and 0.969 vs 0.817). Ridge is an experiment, not the shipped estimator.

- **Runtime.** v2 562 ms vs v1 192 ms vs DCP 59 ms on SOTS; fast Retinex was rejected (quality drop on calib).
