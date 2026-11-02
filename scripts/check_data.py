"""Read-only dataset check: do the paths in ``data/splits.json`` resolve?

Reports, per split, how many records resolve to real files and lists the ones
that do not.  Nothing is written, renamed or downloaded.

On a case-insensitive filesystem (Windows) ``data/RTTS`` and ``data/rtts`` are
the same folder.  On Linux paths are case-sensitive, so a mismatch is reported
here as a hint instead of being silently fixed.

Usage:
    python scripts/check_data.py            # summary + missing entries
    python scripts/check_data.py --all      # list every missing path
    python scripts/check_data.py --quiet    # only the summary table

Exit code is 0 when every referenced file exists, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED = {
    "calib": 299,
    "test_sots": 243,
    "test_rtts": 72,
    "selector_train": 180,
    "density_validation": 64,
}
PATH_KEYS = ("hazy", "clear", "depth")


def _path_str(value: str) -> str:
    return value.replace("\\", "/")


def case_hint(path: Path) -> str | None:
    """Return the on-disk spelling if only the letter case differs, else None."""
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
    except (ValueError, OSError):
        return None
    current = ROOT
    actual: list[str] = []
    for part in relative.parts:
        if not current.is_dir():
            return None
        exact = current / part
        if exact.exists():
            current = exact
            actual.append(part)
            continue
        matches = sorted(p for p in current.iterdir() if p.name.lower() == part.lower())
        if not matches:
            return None
        current = matches[0]
        actual.append(matches[0].name)
    return "/".join(actual)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify that dataset files referenced by splits.json exist")
    parser.add_argument("--all", action="store_true", help="list every missing path, not just the first few")
    parser.add_argument("--quiet", action="store_true", help="only print the per-split summary")
    args = parser.parse_args()

    splits_path = ROOT / "data" / "splits.json"
    if not splits_path.exists():
        print(f"[check] missing {splits_path} -> run: python scripts/prepare_data.py")
        return 1
    payload = json.loads(splits_path.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    sources = payload.get("sources", {})
    print(f"[check] {len(records)} records; sources={sources}")

    stats: dict[str, dict[str, int]] = {}
    missing: dict[str, list[str]] = {}
    for rec in records:
        split = str(rec.get("split", "unknown"))
        stat = stats.setdefault(split, {"records": 0, "files": 0, "ok": 0, "missing": 0})
        stat["records"] += 1
        record_ok = True
        for key in PATH_KEYS:
            value = rec.get(key)
            if not value:
                continue
            stat["files"] += 1
            path = ROOT / _path_str(value)
            if path.exists():
                continue
            record_ok = False
            stat["missing"] += 1
            hint = case_hint(path)
            note = f"  (case mismatch, on disk: {hint})" if hint else ""
            missing.setdefault(split, []).append(f"{rec.get('id', '?')}.{key}: {value}{note}")
        if record_ok:
            stat["ok"] += 1

    print()
    header = f"{'split':<20} {'records':>8} {'files':>7} {'resolve':>8} {'missing':>8} {'expected':>9}"
    print(header)
    print("-" * len(header))
    ok_all = True
    for split in sorted(stats):
        stat = stats[split]
        expected = EXPECTED.get(split, "-")
        if stat["missing"]:
            ok_all = False
        print(f"{split:<20} {stat['records']:>8} {stat['files']:>7} "
              f"{stat['ok']:>8} {stat['missing']:>8} {str(expected):>9}")

    for split, expected in EXPECTED.items():
        actual = stats.get(split, {}).get("records", 0)
        if actual != expected:
            print(f"[check] note: {split} has {actual} records, expected {expected} "
                  f"(splits.json may have been rebuilt)")
    total_missing = sum(len(v) for v in missing.values())
    print(f"\n[check] total missing paths: {total_missing}")
    if total_missing and not args.quiet:
        for split in sorted(missing):
            entries = missing[split]
            shown = entries if args.all else entries[:5]
            print(f"\n[{split}] {len(entries)} missing")
            for line in shown:
                print(f"  - {line}")
            if len(entries) > len(shown):
                print(f"  ... {len(entries) - len(shown)} more (use --all)")
    if ok_all:
        print("[check] all referenced files are present")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
