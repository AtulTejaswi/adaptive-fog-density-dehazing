"""v2 must be strictly opt-in: flags off == v1.0, and scalar/array paths agree."""
from __future__ import annotations

import numpy as np

from src.config import load_params
from src.dcp import recover_radiance, transmission_map
from src.pipeline import dehaze_adaptive, dehaze_adaptive_v2


def _v1_params() -> dict:
    params = load_params()
    params["v2"]["enabled"] = False
    return params


def _v2_flags_off() -> dict:
    params = load_params()
    params["v2"]["enabled"] = True
    params["v2"]["airlight"]["method"] = "v1"
    params["v2"]["sky"]["enabled"] = False
    params["v2"]["local_density"]["enabled"] = False
    params["v2"]["enhance"]["local_blend"] = False
    params["v2"]["retinex"]["fast"] = False
    return params


def test_v2_flags_off_matches_v1_bit_exactly(hazy_pair):
    image = hazy_pair["hazy"]
    v1, info1 = dehaze_adaptive(image, _v1_params())
    v2, info2 = dehaze_adaptive(image, _v2_flags_off())
    assert np.array_equal(v1, v2)
    assert info1["class"] == info2["class"]
    assert info1["params"]["omega"] == info2["params"]["omega"]
    assert info1["params"]["t0"] == info2["params"]["t0"]


def test_explicit_v2_entry_with_flags_off_matches_v1(hazy_pair):
    image = hazy_pair["hazy"]
    v1, _ = dehaze_adaptive(image, _v1_params())
    v2, _ = dehaze_adaptive_v2(image, _v1_params())
    assert np.array_equal(v1, v2)


def test_array_omega_matches_scalar(hazy_pair):
    image = hazy_pair["hazy"]
    airlight = np.array([0.85, 0.88, 0.90], dtype=np.float32)
    scalar = transmission_map(image, airlight, omega=0.95, guided_radius=10, t_min=0.10)
    mapped = transmission_map(
        image, airlight,
        omega=np.full(image.shape[:2], 0.95, dtype=np.float32),
        guided_radius=10,
        t_min=np.full(image.shape[:2], 0.10, dtype=np.float32),
    )
    assert np.allclose(scalar, mapped, atol=1e-6)


def test_array_t0_matches_scalar(hazy_pair):
    image = hazy_pair["hazy"]
    airlight = np.array([0.85, 0.88, 0.90], dtype=np.float32)
    t = transmission_map(image, airlight, omega=0.95, guided_radius=10, t_min=0.10)
    scalar = recover_radiance(image, airlight, t, t0=0.10)
    mapped = recover_radiance(image, airlight, t,
                              t0=np.full(image.shape[:2], 0.10, dtype=np.float32))
    assert np.allclose(scalar, mapped, atol=1e-6)
