#!/usr/bin/env python3
"""Retrain the legacy suitability classifier for Crop Planner v2 (spec 02, R2).

Same public dataset as 1.x (dataset/data.csv: N, P, K, temperature,
humidity, pH, rainfall -> 22 crops) but:
  - no PCA, so explanations name real inputs (soil N, pH...), not components;
  - StandardScaler -> RandomForest, stratified 5-fold cross-validation;
  - CalibratedClassifierCV (ensemble=False) for honest probabilities, one model;
  - saved with a version string and the training range of every input, so
    the app refuses inputs outside what the model has seen.

    python scripts/train_suitability.py
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dataset" / "data.csv"
OUT_DIR = ROOT / "agrisense" / "planner" / "models"
FEATURES = ["N", "P", "K", "temperature", "humidity", "ph", "rainfall"]
VERSION = f"suitability-{date.today():%Y.%m}.1"
SEED = 42


def load() -> tuple[np.ndarray, np.ndarray]:
    with DATA.open(encoding="utf-8") as f:
        rows = {tuple(r.values()): r for r in csv.DictReader(f)}  # drops the exact duplicate
    x = np.array([[float(r[k]) for k in FEATURES] for r in rows.values()])
    y = np.array([r["label"] for r in rows.values()])
    return x, y


def pipeline() -> Pipeline:
    return Pipeline([
        ("scale", StandardScaler()),
        ("forest", RandomForestClassifier(n_estimators=200, min_samples_leaf=2, class_weight="balanced",
                                          random_state=SEED, n_jobs=-1)),
    ])


def main() -> int:
    x, y = load()
    x_train, x_test, y_train, y_test = train_test_split(x, y, test_size=0.2, stratify=y, random_state=SEED)

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_scores = cross_val_score(pipeline(), x_train, y_train, cv=cv, scoring="accuracy")

    model = CalibratedClassifierCV(pipeline(), method="sigmoid", cv=cv, ensemble=False)
    model.fit(x_train, y_train)
    proba = model.predict_proba(x_test)
    metrics = {
        "rows": int(len(y)),
        "cv_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cv_accuracy_std": round(float(cv_scores.std()), 4),
        "test_accuracy": round(float(accuracy_score(y_test, model.predict(x_test))), 4),
        "test_log_loss": round(float(log_loss(y_test, proba, labels=model.classes_)), 4),
    }
    # Refit on all rows for the shipped model; the metrics above are from the held-out split.
    model = CalibratedClassifierCV(pipeline(), method="sigmoid", cv=cv, ensemble=False).fit(x, y)

    bundle = {
        "version": VERSION,
        "sklearn": sklearn.__version__,
        "features": FEATURES,
        "classes": [str(c) for c in model.classes_],
        "ranges": {f: [float(x[:, i].min()), float(x[:, i].max())] for i, f in enumerate(FEATURES)},
        "metrics": metrics,
        "model": model,
        "source": "dataset/data.csv (public Kaggle crop recommendation dataset, augmented; no location, season or price)",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / "suitability.joblib"
    joblib.dump(bundle, path, compress=3)
    (OUT_DIR / "suitability.json").write_text(
        json.dumps({k: v for k, v in bundle.items() if k != "model"}, indent=2), encoding="utf-8")
    print(f"{VERSION}: {json.dumps(metrics)}")
    print(f"saved {path.relative_to(ROOT)} ({path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
