"""Download a fixed real-world RTTS subset (RESIDE-beta) for the no-reference test.

The RTTS images used in this project are the 72 files listed in
``scripts/rtts_subset.txt``.  They come from the Hugging Face mirror
``fuhao7i/RTTS`` (Apache-2.0), which contains the RESIDE-beta RTTS images
(4322 real-world hazy photographs).  A fixed manifest keeps the subset and the
reported no-reference numbers exactly reproducible.

Usage:
    python scripts/download_rtts.py            # download into data/RTTS/
    python scripts/download_rtts.py --check    # only report what is missing

The images are gitignored; only this script and the manifest are committed.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPO = "fuhao7i/RTTS"
BASE_URL = f"https://huggingface.co/datasets/{REPO}/resolve/main"
MANIFEST = ROOT / "scripts" / "rtts_subset.txt"
DEST = ROOT / "data" / "RTTS"


def _read_manifest() -> list[str]:
    if not MANIFEST.exists():
        raise FileNotFoundError(f"missing manifest: {MANIFEST}")
    return [line.strip() for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def _download(url: str, dest: Path, timeout: int = 600) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1024:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as response, open(dest, "wb") as fh:
            shutil.copyfileobj(response, fh, length=1024 * 1024)
        return dest.stat().st_size > 1024
    except Exception as exc:  # network blocked, auth required, timeout...
        print(f"  [fail] {dest.name}: {exc}")
        dest.unlink(missing_ok=True)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Download the fixed RTTS subset")
    parser.add_argument("--check", action="store_true", help="report missing files only")
    parser.add_argument("--timeout", type=int, default=600)
    args = parser.parse_args()

    files = _read_manifest()
    missing = [f for f in files if not (DEST / Path(f).name).exists()]
    print(f"[rtts] manifest={len(files)} images; missing={len(missing)}")
    if args.check:
        for f in missing[:10]:
            print(f"  missing: {Path(f).name}")
        return 0

    ok = 0
    for idx, rel in enumerate(files, 1):
        dest = DEST / Path(rel).name
        if dest.exists():
            ok += 1
            continue
        url = f"{BASE_URL}/{urllib.parse.quote(rel)}"
        if _download(url, dest, timeout=args.timeout):
            ok += 1
        if idx % 12 == 0:
            print(f"  {idx}/{len(files)} done ({ok} present)")
        time.sleep(0.05)  # be polite to the hub

    print(f"[rtts] {ok}/{len(files)} images available in {DEST}")
    if ok < len(files):
        print("[rtts] some downloads failed; re-run the script or check the network.")
        return 1
    print("[rtts] done.  Next: python scripts/prepare_data.py --no-download")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
