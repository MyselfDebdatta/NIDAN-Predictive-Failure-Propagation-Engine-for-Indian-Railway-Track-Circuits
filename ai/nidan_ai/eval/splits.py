"""Time- and station-aware splits with embargoes.

Never shuffle across time. No station appears in both train and test. An embargo removes the
boundary window, and post-repair samples are excluded from pre-failure windows by the feature
builder's as-of rule and by the explicit checks here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np


class LeakageError(AssertionError):
    """Raised when a split or feature window violates the leakage contract."""


@dataclass(frozen=True, slots=True)
class TemporalSplit:
    """Index sets for a time-ordered train/calibration/test split."""

    train: np.ndarray
    calibration: np.ndarray
    test: np.ndarray
    embargo: timedelta

    def as_dict(self) -> dict[str, list[int]]:
        return {
            "train": self.train.tolist(),
            "calibration": self.calibration.tolist(),
            "test": self.test.tolist(),
        }


def temporal_split(
    timestamps: list[datetime],
    *,
    train_fraction: float = 0.60,
    calibration_fraction: float = 0.20,
    embargo_days: int = 1,
) -> TemporalSplit:
    """Split ordered timestamps into train/calibration/test with an embargo gap."""
    if not timestamps:
        raise ValueError("No timestamps to split")
    order = np.argsort(np.array([timestamp.timestamp() for timestamp in timestamps]), kind="stable")
    n = order.size
    n_train = int(train_fraction * n)
    n_cal = int(calibration_fraction * n)
    embargo = timedelta(days=embargo_days)
    train = order[:n_train]
    if not train.size:
        raise LeakageError("Training split is empty")
    train_end = timestamps[int(train[-1])]
    cal_candidates = [idx for idx in order[n_train:] if timestamps[int(idx)] - train_end >= embargo]
    calibration = np.array(cal_candidates[:n_cal], dtype=int)
    if not calibration.size:
        raise LeakageError("Embargo gap leaves no samples for calibration")
    cal_end = timestamps[int(calibration[-1])]
    test_candidates = [
        idx for idx in cal_candidates[n_cal:] if timestamps[int(idx)] - cal_end >= embargo
    ]
    test = np.array(test_candidates, dtype=int)
    if not test.size:
        raise LeakageError("Embargo gap leaves no samples for test")
    return TemporalSplit(train=train, calibration=calibration, test=test, embargo=embargo)


def group_split(
    groups: list[str],
    *,
    test_fraction: float = 0.25,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Split by group (station/division) so no group crosses the boundary."""
    unique = sorted(set(groups))
    if len(unique) < 2:
        raise LeakageError("At least two groups are required")
    rng = np.random.default_rng(seed)
    shuffled = list(unique)
    rng.shuffle(shuffled)
    n_test = max(1, int(round(test_fraction * len(shuffled))))
    test_groups = set(shuffled[:n_test])
    train = np.array([index for index, group in enumerate(groups) if group not in test_groups])
    test = np.array([index for index, group in enumerate(groups) if group in test_groups])
    assert_no_group_overlap([groups[index] for index in train], [groups[index] for index in test])
    return train, test


def assert_no_group_overlap(train_groups: list[str], test_groups: list[str]) -> None:
    overlap = set(train_groups) & set(test_groups)
    if overlap:
        raise LeakageError(f"Group overlap between train and test: {sorted(overlap)}")


def assert_no_future(feature_as_of: datetime, input_times: list[datetime]) -> None:
    future = [timestamp for timestamp in input_times if timestamp > feature_as_of]
    if future:
        raise LeakageError(f"Feature window contains {len(future)} future sample(s)")


def exclude_post_repair(timestamps: list[datetime], *, repair_time: datetime) -> np.ndarray:
    """Indices strictly before a repair, for pre-failure windows."""
    return np.array(
        [index for index, timestamp in enumerate(timestamps) if timestamp < repair_time],
        dtype=int,
    )
