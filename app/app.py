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
from src.config import load_json, load_params, resolve_path  # noqa: E402
from src.density import DensityEstimator  # noqa: E402
from src.io_utils import read_rgb, to_uint8, write_rgb  # noqa: E402
from src.metrics import no_reference_metrics  # noqa: E402
from src.pipeline import dehaze_adaptive  # noqa: E402
from src.preprocess import preprocess_array  # noqa: E402

st.set_page_config(page_title="Adaptive Fog-Density-Aware Dehazing",
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
    st.title("🌫️ Adaptive Fog-Density-Aware Dehazing")
    st.caption("Density estimation → adaptive strategy → DCP + guided filter → "
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
        show_maps = st.checkbox("Show transmission map", value=True)
        run = st.button("Dehaze", type="primary", use_container_width=True)

    source = None
    if uploaded is not None:
        source = uploaded
    elif sample_name != "(none)":
        source = samples[sample_name]

    if source is None:
        st.info("Upload an image or pick a sample from the sidebar.")
        st.stop()

    try:
        if hasattr(source, "read"):
            img = np.array(Image.open(source).convert("RGB")).astype(np.float32) / 255.0
        else:
            img = read_rgb(source)
    except Exception as exc:
        st.error(f"Could not read image: {exc}")
        st.stop()

    hazy = preprocess_array(img, params)
    if not run and "last_result" in st.session_state and st.session_state.get("last_source") == str(source):
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
        result = {"baseline": baseline, "adaptive": adaptive, "info": info}
        st.session_state["last_result"] = result
        st.session_state["last_source"] = str(source)

    info = result["info"]
    baseline = result["baseline"]
    adaptive = result["adaptive"]

    score = float(info["score"])
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Fog-density score", f"{score:.3f}")
    col2.metric("Selected class", CLASS_BADGE.get(info["class"], info["class"]))
    col3.metric("Omega / t0", f"{info['params']['omega']:.2f} / {info['params']['t0']:.2f}")
    col4.metric("Runtime", f"{info['timing_ms']['total']:.0f} ms")

    st.progress(min(max(score, 0.0), 1.0), text="0 = clear · 1 = dense fog")

    tab1, tab2, tab3 = st.tabs(["Comparison", "Transmission & parameters", "Metrics"])
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.image(_to_display(hazy), caption="Input (preprocessed)", use_container_width=True)
        c2.image(_to_display(baseline), caption="Baseline: fixed DCP", use_container_width=True)
        c3.image(_to_display(adaptive), caption="Adaptive (this work)", use_container_width=True)
        st.download_button("Download adaptive result", _download_bytes(adaptive),
                           file_name="dehazed_adaptive.png", mime="image/png")

    with tab2:
        c1, c2 = st.columns(2)
        if show_maps:
            t = np.clip(info["transmission"], 0, 1)
            c1.image(t, caption=f"Transmission map (mean t = {info['mean_transmission']:.2f})",
                     clamp=True, use_container_width=True)
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
        c2.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
        st.json({"density features": info["features"],
                 "normalised": info["normalised"],
                 "timing_ms": info["timing_ms"]})

    with tab3:
        m_base = no_reference_metrics(hazy, baseline)
        m_adap = no_reference_metrics(hazy, adaptive)
        table = pd.DataFrame([
            {"metric": "Entropy (out)", "baseline": m_base["entropy_out"], "adaptive": m_adap["entropy_out"]},
            {"metric": "Entropy gain", "baseline": m_base["entropy_gain"], "adaptive": m_adap["entropy_gain"]},
            {"metric": "Contrast improvement", "baseline": m_base["contrast_improvement"], "adaptive": m_adap["contrast_improvement"]},
            {"metric": "Edge preservation", "baseline": m_base["edge_preservation"], "adaptive": m_adap["edge_preservation"]},
            {"metric": "Color cast (lower better)", "baseline": m_base["color_cast_out"], "adaptive": m_adap["color_cast_out"]},
        ])
        st.dataframe(table.style.format({"baseline": "{:.4f}", "adaptive": "{:.4f}"}),
                     hide_index=True, use_container_width=True)
        st.caption("No-reference metrics are shown because an uploaded image has no ground truth.")


if __name__ == "__main__":
    main()
