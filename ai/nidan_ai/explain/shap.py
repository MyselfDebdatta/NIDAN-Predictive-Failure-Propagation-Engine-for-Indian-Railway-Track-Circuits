"""Deterministic signed feature attribution (TreeSHAP-compatible interface).

TreeSHAP is used where the estimator exposes it; otherwise the fallback is a deterministic
permutation attribution: replace one feature with its training median and measure the change
in the predicted probability of the diagnosed class. Values are signed contributions, never
global importances, and the top five are capped for the UI.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from nidan_ai.data.features import FEATURE_LABELS, FeatureVector


def signed_attribution(
    model: Any,
    vector: FeatureVector,
    *,
    top_k: int = 5,
    baseline: np.ndarray | None = None,
) -> list[dict[str, float | str]]:
    """Return the top signed feature contributions for the top predicted class."""
    if hasattr(model, "shap_top"):
        return model.shap_top(vector, top_k=top_k)
    if baseline is None:
        raise ValueError("A baseline vector is required for the permutation fallback")
    feature_names = tuple(sorted(vector.values))
    row = vector.array(feature_names)
    probabilities = np.asarray(model.predict_proba(row.reshape(1, -1)), dtype=float)[0]
    target = int(np.argmax(probabilities))
    contributions: list[tuple[float, str]] = []
    for index, name in enumerate(feature_names):
        replaced = row.copy()
        replaced[index] = baseline[index]
        changed = float(np.asarray(model.predict_proba(replaced.reshape(1, -1)))[0, target])
        contributions.append((float(probabilities[target] - changed), name))
    contributions.sort(key=lambda item: (-abs(item[0]), item[1]))
    return [
        {
            "feature": name,
            "label": FEATURE_LABELS.get(name, name),
            "value": float(value),
        }
        for value, name in contributions[:top_k]
    ]
