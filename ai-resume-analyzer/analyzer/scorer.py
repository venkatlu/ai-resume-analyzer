"""ATS scoring.

A small TensorFlow/Keras network maps 7 resume<->job features to a 0-100 ATS score.
The network is trained (first run only, ~10 s) on synthetic data generated from a
transparent weighted rule, so it behaves like the rule but is smooth and non-linear.
If you have real labelled resumes, replace `_synthetic_data()` with your data.
If TensorFlow is not installed the weighted rule is used directly.
"""
import os
import threading

import numpy as np

FEATURES = ["skill_match", "keyword_match", "semantic_similarity",
            "section_completeness", "contact_info", "impact_language", "length_quality"]
WEIGHTS = np.array([0.35, 0.20, 0.15, 0.12, 0.05, 0.08, 0.05], dtype="float32")

MODEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", "ats_model.keras")
_lock = threading.Lock()
_model = None
_tf_failed = False


def rule_score(x):
    x = np.asarray(x, dtype="float32")
    base = float(np.dot(x, WEIGHTS))
    if x[0] < 0.25:            # very poor skill overlap is penalised extra
        base *= 0.85
    return max(0.0, min(1.0, base))


def _synthetic_data(n=6000, seed=42):
    rng = np.random.default_rng(seed)
    X = rng.random((n, len(FEATURES))).astype("float32")
    y = np.array([rule_score(r) for r in X], dtype="float32")
    y = np.clip(y + rng.normal(0, 0.015, n).astype("float32"), 0, 1)
    return X, y


def train_model(save=True):
    import tensorflow as tf
    tf.random.set_seed(42)
    X, y = _synthetic_data()
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(len(FEATURES),)),
        tf.keras.layers.Dense(32, activation="relu"),
        tf.keras.layers.Dense(16, activation="relu"),
        tf.keras.layers.Dense(1, activation="sigmoid"),
    ])
    model.compile(optimizer=tf.keras.optimizers.Adam(0.005), loss="mse", metrics=["mae"])
    model.fit(X, y, epochs=40, batch_size=64, validation_split=0.15, verbose=0)
    if save:
        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        model.save(MODEL_PATH)
    return model


def _get_model():
    global _model, _tf_failed
    if _model is not None or _tf_failed:
        return _model
    with _lock:
        if _model is not None or _tf_failed:
            return _model
        try:
            os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
            import tensorflow as tf
            if os.path.exists(MODEL_PATH):
                _model = tf.keras.models.load_model(MODEL_PATH)
            else:
                _model = train_model()
        except Exception as exc:  # TF missing / incompatible -> fall back to rule
            print(f"[scorer] TensorFlow unavailable ({exc}); using rule-based score.")
            _tf_failed = True
    return _model


def predict_score(features):
    """features: list of 7 floats in [0,1] -> (score 0-100, engine name)."""
    x = np.clip(np.asarray(features, dtype="float32"), 0, 1)
    model = _get_model()
    if model is not None:
        try:
            s = float(model.predict(x.reshape(1, -1), verbose=0)[0][0])
            return round(s * 100, 1), "TensorFlow neural scorer"
        except Exception as exc:
            print(f"[scorer] prediction failed ({exc}); using rule.")
    return round(rule_score(x) * 100, 1), "Weighted rule scorer"
