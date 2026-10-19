"""Leakage / provenance checks for the frozen splits and parameters.

These tests are skipped when ``data/splits.json`` is absent (e.g. a fresh clone
that has not downloaded data yet).  They guard the project's core reproducibility
rule: nothing derived from the test splits may enter the tuning pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _splits() -> dict:
    path = ROOT / "data" / "splits.json"
    if not path.exists():
        pytest.skip("data/splits.json not built; run scripts/prepare_data.py")
    return json.loads(path.read_text(encoding="utf-8"))


def _scene(rec: dict) -> tuple[str, str]:
    return (str(rec.get("group", "")), Path(str(rec.get("clear", rec["hazy"]))).stem)


def test_calib_and_test_scenes_are_disjoint() -> None:
    records = _splits()["records"]
    calib = {_scene(r) for r in records if r["split"] == "calib" and r.get("clear")}
    test = {_scene(r) for r in records if r["split"] == "test_sots" and r.get("clear")}
    assert calib, "no calib scenes found"
    assert test, "no SOTS test scenes found"
    assert calib.isdisjoint(test), f"scene leaks between calib and test: {calib & test}"


def test_split_counts_match_records() -> None:
    payload = _splits()
    records = payload["records"]
    actual: dict[str, int] = {}
    for rec in records:
        actual[rec["split"]] = actual.get(rec["split"], 0) + 1
    assert actual == payload["counts"], (actual, payload["counts"])


def test_rtts_has_no_ground_truth() -> None:
    records = _splits()["records"]
    rtts = [r for r in records if r["split"] == "test_rtts"]
    assert rtts, "no RTTS records found"
    assert all(not r.get("has_gt") for r in rtts)
    assert all(not r.get("clear") for r in rtts)
    # real RTTS is the default source when data/RTTS is populated
    sources = {r.get("source") for r in rtts}
    assert sources <= {"rtts", "synthetic_rtts"}, sources


def test_tuned_params_declare_calib_only() -> None:
    path = ROOT / "config" / "tuned_params.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data.get("tuned_on") == "calib"
    assert data.get("objective"), "tuning objective must be recorded"
