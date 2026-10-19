# Slides outline — Adaptive Fog-Density-Aware Dehazing

**15 slides, ~10 minutes**

1. **Title** — Adaptive, Fog-Density-Aware Single-Image Dehazing. IPA project.
2. **Problem** — haze scattering; fixed DCP over-corrects light haze, under-corrects dense haze. Before/after example.
3. **Atmospheric model** — `I = Jt + A(1-t)`, `t = exp(-beta d)`; what must be estimated.
4. **Pipeline overview** — preprocessing → density → selector → DCP + enhancement → evaluation.
5. **Density estimation** — dark-channel mean ↑, entropy ↓, contrast ↓; percentile normalisation; score ∈ [0,1].
6. **Validation** — score vs beta figure; Spearman overall and within-scene. Key: monotonic without labels.
7. **Adaptive selector** — tertiles; light/moderate/heavy parameter table; constrained tuning on calib.
8. **DCP + guided filter** — transmission, atmospheric light, radiance recovery; own guided filter (no contrib).
9. **Enhancement stack** — Retinex (illumination) → CLAHE (local contrast) → gray-world (colour cast); all toggleable for ablations.
10. **Experimental setup** — 299 calib / 243 SOTS test / 48 no-reference; freeze before test; metrics and runtime.
11. **Results** — overall PSNR/SSIM table and per-class bar chart; paired win rate / Wilcoxon.
12. **Qualitative** — before/after by class and transmission maps; adaptive preserves light-haze detail and recovers dense-haze contrast.
13. **Ablations** — components, density features, selector variants. What each contributes.
14. **Failure cases & limitations** — sky, white objects, night, noise amplification; RTTS fallback is synthetic.
15. **Conclusion & demo** — explainable, CPU-friendly, reproducible; Streamlit demo; future work (sky-aware transmission, noise-aware t0, real RTTS).

## Speaker notes / demo cues

* Open the Streamlit app, upload a light-haze image: show score < t1, lower omega, CLAHE dominant.
* Upload a heavy-haze image: score > t2, higher omega, lower t0, Retinex off/weak.
* Toggle enhancements to reproduce ablation rows live.
* Point out the transmission map and the `mean t` value.
* Close with the honest failure grid: sky and white objects.
