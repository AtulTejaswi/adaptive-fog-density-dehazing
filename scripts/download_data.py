"""Download / extract SOTS (RESIDE) and locate hazy-clear pairs.

If the automatic download is blocked, the script prints exact manual
instructions and exits with code 0 so the rest of the pipeline can fall back to
synthetic data.  See ``data/README.md`` for the expected layout.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import load_params, resolve_path  # noqa: E402


def download_file(url: str, dest: Path, timeout: int = 1800) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1_000_000:
        print(f"[download] already present: {dest} ({dest.stat().st_size / 1e6:.1f} MB)")
        return True
    print(f"[download] {url}\n           -> {dest}")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response, open(dest, "wb") as fh:
            shutil.copyfileobj(response, fh, length=1024 * 1024)
        print(f"[download] done: {dest.stat().st_size / 1e6:.1f} MB")
        return True
    except Exception as exc:  # network blocked, auth required, timeout...
        print(f"[download] FAILED: {exc}")
        if dest.exists() and dest.stat().st_size < 1_000_000:
            dest.unlink(missing_ok=True)
        return False


def extract_zip(zip_path: Path, dest: Path) -> bool:
    marker = dest / "SOTS"
    if marker.exists() and any(marker.rglob("*.png")):
        print(f"[extract] already extracted: {marker}")
        return True
    if not zip_path.exists():
        return False
    print(f"[extract] {zip_path} -> {dest} (this can take a minute)")
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(dest)
        print("[extract] done")
        return True
    except Exception as exc:
        print(f"[extract] FAILED: {exc}")
        return False


def _valid_image(path: Path) -> bool:
    img = cv2.imread(str(path), cv2.IMREAD_REDUCED_COLOR_4)
    return img is not None and img.size > 0


def find_sots_pairs(root: Path | None = None) -> list[dict]:
    """Return one hazy/clear pair per unique clear scene."""
    root = root or (ROOT / "data" / "SOTS")
    pairs: list[dict] = []
    if not root.exists():
        return pairs
    for group in ("indoor", "outdoor"):
        hazy_dir = root / group / "hazy"
        gt_dir = root / group / "gt"
        if not hazy_dir.exists() or not gt_dir.exists():
            continue
        by_stem: dict[str, list[Path]] = {}
        for hazy in sorted(hazy_dir.iterdir()):
            if hazy.suffix.lower() not in {".png", ".jpg", ".jpeg"}:
                continue
            stem = hazy.stem.split("_")[0]
            gt = gt_dir / f"{stem}.png"
            if not gt.exists():
                gt = gt_dir / f"{stem}.jpg"
            if not gt.exists():
                continue
            by_stem.setdefault(stem, []).append(hazy)
        rng = np.random.default_rng(42 + (0 if group == "indoor" else 1))
        for stem, candidates in sorted(by_stem.items()):
            hazy = candidates[int(rng.integers(0, len(candidates)))]
            gt = gt_dir / f"{stem}.png"
            if not gt.exists():
                gt = gt_dir / f"{stem}.jpg"
            if not _valid_image(hazy) or not _valid_image(gt):
                continue
            pairs.append({
                "id": f"sots_{group}_{stem}",
                "group": group,
                "source": "sots",
                "has_gt": True,
                "hazy": hazy.relative_to(ROOT).as_posix(),
                "clear": gt.relative_to(ROOT).as_posix(),
                "beta": None,
                "class": None,
                "scene": stem,
            })
    print(f"[pairs] found {len(pairs)} unique SOTS pairs")
    return pairs


def ensure_sots(params: dict, force: bool = False, download: bool = True) -> bool:
    data_cfg = params.get("data", {})
    zip_path = resolve_path(data_cfg.get("sots_zip", "data/downloads/SOTS.zip"))
    if force and zip_path.exists():
        zip_path.unlink()
    if download and not zip_path.exists():
        download_file(str(data_cfg.get("sots_url")), zip_path,
                      timeout=int(data_cfg.get("download_timeout", 1800)))
    if zip_path.exists():
        extract_zip(zip_path, ROOT / "data")
    pairs = find_sots_pairs()
    if pairs:
        return True
    print(MANUAL_INSTRUCTIONS)
    return False


MANUAL_INSTRUCTIONS = """
[manual] Could not obtain SOTS automatically.  Options:
  1) Download SOTS.zip manually (RESIDE SOTS indoor+outdoor) and put it at
     data/downloads/SOTS.zip, then re-run:  python scripts/prepare_data.py
  2) Expected extracted layout:
       data/SOTS/indoor/hazy/1400_1.png      data/SOTS/indoor/gt/1400.png
       data/SOTS/outdoor/hazy/0001_0.8_0.2.jpg data/SOTS/outdoor/gt/0001.png
  3) Or do nothing: prepare_data.py will build a fully synthetic dataset
     (same scattering model, several beta values) so every experiment still runs.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Download/extract SOTS (RESIDE)")
    parser.add_argument("--force", action="store_true", help="re-download the zip")
    parser.add_argument("--no-download", action="store_true", help="only inspect local files")
    args = parser.parse_args()
    params = load_params()
    ok = ensure_sots(params, force=args.force, download=not args.no_download)
    return 0 if ok else 0


if __name__ == "__main__":
    raise SystemExit(main())
