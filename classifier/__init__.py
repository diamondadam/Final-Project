"""
classifier — track health classification module.

Public API
----------
extract_features(daq_path, motion_path) -> np.ndarray
    Extract the 33-element feature vector from one run's CSV files.

load_model(name) -> sklearn Pipeline
    Load a saved model by name: "knn" or "gbm".
    Raises FileNotFoundError if models haven't been trained yet
    (run train_classifiers.py first).

predict(model, daq_path, motion_path) -> dict
    Run inference on one run. Returns:
        {
          "label":        str,           # "Healthy" | "Degraded" | "Damaged"
          "probabilities": {str: float}, # one entry per class
        }

Example
-------
    import classifier
    model = classifier.load_model("knn")
    result = classifier.predict(model, "path/to/daq.csv", "path/to/arduino.csv")
    print(result["label"], result["probabilities"])
"""

import os as _os
import joblib as _joblib
import numpy as _np

from .train_classifiers import extract_features, LABELS  # noqa: F401

_MODEL_DIR = _os.path.join(_os.path.dirname(__file__), "output")
_MODEL_FILES = {
    "knn": "model_knn.joblib",
    "gbm": "model_gbm.joblib",
}


def load_model(name: str):
    """
    Load a trained sklearn Pipeline by name ("knn" or "gbm").

    Raises
    ------
    ValueError
        If `name` is not a recognised model key.
    FileNotFoundError
        If the model file hasn't been generated yet.
    """
    if name not in _MODEL_FILES:
        raise ValueError(f"Unknown model '{name}'. Choose from: {list(_MODEL_FILES)}")
    path = _os.path.join(_MODEL_DIR, _MODEL_FILES[name])
    if not _os.path.exists(path):
        raise FileNotFoundError(
            f"Model file not found: {path}\n"
            "Run `python -m classifier.train_classifiers` to train and save models."
        )
    return _joblib.load(path)


def predict(model, daq_path: str, motion_path: str) -> dict:
    """
    Run inference for one run.

    Parameters
    ----------
    model       : fitted sklearn Pipeline returned by load_model()
    daq_path    : path to daq_sensors_1000hz.csv
    motion_path : path to arduino_motion_raw.csv

    Returns
    -------
    dict with keys:
        "label"         : predicted class string
        "probabilities" : {class_name: probability} for all three classes
    """
    feat = extract_features(daq_path, motion_path).reshape(1, -1)
    label = model.predict(feat)[0]
    proba = model.predict_proba(feat)[0]
    classes = model.classes_
    return {
        "label": label,
        "probabilities": {cls: round(float(p), 4) for cls, p in zip(classes, proba)},
    }
