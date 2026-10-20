# FogSense — slides outline

**18 slides (v1: 15, v2: 3), ~12 minutes**

1. **Title** — FogSense: An Intelligent Multi-Algorithm Framework for Adaptive Haze Removal. IPA project.
2. **Problem** — haze scattering; fixed DCP over-corrects light haze, under-corrects dense haze. Before/after example.
3. **Atmospheric model** — `I = Jt + A(1-t)`, `t = exp(-beta d)`; what must be estimated.
4. **Pipeline overview** — preprocessing → density → selector → DCP + enhancement → evaluation.
5. **Density estimation** — dark-channel mean ↑, entropy ↓, contrast ↓; percentile normalisation; score ∈ [0,1].
6. **Validation** — score vs beta figure; Spearman overall and within-scene. Key: monotonic without labels.
7. **Adaptive selector** — tertiles; light/moderate/heavy parameter table; constrained tuning on calib.
8. **DCP + guided filter** — transmission, atmospheric light, radiance recovery; own guided filter (no contrib).
9. **Enhancement stack** — Retinex (illumination) → CLAHE (local contrast) → gray-world (colour cast); all toggleable for ablations.
10. **Experimental setup** — 299 calib / 243 SOTS test / 72 real RTTS no-reference; freeze before test; metrics and runtime.
11. **Results** — SOTS test: adaptive **18.78 dB / 0.8896** vs fixed DCP **15.71 dB / 0.8263**; +3.07 dB, +0.0633 SSIM; PSNR win rate 96.3% (p < 1e-30). Per-class bar chart: light +3.24 dB, moderate +4.11 dB, heavy +1.37 dB.
12. **Qualitative** — before/after by class and transmission maps; adaptive preserves light-haze detail and recovers dense-haze contrast.
13. **Ablations** — 10 variants. Component: no-enh 17.77/0.8726, CLAHE 18.18/0.8850, CLAHE+Retinex 19.30/0.8840, full 18.78/0.8896. Density: dark-only 18.48/0.8831, +entropy 18.84/0.8901. Selector: continuous 18.80/0.8574, classifier 18.40/0.8780; 3-bin wins on SSIM.
14. **Failure cases & limitations** — sky, white objects, night, noise amplification. Real 72-image RTTS (no ground truth): entropy gain +0.325, contrast +0.173, edge preservation +0.477 vs baseline; color cast reduced (0.026 -> 0.013); runtime ~3.7x baseline.
15. **Conclusion & demo** — explainable, CPU-friendly, reproducible; Streamlit demo; future work (sky-aware transmission, noise-aware t0, learned density regression).

## Speaker notes / demo cues

* Open the Streamlit app, upload a light-haze image: show score < t1, lower omega, CLAHE dominant.
* Upload a heavy-haze image: score > t2, higher omega, lower t0, Retinex off/weak.
* Toggle enhancements to reproduce ablation rows live.
* Point out the transmission map and the `mean t` value.
* Close with the honest failure grid: sky and white objects.

<!-- V2_SLIDES_START -->
## v2 upgrade (slides 16-18)

16. **What changed in v2 (opt-in).** v2 airlight (connected + low-gradient candidates), conservative sky mask (floor t, blend back), local density map with per-pixel omega(x)/t0(x), spatially blended enhancement. All flags off = v1 byte-identical.
17. **v2 results (SOTS 243).** v2 **18.45 dB / 0.8873** vs v1 **18.78 dB / 0.8896** (-0.32 dB, -0.0023 SSIM). Indoor +0.75 dB / +0.0118 SSIM; outdoor -0.43 dB / -0.0037 SSIM. Stronger CAP baseline: 18.09 dB / 0.7833; v2 vs CAP +0.36 dB PSNR / +0.1040 SSIM.
18. **Honest takeaway.** v2 improves CIEDE2000 (-0.120) and indoor scenes but not aggregate PSNR/SSIM; v1 stays the default. NIQE/FADE are style proxies. Runtime 562 ms vs 192 ms (v1) vs 59 ms (DCP).
<!-- V2_SLIDES_END -->
