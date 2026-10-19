"""Configuration helpers.

Every tunable lives in ``config/params.yaml``.  Values fitted on the calibration
split live in JSON files so that the YAML stays readable and hand-editable.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARAMS = ROOT / "config" / "params.yaml"

_cache: dict[str, Any] = {}


def load_params(path: str | Path | None = None, reload: bool = False) -> dict:
    """Load params.yaml (cached).  Returns a deep copy so callers can mutate."""
    key = str(path or DEFAULT_PARAMS)
    if reload or key not in _cache:
        with open(key, "r", encoding="utf-8") as fh:
            _cache[key] = yaml.safe_load(fh)
    return copy.deepcopy(_cache[key])


def resolve_path(path: str | Path) -> Path:
    """Resolve a project-relative path against the repository root."""
    p = Path(path)
    return p if p.is_absolute() else (ROOT / p)


def get(cfg: dict, dotted: str, default: Any = None) -> Any:
    """Read ``a.b.c`` from a nested dict."""
    node: Any = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def deep_update(base: dict, extra: dict) -> dict:
    """Recursively merge ``extra`` into ``base`` (returns base)."""
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            deep_update(base[key], value)
        else:
            base[key] = copy.deepcopy(value)
    return base


def load_json(path: str | Path, default: Any = None) -> Any:
    p = resolve_path(path)
    if not p.exists():
        return default
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_json(path: str | Path, data: Any) -> Path:
    p = resolve_path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=False)
        fh.write("\n")
    return p
