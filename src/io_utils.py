"""Small image and filesystem helpers.  Images are RGB float32 in [0, 1]."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def is_image(path: str | Path) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTENSIONS


def list_images(folder: str | Path) -> list[Path]:
    folder = Path(folder)
    if not folder.exists():
        return []
    return sorted(p for p in folder.rglob("*") if p.is_file() and is_image(p))


def read_rgb(path: str | Path) -> np.ndarray:
    """Read an image as RGB float32 in [0, 1]."""
    data = np.fromfile(str(path), dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(f"Cannot read image: {path}")
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0


def to_uint8(img: np.ndarray) -> np.ndarray:
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def write_rgb(path: str | Path, img: np.ndarray) -> Path:
    """Write an RGB float image (or uint8) to disk, creating parents."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    arr = to_uint8(img) if img.dtype != np.uint8 else img
    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    ok, buffer = cv2.imencode(path.suffix or ".png", bgr)
    if not ok:
        raise ValueError(f"Cannot encode image: {path}")
    buffer.tofile(str(path))
    return path


def read_depth(path: str | Path) -> np.ndarray:
    return np.load(str(path)).astype(np.float32)


def save_depth(path: str | Path, depth: np.ndarray) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(path), depth.astype(np.float32))
    return path


def image_id(path: str | Path) -> str:
    return Path(path).stem
