"""The legacy suitability classifier, scoped honestly (spec 02, R2).

Trained on a public dataset with no location, season or price, whose soil
units don't match Soil Health Cards. So it is used only when every input is
known and inside its training range, with low weight in the ranking.

Explanations are per-prediction tree contributions (Saabas method) on the
random forest under the calibration: for one field, how much each input
pushed the probability of a crop up or down. They name real inputs because
the model has no PCA step.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "models" / "suitability.joblib"


@dataclass(frozen=True)
class Suitability:
    version: str
    probabilities: dict[str, float]  # dataset label -> calibrated probability
    _x: tuple  # the input row, kept for explanations

    def contributions(self, label: str) -> dict[str, float]:
        return explain(np.array(self._x), label)


@lru_cache(maxsize=1)
def bundle() -> dict:
    import joblib  # deferred: keeps app start fast when the planner isn't used

    return joblib.load(MODEL_PATH)


def out_of_range(values: dict[str, float]) -> list[str]:
    ranges = bundle()["ranges"]
    return [f for f, v in values.items() if not ranges[f][0] <= v <= ranges[f][1]]


def predict(values: dict[str, float]) -> Suitability:
    b = bundle()
    x = np.array([[values[f] for f in b["features"]]])
    proba = b["model"].predict_proba(x)[0]
    return Suitability(b["version"], {label: float(p) for label, p in zip(b["model"].classes_, proba)},
                       tuple(x[0]))


def explain(x: np.ndarray, label: str) -> dict[str, float]:
    """Mean per-tree change in P(label) attributed to each input."""
    b = bundle()
    pipeline = b["model"].calibrated_classifiers_[0].estimator
    scaled = pipeline.named_steps["scale"].transform(x.reshape(1, -1))[0]
    forest = pipeline.named_steps["forest"]
    k = list(forest.classes_).index(label)
    total = np.zeros(len(b["features"]))
    for tree in forest.estimators_:
        t = tree.tree_
        values = t.value[:, 0, :]
        values = values / values.sum(axis=1, keepdims=True)
        node, prev = 0, values[0, k]
        while t.children_left[node] != -1:
            feature = t.feature[node]
            node = t.children_left[node] if scaled[feature] <= t.threshold[node] else t.children_right[node]
            total[feature] += values[node, k] - prev
            prev = values[node, k]
    total /= len(forest.estimators_)
    return {f: float(v) for f, v in zip(b["features"], total)}


def metrics() -> dict:
    return bundle()["metrics"]
