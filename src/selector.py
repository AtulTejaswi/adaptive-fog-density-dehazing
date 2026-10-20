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
        self.local_calibration = (
            load_json(paths.get("calibration_local", "config/calibration_local.json"), default={}) or {}
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

    # -- v2: spatially varying parameters -----------------------------------
    def class_anchors(self) -> list[float]:
        """Score anchors for the three classes (calib centroids when available)."""
        centroids = self.local_calibration.get("class_score_centroids") or {}
        anchors = [float(centroids[c]) for c in CLASSES if c in centroids]
        if len(anchors) == 3:
            return anchors
        return [0.5 * self.t1, 0.5 * (self.t1 + self.t2),
                min(1.0, self.t2 + 0.5 * (1.0 - self.t2))]

    def parameter_maps(self, score_map: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Interpolate omega(x) and t0(x) from the per-class values.

        Anchors are the calibration class centroids, so the map follows the
        same score scale as the three-bin selector.  omega is non-decreasing
        and t0 is non-increasing in density.
        """
        values = []
        for label in CLASSES:
            cfg = self.params_for_class(label)
            values.append((float(cfg.get("omega", 0.85)), float(cfg.get("t0", 0.20))))
        xs = np.asarray(self.class_anchors(), dtype=np.float64)
        order = np.argsort(xs)
        xs = xs[order]
        # strictly increasing anchors for np.interp
        for i in range(1, len(xs)):
            if xs[i] <= xs[i - 1] + 1e-6:
                xs[i] = xs[i - 1] + 1e-3
        omegas = np.asarray([values[i][0] for i in order], dtype=np.float64)
        t0s = np.asarray([values[i][1] for i in order], dtype=np.float64)
        omegas = np.maximum.accumulate(omegas)
        t0s = np.minimum.accumulate(t0s)

        dehaze = self.params.get("dehaze", {})
        local = self.params.get("v2", {}).get("local_density", {})
        omega_bounds = local.get("omega_bounds", [float(omegas.min()), float(dehaze.get("max_omega", 0.97))])
        t0_bounds = local.get("t0_bounds", [float(dehaze.get("min_t0", 0.05)), float(t0s.max())])
        omega_map = np.interp(score_map, xs, omegas)
        t0_map = np.interp(score_map, xs, t0s)
        omega_map = np.clip(omega_map, float(omega_bounds[0]), float(omega_bounds[1]))
        t0_map = np.clip(t0_map, float(t0_bounds[0]), float(t0_bounds[1]))
        return omega_map.astype(np.float32), t0_map.astype(np.float32)

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
