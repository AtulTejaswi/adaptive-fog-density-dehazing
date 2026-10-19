import numpy as np

from src.dcp import atmospheric_light, dcp_dehaze, recover_radiance, transmission_map


def test_atmospheric_light_range(hazy_pair):
    a = atmospheric_light(hazy_pair["hazy"])
    assert a.shape == (3,)
    assert np.all(a >= 0.0) and np.all(a <= 1.0)


def test_transmission_range(hazy_pair):
    a = atmospheric_light(hazy_pair["hazy"])
    t = transmission_map(hazy_pair["hazy"], a, omega=0.95, patch_size=15,
                         guided_radius=10, guided_eps=1e-4, t_min=0.1)
    assert t.shape == hazy_pair["hazy"].shape[:2]
    assert t.min() >= 0.1 - 1e-6 and t.max() <= 1.0


def test_recover_radiance_range(hazy_pair):
    a = np.array([0.85, 0.88, 0.9], dtype=np.float32)
    out = recover_radiance(hazy_pair["hazy"], a, hazy_pair["t"], t0=0.1)
    assert out.shape == hazy_pair["hazy"].shape
    assert out.min() >= 0.0 and out.max() <= 1.0


def test_dcp_dehaze_info(hazy_pair):
    out, info = dcp_dehaze(hazy_pair["hazy"], omega=0.9, t0=0.1, patch_size=15,
                          guided_radius=8, guided_eps=1e-4)
    assert out.shape == hazy_pair["hazy"].shape
    assert out.dtype == np.float32
    assert 0.0 <= out.min() <= out.max() <= 1.0
    for key in ("airlight", "transmission", "mean_transmission", "min_transmission"):
        assert key in info
    assert info["transmission"].shape == out.shape[:2]


def test_dcp_increases_contrast(hazy_pair):
    from src.density import rms_contrast

    out, _ = dcp_dehaze(hazy_pair["hazy"], omega=0.95, t0=0.1, guided_radius=8)
    assert rms_contrast(out) > rms_contrast(hazy_pair["hazy"])
