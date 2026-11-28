"""Phase A2 leakage tests: UTC enforcement, split embargoes, no future/target leakage."""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

from nidan_ai.bench.generator import generate
from nidan_ai.data.canonical import NaiveTimestampError, from_bench, parse_utc
from nidan_ai.data.features import MODEL_FEATURES, build_features, context_from_asset
from nidan_ai.eval.splits import (
    LeakageError,
    assert_no_future,
    assert_no_group_overlap,
    exclude_post_repair,
    group_split,
    temporal_split,
)


def test_naive_timestamp_is_rejected() -> None:
    with pytest.raises(NaiveTimestampError):
        parse_utc("2026-07-14T12:00:00")
    with pytest.raises(NaiveTimestampError):
        parse_utc(datetime(2026, 7, 14, 12, 0))
    aware = parse_utc("2026-07-14T17:30:00+05:30")
    assert aware.tzinfo == UTC
    assert aware.hour == 12


def test_temporal_and_group_splits_enforce_embargo_and_no_overlap() -> None:
    base = datetime(2026, 6, 1, tzinfo=UTC)
    timestamps = [base + timedelta(hours=i) for i in range(240)]
    split = temporal_split(timestamps, embargo_days=1)
    assert timestamps[int(split.calibration[0])] - timestamps[int(split.train[-1])] >= timedelta(
        days=1
    )
    assert timestamps[int(split.test[0])] - timestamps[int(split.calibration[-1])] >= timedelta(
        days=1
    )

    short = [base + timedelta(hours=i) for i in range(12)]
    with pytest.raises(LeakageError):
        temporal_split(short, embargo_days=2)

    groups = ["STN_A", "STN_A", "STN_B", "STN_B", "STN_C", "STN_D"]
    tr, te = group_split(groups, test_fraction=0.33, seed=42)
    assert_no_group_overlap([groups[i] for i in tr], [groups[i] for i in te])
    with pytest.raises(LeakageError):
        assert_no_group_overlap(["STN_A", "STN_B"], ["STN_B", "STN_C"])


def test_no_future_and_exclude_post_repair() -> None:
    base = datetime(2026, 6, 1, tzinfo=UTC)
    times = [base + timedelta(days=d) for d in range(10)]
    assert_no_future(base + timedelta(days=9), times)
    with pytest.raises(LeakageError):
        assert_no_future(base + timedelta(days=5), times)

    keep = exclude_post_repair(times, repair_time=base + timedelta(days=6))
    assert keep.tolist() == [0, 1, 2, 3, 4, 5]


def test_feature_vector_ignores_future_mutations_and_has_no_target_columns() -> None:
    forbidden = {"days_to_failure", "event_day", "event_mode", "closure_text", "cause_code"}
    assert forbidden.isdisjoint(set(MODEL_FEATURES))

    stream = generate("monsoon-60d", seed=42)
    asset = stream.assets[0]
    ctx = context_from_asset(asset)
    as_of = stream.timestamps[25 * 24]

    ds1 = from_bench(stream, as_of=stream.timestamps[-1])
    fv1 = build_features(ds1.assets[asset.asset_id], ctx, as_of)

    mutated = copy.deepcopy(stream)
    mutated.series[asset.asset_id]["relay_i"][26 * 24 :] = 0.0
    ds2 = from_bench(mutated, as_of=mutated.timestamps[-1])
    fv2 = build_features(ds2.assets[asset.asset_id], ctx, as_of)

    assert np.array_equal(fv1.array(MODEL_FEATURES), fv2.array(MODEL_FEATURES))
