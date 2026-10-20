"""Streamlit demo: upload an image, see fog-density score, selected class,
parameters, and baseline vs adaptive dehazing side by side.

Run from the repository root:
    streamlit run app/app.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.baseline import dehaze_baseline  # noqa: E402
from src.config import load_json, load_params, load_v2_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb, to_uint8, write_rgb  # noqa: E402
from src.metrics import no_reference_metrics  # noqa: E402
from src.pipeline import dehaze_adaptive, dehaze_adaptive_v2  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

st.set_page_config(page_title="FogSense — Adaptive Haze Removal",
                   page_icon="🌫️", layout="wide")

CLASS_BADGE = {"light": "🟢 light", "moderate": "🟡 moderate", "heavy": "🔴 heavy"}


@st.cache_data(show_spinner=False)
def _load_config():
    return load_params()


@st.cache_data(show_spinner=False)
def _sample_options():
    splits = load_json("data/splits.json", default={}) or {}
    options = {}
    for rec in splits.get("records", []):
        if rec["split"] in {"test_rtts", "test_sots"} and rec.get("hazy"):
            path = resolve_path(rec["hazy"])
            if path.exists():
                options[f"{rec['split']} / {rec['id']}"] = str(path)
    return options


def _to_display(img: np.ndarray) -> Image.Image:
    return Image.fromarray(to_uint8(img))


def _download_bytes(img: np.ndarray) -> bytes:
    buffer = io.BytesIO()
    _to_display(img).save(buffer, format="PNG")
    return buffer.getvalue()


def main() -> None:
    params = _load_config()
    st.title("🌫️ FogSense — Adaptive Haze Removal")
    st.caption("FogSense: density estimation → adaptive strategy → DCP + guided filter → "
               "Retinex / CLAHE / gray-world. Classical methods only.")

    with st.sidebar:
        st.header("Input")
        uploaded = st.file_uploader("Upload a hazy image", type=["png", "jpg", "jpeg", "bmp", "webp"])
        samples = _sample_options()
        sample_name = st.selectbox("…or try a sample", ["(none)"] + list(samples.keys()))
        st.header("Selector")
        mode = st.selectbox("Mode", ["three_bin", "continuous", "classifier"], index=0,
                            help="three_bin is the main method; the others are ablation variants.")
        force = st.selectbox("Force class (debug)", ["auto", "light", "moderate", "heavy"])
        st.header("Enhancement overrides")
        use_clahe = st.checkbox("CLAHE", value=True)
        use_retinex = st.checkbox("Retinex", value=True)
        use_gray = st.checkbox("Gray-world", value=True)
        st.header("v2 upgrades (opt-in)")
        use_v2 = st.checkbox("Enable v2 pipeline", value=False)
        use_airlight_v2 = st.checkbox("v2 airlight (connected + low-gradient)",
                                      value=True, disabled=not use_v2)
        use_sky = st.checkbox("Sky / white-object handling", value=True, disabled=not use_v2)
        use_local = st.checkbox("Local density maps", value=True, disabled=not use_v2)
        use_local_enh = st.checkbox("Spatially blended enhancement",
                                    value=True, disabled=not use_v2)
        st.caption("v2 knobs are fitted on the calib split only. With v2 off the "
                   "pipeline is byte-identical to v1.0.")
        show_maps = st.checkbox("Show transmission map", value=True)
        run = st.button("Dehaze", type="primary", width="stretch")

    source = None
    if uploaded is not None:
        source = uploaded
    elif sample_name != "(none)":
        source = samples[sample_name]

    if source is None:
        st.info("Upload an image or pick a sample from the sidebar.")
        st.stop()

    try:
        if hasattr(source, "getvalue"):
            img = np.array(Image.open(io.BytesIO(source.getvalue())).convert("RGB")).astype(np.float32) / 255.0
        elif hasattr(source, "read"):
            source.seek(0)
            img = np.array(Image.open(source).convert("RGB")).astype(np.float32) / 255.0
        else:
            img = read_rgb(source)
    except Exception as exc:
        st.error(f"Could not read image: {exc}")
        st.stop()

    hazy = preprocess_array(img, params)
    settings_key = (str(source), mode, force, bool(use_clahe), bool(use_retinex),
                    bool(use_gray), bool(use_v2), bool(use_airlight_v2), bool(use_sky),
                    bool(use_local), bool(use_local_enh))
    if not run and st.session_state.get("last_key") == settings_key:
        result = st.session_state["last_result"]
    else:
        with st.spinner("Estimating fog density and dehazing…"):
            baseline, _ = dehaze_baseline(hazy, params)
            adaptive, info = dehaze_adaptive(
                hazy, params, mode=mode,
                force_class=None if force == "auto" else force,
                enhancement_switches={
                    "clahe": bool(use_clahe),
                    "retinex": bool(use_retinex),
                    "gray_world": bool(use_gray),
                },
            )
            v2_out, v2_info = None, None
            if use_v2:
                tuned = load_v2_params(params)
                v2_cfg = tuned.get("v2", {})
                v2_cfg["enabled"] = True
                v2_cfg.setdefault("airlight", {})["method"] = "v2" if use_airlight_v2 else "v1"
                v2_cfg.setdefault("sky", {})["enabled"] = bool(use_sky)
                v2_cfg.setdefault("local_density", {})["enabled"] = bool(use_local)
                v2_cfg.setdefault("enhance", {})["local_blend"] = bool(use_local and use_local_enh)
                v2_cfg.setdefault("retinex", {})["fast"] = False
                v2_out, v2_info = dehaze_adaptive_v2(hazy, params, v2=v2_cfg)
        result = {"baseline": baseline, "adaptive": adaptive, "info": info,
                  "v2": v2_out, "v2_info": v2_info}
        st.session_state["last_result"] = result
        st.session_state["last_key"] = settings_key

    info = result["info"]
    baseline = result["baseline"]
    adaptive = result["adaptive"]
    v2_out = result.get("v2")
    v2_info = result.get("v2_info")

    score = float(info["score"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fog-density score", f"{score:.3f}")
    col2.metric("Selected class", CLASS_BADGE.get(info["class"], info["class"]))
    col3.metric("Omega / t0", f"{info['params']['omega']:.2f} / {info['params']['t0']:.2f}")
    col4.metric("Runtime", f"{info['timing_ms']['total']:.0f} ms")
    if v2_info is not None:
        st.caption(f"v2: {v2_info['timing_ms']['total']:.0f} ms "
                   f"(local density {v2_info['timing_ms']['local_density']:.0f} ms)")

    st.progress(min(max(score, 0.0), 1.0), text="0 = clear · 1 = dense fog")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Comparison", "Transmission & parameters", "v2 maps", "Metrics"])
    with tab1:
        if v2_out is not None:
            c1, c2, c3, c4 = st.columns(4)
            c1.image(_to_display(hazy), caption="Input (preprocessed)", width="stretch")
            c2.image(_to_display(baseline), caption="Baseline: fixed DCP", width="stretch")
            c3.image(_to_display(adaptive), caption="v1 adaptive (default)", width="stretch")
            c4.image(_to_display(v2_out), caption="v2 adaptive (opt-in)", width="stretch")
            d1, d2 = st.columns(2)
            d1.download_button("Download v1 result", _download_bytes(adaptive),
                               file_name="dehazed_v1.png", mime="image/png")
            d2.download_button("Download v2 result", _download_bytes(v2_out),
                               file_name="dehazed_v2.png", mime="image/png")
        else:
            c1, c2, c3 = st.columns(3)
            c1.image(_to_display(hazy), caption="Input (preprocessed)", width="stretch")
            c2.image(_to_display(baseline), caption="Baseline: fixed DCP", width="stretch")
            c3.image(_to_display(adaptive), caption="Adaptive (this work)", width="stretch")
            st.download_button("Download adaptive result", _download_bytes(adaptive),
                               file_name="dehazed_adaptive.png", mime="image/png")

    with tab2:
        c1, c2 = st.columns(2)
        if show_maps:
            t = np.clip(info["transmission"], 0, 1)
            c1.image(t, caption=f"Transmission map (mean t = {info['mean_transmission']:.2f})",
                     clamp=True, width="stretch")
        rows = [
            {"parameter": "class", "value": info["class"]},
            {"parameter": "omega", "value": f"{info['params']['omega']:.3f}"},
            {"parameter": "t0", "value": f"{info['params']['t0']:.3f}"},
            {"parameter": "patch size", "value": info["params"]["patch_size"]},
            {"parameter": "guided filter radius", "value": info["params"]["guided_filter"]["radius"]},
            {"parameter": "guided filter eps", "value": f"{info['params']['guided_filter']['eps']:.1e}"},
            {"parameter": "CLAHE clip", "value": info["params"]["clahe"].get("clip_limit")},
            {"parameter": "Retinex strength", "value": info["params"]["retinex"].get("strength")},
            {"parameter": "gray-world strength", "value": info["params"]["gray_world"].get("strength")},
            {"parameter": "atmospheric light A", "value": ", ".join(f"{v:.3f}" for v in info["airlight"])},
        ]
        rows = [{"parameter": r["parameter"], "value": str(r["value"])} for r in rows]
        c2.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        st.json({"density features": info["features"],
                 "normalised": info["normalised"],
                 "timing_ms": info["timing_ms"]})
        if v2_info is not None:
            st.subheader("v2 parameters (mean over the image)")
            v2_rows = [
                {"parameter": "v2 airlight", "value": str(v2_info.get("airlight_method"))},
                {"parameter": "v2 mean omega", "value": f"{v2_info['params']['omega']:.3f}"},
                {"parameter": "v2 mean t0", "value": f"{v2_info['params']['t0']:.3f}"},
                {"parameter": "sky pixels", "value": str(int(v2_info["sky_mask"].sum()))
                 if v2_info.get("sky_mask") is not None else "0"},
                {"parameter": "local density", "value": str(bool(v2_info["v2"]["local_density"]))},
                {"parameter": "local enhancement", "value": str(bool(v2_info["v2"]["local_enhance"]))},
            ]
            st.dataframe(pd.DataFrame(v2_rows), hide_index=True, width="stretch")

    with tab3:
        if v2_info is None:
            st.info("Enable the v2 pipeline in the sidebar to see local-density maps.")
        else:
            c1, c2, c3 = st.columns(3)
            score_map = v2_info.get("score_map")
            omega_map = v2_info.get("omega_map")
            sky = v2_info.get("sky_mask")
            if score_map is not None:
                c1.image(np.clip(score_map, 0, 1), caption="Local density score",
                         clamp=True, width="stretch")
            if omega_map is not None:
                c2.image(np.clip(omega_map, 0, 1), caption="omega(x)",
                         clamp=True, width="stretch")
            if sky is not None:
                overlay = np.clip(hazy, 0, 1).copy()
                if sky.any():
                    overlay[sky] = 0.5 * overlay[sky] + 0.5 * np.array([0.1, 0.8, 0.2],
                                                                       dtype=np.float32)
                c3.image(overlay, caption=f"Sky mask ({int(sky.sum())} px)",
                         clamp=True, width="stretch")
            st.json({"v2 flags": v2_info.get("v2"),
                     "timing_ms": v2_info.get("timing_ms")})

    with tab4:
        m_base = no_reference_metrics(hazy, baseline)
        m_adap = no_reference_metrics(hazy, adaptive)
        rows = {
            "metric": ["Entropy (out)", "Entropy gain", "Contrast improvement",
                       "Edge preservation", "Color cast (lower better)"],
            "baseline": [m_base["entropy_out"], m_base["entropy_gain"],
                         m_base["contrast_improvement"], m_base["edge_preservation"],
                         m_base["color_cast_out"]],
            "adaptive": [m_adap["entropy_out"], m_adap["entropy_gain"],
                         m_adap["contrast_improvement"], m_adap["edge_preservation"],
                         m_adap["color_cast_out"]],
        }
        if v2_out is not None:
            m_v2 = no_reference_metrics(hazy, v2_out)
            rows["v2"] = [m_v2["entropy_out"], m_v2["entropy_gain"],
                          m_v2["contrast_improvement"], m_v2["edge_preservation"],
                          m_v2["color_cast_out"]]
        table = pd.DataFrame(rows)
        st.dataframe(table.style.format({k: "{:.4f}" for k in ("baseline", "adaptive", "v2")
                                         if k in table.columns}),
                     hide_index=True, width="stretch")
        st.caption("No-reference metrics are shown because an uploaded image has no ground truth.")


if __name__ == "__main__":
    main()
