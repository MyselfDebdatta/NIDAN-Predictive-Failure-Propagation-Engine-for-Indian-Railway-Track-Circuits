"""Trained model bundle dataclass stored outside ``__main__`` for safe pickling."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from nidan_ai.models.classifier import DiagnosisBundle
from nidan_ai.models.conformal import HorizonCalibrator
from nidan_ai.models.graph import GraphRiskModel
from nidan_ai.models.survival import SurvivalBundle


@dataclass(slots=True)
class EngineBundle:
    """Trained T2, T3, T4, and calibration models for deterministic scoring."""

    diagnosis: DiagnosisBundle
    graph_h24: GraphRiskModel
    graph_h72: GraphRiskModel
    graph_h7d: GraphRiskModel
    survival: SurvivalBundle
    calibrator: HorizonCalibrator
    ece_by_horizon: dict[str, float]
    cal_predictions: np.ndarray
    cal_outcomes: np.ndarray
    reference_margin: np.ndarray
    reference_rain: np.ndarray
    split_name: str
