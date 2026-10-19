from __future__ import annotations

import numpy as np
import pytest

from src.synthetic import apply_haze, make_depth


@pytest.fixture(scope="session")
def rng() -> np.random.Generator:
    return np.random.default_rng(123)


@pytest.fixture(scope="session")
def sample_image() -> np.ndarray:
    h, w = 96, 128
    yy, xx = np.mgrid[0:h, 0:w]
    img = np.zeros((h, w, 3), dtype=np.float32)
    img[..., 0] = 0.25 + 0.6 * (xx / w)
    img[..., 1] = 0.20 + 0.5 * (yy / h)
    img[..., 2] = 0.15 + 0.4 * (1.0 - xx / w)
    # a few high-contrast objects so entropy/edges are non-trivial
    img[20:40, 20:45] = [0.9, 0.85, 0.2]
    img[55:80, 70:110] = [0.1, 0.7, 0.8]
    return np.clip(img, 0, 1).astype(np.float32)


@pytest.fixture(scope="session")
def hazy_pair(sample_image, rng):
    depth = make_depth(rng, sample_image.shape[0], sample_image.shape[1])
    hazy, t = apply_haze(sample_image, depth, beta=0.9, airlight=np.array([0.85, 0.88, 0.9]),
                         noise_sigma=0.0, rng=rng)
    return {"clear": sample_image, "hazy": hazy, "depth": depth, "t": t}
