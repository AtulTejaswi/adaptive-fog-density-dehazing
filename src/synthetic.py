"""Synthetic haze generation with the atmospheric scattering model.

Used for (a) the beta -> density monotonicity validation, (b) the no-reference
RTTS-style fallback set, and (c) a fully reproducible dataset if RESIDE/SOTS
cannot be downloaded.  Ground-truth clear images and depth maps are retained
for the synthetic pairs.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from scipy.ndimage import gaussian_filter

from .io_utils import save_depth, write_rgb


def beta_to_class(beta: float, ranges: dict | None = None) -> str:
    ranges = ranges or {"light": [0.15, 0.55], "moderate": [0.55, 1.10], "heavy": [1.10, 2.10]}
    if beta < ranges["moderate"][0]:
        return "light"
    if beta < ranges["heavy"][0]:
        return "moderate"
    return "heavy"


def sample_beta(rng: np.random.Generator, ranges: dict) -> tuple[float, str]:
    # equal probability per class, log-uniform inside the class range
    label = str(rng.choice(["light", "moderate", "heavy"]))
    lo, hi = ranges[label]
    beta = float(np.exp(rng.uniform(math.log(lo), math.log(hi))))
    return beta, label


def load_base_images(kind: str = "skimage") -> list[np.ndarray]:
    """A small, license-friendly pool of clear images."""
    if kind != "skimage":
        raise ValueError(f"Unknown base image source: {kind}")
    from skimage import data

    loaders = [data.astronaut, data.chelsea, data.coffee, data.rocket,
               data.cat, data.retina, data.hubble_deep_field, data.skin]
    images = []
    for loader in loaders:
        try:
            img = loader()
        except Exception:
            continue
        if img.ndim == 2:
            img = np.stack([img] * 3, axis=-1)
        if img.dtype != np.uint8:
            img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
        images.append(cv2.cvtColor(img[..., :3], cv2.COLOR_RGB2BGR)[..., ::-1].copy())
    if not images:
        raise RuntimeError("No base images available from scikit-image")
    return images


def random_scene(
    base: np.ndarray,
    rng: np.random.Generator,
    size: tuple[int, int] = (384, 512),
) -> np.ndarray:
    """Random crop / resize / flip / colour-jitter a base image."""
    h, w = size
    bh, bw = base.shape[:2]
    aspect = w / h
    if bw / bh > aspect:
        crop_h = bh
        crop_w = int(round(bh * aspect))
    else:
        crop_w = bw
        crop_h = int(round(bw / aspect))
    # random zoom out of the largest possible crop
    scale = rng.uniform(0.55, 0.95)
    ch = max(32, int(crop_h * scale))
    cw = max(32, int(crop_w * scale))
    y0 = int(rng.integers(0, max(1, bh - ch + 1)))
    x0 = int(rng.integers(0, max(1, bw - cw + 1)))
    patch = base[y0:y0 + ch, x0:x0 + cw]
    interp = cv2.INTER_AREA if (ch > h or cw > w) else cv2.INTER_CUBIC
    scene = cv2.resize(patch, (w, h), interpolation=interp)

    if rng.random() < 0.5:
        scene = scene[:, ::-1]
    if rng.random() < 0.5:
        scene = scene[::-1]
    scene = scene.astype(np.float32) / 255.0
    # gentle contrast / brightness / channel jitter so scenes are not clones
    contrast = rng.uniform(0.9, 1.1)
    brightness = rng.uniform(-0.04, 0.04)
    scene = np.clip((scene - 0.5) * contrast + 0.5 + brightness, 0.0, 1.0)
    channel_gain = rng.uniform(0.97, 1.03, size=3).astype(np.float32)
    scene = np.clip(scene * channel_gain, 0.0, 1.0)
    return scene.astype(np.float32)


def make_depth(rng: np.random.Generator, h: int, w: int,
               smoothness: float = 12.0) -> np.ndarray:
    """Smooth pseudo-depth in [0.15, 1.4]; farther at the top of the image."""
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    vertical = yy ** 1.15
    noise = gaussian_filter(rng.normal(size=(h, w)).astype(np.float32),
                            sigma=max(h, w) / float(smoothness))
    noise = noise - noise.min()
    noise = noise / (noise.max() + 1e-6)
    depth = 0.25 + 0.85 * vertical + 0.40 * noise
    depth = depth - depth.min()
    depth = depth / (depth.max() + 1e-6)
    return (0.15 + 1.25 * depth).astype(np.float32)


def apply_haze(
    clear: np.ndarray,
    depth: np.ndarray,
    beta: float,
    airlight: np.ndarray | float,
    noise_sigma: float = 0.004,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """I = J*t + A*(1-t), t = exp(-beta*d).  Returns hazy image and t."""
    a = np.asarray(airlight, dtype=np.float32).reshape(1, 1, -1)
    if a.size == 1:
        a = np.repeat(a, 3, axis=2)
    t = np.exp(-float(beta) * depth).astype(np.float32)
    hazy = clear * t[..., None] + a * (1.0 - t[..., None])
    if noise_sigma > 0:
        rng = rng or np.random.default_rng(0)
        hazy = hazy + rng.normal(0.0, float(noise_sigma), size=hazy.shape).astype(np.float32)
    return np.clip(hazy, 0.0, 1.0).astype(np.float32), t


def generate_split(
    out_root: str | Path,
    split: str,
    n_images: int,
    rng: np.random.Generator,
    config: dict,
    base_images: list[np.ndarray] | None = None,
    start_index: int = 0,
    save_clear: bool = True,
    save_depth_map: bool = True,
    source: str = "synthetic",
    fixed_beta: float | None = None,
) -> list[dict]:
    """Generate a synthetic hazy split and return split records."""
    out_root = Path(out_root)
    size = tuple(config.get("image_size", [384, 512]))
    ranges = config.get("beta_ranges", {})
    a_lo, a_hi = config.get("atmospheric_light", [0.82, 0.95])
    noise = float(config.get("noise_sigma", 0.004))
    base_images = base_images or load_base_images("skimage")
    records: list[dict] = []

    hazy_dir = out_root / split / "hazy"
    clear_dir = out_root / split / "clear"
    depth_dir = out_root / split / "depth"

    for i in range(int(n_images)):
        idx = start_index + i
        base = base_images[idx % len(base_images)]
        clear = random_scene(base, rng, size)
        depth = make_depth(rng, clear.shape[0], clear.shape[1])
        if fixed_beta is None:
            beta, label = sample_beta(rng, ranges)
        else:
            beta = float(fixed_beta)
            label = beta_to_class(beta, ranges)
        airlight = rng.uniform(a_lo, a_hi, size=3).astype(np.float32)
        hazy, _ = apply_haze(clear, depth, beta, airlight, noise_sigma=noise, rng=rng)

        name = f"{split}_{idx:05d}"
        rec = {
            "id": name,
            "split": split,
            "source": source,
            "has_gt": bool(save_clear),
            "beta": float(beta),
            "class": label,
            "group": "synthetic",
            "hazy": str((hazy_dir / f"{name}.png").as_posix()),
        }
        write_rgb(hazy_dir / f"{name}.png", hazy)
        if save_clear:
            write_rgb(clear_dir / f"{name}.png", clear)
            rec["clear"] = str((clear_dir / f"{name}.png").as_posix())
        if save_depth_map:
            save_depth(depth_dir / f"{name}.npy", depth)
            rec["depth"] = str((depth_dir / f"{name}.npy").as_posix())
        records.append(rec)
    return records


def generate_beta_sweep(
    out_root: str | Path,
    clear_images: list[np.ndarray],
    betas: list[float],
    rng: np.random.Generator,
    config: dict,
    source: str = "sots",
) -> list[dict]:
    """One clear scene per beta, for score-vs-beta monotonicity validation."""
    out_root = Path(out_root)
    ranges = config.get("beta_ranges", {})
    a_lo, a_hi = config.get("atmospheric_light", [0.82, 0.95])
    noise = float(config.get("noise_sigma", 0.004))
    records: list[dict] = []
    for scene_idx, clear in enumerate(clear_images):
        depth = make_depth(rng, clear.shape[0], clear.shape[1])
        airlight = rng.uniform(a_lo, a_hi, size=3).astype(np.float32)
        for beta in betas:
            beta = float(beta)
            hazy, _ = apply_haze(clear, depth, beta, airlight, noise_sigma=noise, rng=rng)
            name = f"beta_{scene_idx:03d}_{beta:.3f}".replace(".", "p")
            hazy_path = out_root / "density_validation" / "hazy" / f"{name}.png"
            write_rgb(hazy_path, hazy)
            records.append({
                "id": name,
                "split": "density_validation",
                "source": source,
                "has_gt": True,
                "beta": beta,
                "class": beta_to_class(beta, ranges),
                "group": f"scene_{scene_idx:03d}",
                "scene": scene_idx,
                "hazy": hazy_path.as_posix(),
            })
    return records
