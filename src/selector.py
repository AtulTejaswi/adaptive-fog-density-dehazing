"""Stage 3: adaptive strategy selection.

Primary method: rule-based three-bin selector using thresholds fitted as
tertiles of the calibration density-score distribution.  Two optional
ablations are provided: continuous parameter interpolation and a shallow
decision-tree classifier.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

from .config import deep_update, load_json, resolve_path

CLASSES = ("light", "moderate", "heavy")


def _interp(bounds, t: float) -> float:
    lo, hi = float(bounds[0]), float(bounds[1])
    return float(lo + np.clip(t, 0.0, 1.0) * (hi - lo))


class AdaptiveSelector:
    def __init__(self, params: dict, calibration: dict | None = None,
                 tuned: dict | None = None, mode: str | None = None):
        self.params = params
        paths = params.get("paths", {})
        self.calibration = calibration if calibration is not None else (
            load_json(paths.get("calibration", "config/calibration.json"), default={}) or {}
        )
        self.tuned = tuned if tuned is not None else (
            load_json(paths.get("tuned_params", "config/tuned_params.json"), default={}) or {}
        )
        sel = params.get("selector", {})
        thresholds = self.calibration.get("thresholds") or sel.get("thresholds", {})
        self.t1 = float(thresholds.get("t1", 0.33))
        self.t2 = float(thresholds.get("t2", 0.66))
        if self.t2 <= self.t1:
            self.t1, self.t2 = 0.33, 0.66
        self.mode = mode or sel.get("mode", "three_bin")
        self._classifier = None
        if self.mode == "classifier":
            self._classifier = self._load_classifier()

    # -- class / parameters -------------------------------------------------
    def classify(self, score: float, features: dict | None = None) -> str:
        if self.mode == "classifier" and self._classifier is not None and features is not None:
            vector = [[
                float(features.get("dark_channel", 0.5)),
                float(features.get("entropy", 0.5)),
                float(features.get("contrast", 0.5)),
            ]]
            return str(self._classifier.predict(vector)[0])
        if score < self.t1:
            return "light"
        if score < self.t2:
            return "moderate"
        return "heavy"

    def params_for_class(self, label: str) -> dict:
        base = copy.deepcopy(self.params.get("dehaze", {}).get("defaults", {}))
        class_cfg = self.params.get("dehaze", {}).get("classes", {}).get(label, {})
        deep_update(base, class_cfg)
        tuned_class = (self.tuned.get("classes") or {}).get(label, {})
        deep_update(base, tuned_class)
        return base

    def continuous_params(self, score: float) -> dict:
        sel_cfg = self.params.get("selector", {}).get("continuous", {})
        label = self.classify(score)
        cfg = self.params_for_class(label)
        t = float(np.clip(score, 0.0, 1.0))
        cfg["omega"] = _interp(sel_cfg.get("omega", [0.70, 0.96]), t)
        cfg["t0"] = _interp(sel_cfg.get("t0", [0.30, 0.09]), t)
        cfg.setdefault("clahe", {})["clip_limit"] = _interp(
            sel_cfg.get("clahe_clip", [3.0, 1.4]), t
        )
        strength = _interp(sel_cfg.get("retinex_strength", [0.6, 0.0]), t)
        cfg.setdefault("retinex", {})["strength"] = strength
        cfg["retinex"]["enabled"] = bool(strength > 0.02)
        cfg["continuous"] = True
        return cfg

    def select(self, score: float, normalised: dict | None = None) -> dict:
        label = self.classify(score, normalised)
        if self.mode == "continuous":
            cfg = self.continuous_params(score)
        else:
            cfg = self.params_for_class(label)
        return {
            "score": float(score),
            "class": label,
            "mode": self.mode,
            "thresholds": {"t1": self.t1, "t2": self.t2},
            "params": cfg,
        }

    # -- optional shallow classifier ---------------------------------------
    def _load_classifier(self):
        path = resolve_path(
            self.params.get("paths", {}).get("selector_classifier", "config/selector_classifier.joblib")
        )
        if not Path(path).exists():
            return None
        try:
            import joblib

            return joblib.load(path)
        except Exception:
            return None


def train_classifier(
    features: np.ndarray,
    labels: list[str],
    params: dict,
) -> dict:
    """Train a depth-limited decision tree on density features (ablation only)."""
    from sklearn.metrics import accuracy_score
    from sklearn.model_selection import train_test_split
    from sklearn.tree import DecisionTreeClassifier
    import joblib

    cfg = params.get("selector", {}).get("classifier", {})
    x = np.asarray(features, dtype=np.float64)
    y = np.asarray(labels)
    if len(np.unique(y)) < 2:
        model = DecisionTreeClassifier(max_depth=1, random_state=42)
        model.fit(x, y)
        return {"model": model, "accuracy": 1.0, "classes": sorted(set(labels))}
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=float(cfg.get("test_size", 0.25)),
        random_state=int(params.get("project", {}).get("seed", 42)), stratify=y
    )
    model = DecisionTreeClassifier(
        max_depth=int(cfg.get("max_depth", 3)),
        min_samples_leaf=int(cfg.get("min_samples_leaf", 5)),
        random_state=int(params.get("project", {}).get("seed", 42)),
    )
    model.fit(x_train, y_train)
    accuracy = float(accuracy_score(y_test, model.predict(x_test)))
    path = resolve_path(
        params.get("paths", {}).get("selector_classifier", "config/selector_classifier.joblib")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, path)
    return {"model": model, "accuracy": accuracy, "classes": sorted(set(labels))}
