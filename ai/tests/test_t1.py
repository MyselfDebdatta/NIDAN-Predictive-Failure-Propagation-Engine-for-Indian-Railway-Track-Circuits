"""Phase A2 tests: stream QC trust flags, feature edge cases, and T1 anomaly detection."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import numpy as np

from nidan_ai.bench.generator import generate
from nidan_ai.config import TRUST_FLAGS
from nidan_ai.data.canonical import AssetTelemetry, TelemetrySeries, from_bench
from nidan_ai.data.features import MODEL_FEATURES, build_features, context_from_asset
from nidan_ai.data.quality import assess_quality
from nidan_ai.models.anomaly import AnomalyDetector
from nidan_ai.physics.line import LineParams, relay_current


def test_quality_flags_match_backend_closed_set_and_edge_cases() -> None:
    base = datetime(2026, 6, 1, tzinfo=UTC)
    times = [base + timedelta(hours=i) for i in range(48)]
    relay = np.full(48, 820.0)
    relay[5:13] = np.nan  # 8 h gap -> logger_gap_6h
    result = assess_quality(
        timestamps=times, relay_ma=relay, as_of=times[-1], clock_offset_minutes=25
    )
    assert set(result.flags).issubset(TRUST_FLAGS)
    assert "logger_gap_6h" in result.flags
    assert "stuck_value_run" in result.flags
    assert "clock_skew" in result.flags
    assert 0.05 <= result.score < 1.0


def test_feature_builder_handles_zero_one_and_all_suspect_samples() -> None:
    stream = generate("monsoon-60d", seed=42, days=5)
    asset = stream.assets[0]
    ctx = context_from_asset(asset)
    as_of = stream.timestamps[-1]

    # Zero samples
    empty = AssetTelemetry(asset_id=asset.asset_id, series={})
    fv_empty = build_features(empty, ctx, as_of)
    assert np.all(np.isfinite(fv_empty.array(MODEL_FEATURES)))

    # One sample
    one = AssetTelemetry(
        asset_id=asset.asset_id,
        series={
            "relay_i": TelemetrySeries(
                asset_id=asset.asset_id,
                signal_key="relay_i",
                observed_at=[as_of],
                values=np.array([750.0]),
            )
        },
    )
    fv_one = build_features(one, ctx, as_of)
    assert np.all(np.isfinite(fv_one.array(MODEL_FEATURES)))

    # All suspect (out-of-bounds)
    suspect = AssetTelemetry(
        asset_id=asset.asset_id,
        series={
            "relay_i": TelemetrySeries(
                asset_id=asset.asset_id,
                signal_key="relay_i",
                observed_at=[as_of - timedelta(hours=i) for i in range(5)],
                values=np.full(5, -50.0),
            )
        },
    )
    fv_sus = build_features(suspect, ctx, as_of)
    assert fv_sus.quality is not None
    assert "shunt_pattern_review" in fv_sus.quality.flags
    assert np.all(np.isfinite(fv_sus.array(MODEL_FEATURES)))


def test_t1_detects_monsoon_60d_drift_with_lead_and_low_false_alarms() -> None:
    stream = generate("monsoon-60d", seed=42)
    dataset = from_bench(stream, as_of=stream.timestamps[-1])

    # Fit detector on early healthy baseline days (days 2..10) across all assets
    healthy_vectors = []
    for asset in stream.assets:
        ctx = context_from_asset(asset)
        for day in (3, 5, 7, 9):
            healthy_vectors.append(
                build_features(dataset.assets[asset.asset_id], ctx, stream.timestamps[day * 24])
            )
    detector = AnomalyDetector.fit(healthy_vectors, seed=42)

    # Check faulted asset lead time
    faulted_asset = next(a for a in stream.assets if a.faulted)
    ctx_f = context_from_asset(faulted_asset)
    daily_f = [
        build_features(dataset.assets[faulted_asset.asset_id], ctx_f, stream.timestamps[d * 24])
        for d in range(2, stream.scenario_def.days)
    ]
    scores_f = detector.score_series(daily_f)
    event = stream.event_for(faulted_asset.asset_id)
    assert event is not None
    alarm_days = [
        day
        for day, res in zip(range(2, stream.scenario_def.days), scores_f, strict=True)
        if (res.score >= detector.threshold or res.trend_alarm) and res.persistence >= 1
    ]
    assert alarm_days, "Expected T1 to raise an alarm before failure on monsoon-60d"
    lead_days = event.event_day - alarm_days[0]
    assert lead_days >= 3, f"Expected >= 3 days lead before day {event.event_day}, got {lead_days}"

    # Check healthy control asset has <= 2 false alarms over 2 station-months
    control_asset = next(a for a in stream.assets if not a.faulted)
    ctx_c = context_from_asset(control_asset)
    daily_c = [
        build_features(dataset.assets[control_asset.asset_id], ctx_c, stream.timestamps[d * 24])
        for d in range(2, stream.scenario_def.days)
    ]
    scores_c = detector.score_series(daily_c)
    false_alarms = sum(
        1 for res in scores_c if res.score >= detector.threshold and res.persistence >= 2
    )
    assert false_alarms <= 2


def test_lower_ballast_resistance_never_lowers_t1_score() -> None:
    params = LineParams()
    base = datetime(2026, 6, 1, tzinfo=UTC)
    times = [base + timedelta(hours=i) for i in range(72)]
    stream = generate("monsoon-60d", seed=42, days=12)
    ds = from_bench(stream, as_of=stream.timestamps[-1])
    ctx = context_from_asset(stream.assets[0])
    healthy = [
        build_features(ds.assets[stream.assets[0].asset_id], ctx, stream.timestamps[d * 24])
        for d in (2, 3, 4, 5)
    ]
    detector = AnomalyDetector.fit(healthy, seed=42)

    scores = []
    for rb in (20.0, 8.0, 3.0, 1.5):
        ma = 1000.0 * relay_current(params, rb)
        tel = AssetTelemetry(
            asset_id=ctx.asset_id,
            series={
                "relay_i": TelemetrySeries(ctx.asset_id, "relay_i", times, np.full(72, ma)),
                "feed_v": TelemetrySeries(
                    ctx.asset_id, "feed_v", times, np.full(72, params.feed_v)
                ),
                "rain_mm": TelemetrySeries(ctx.asset_id, "rain_mm", times, np.zeros(72)),
                "temp_c": TelemetrySeries(ctx.asset_id, "temp_c", times, np.full(72, 28.0)),
            },
        )
        fv = build_features(tel, ctx, times[-1])
        scores.append(detector.score(fv).score)
    assert all(left <= right + 1e-9 for left, right in zip(scores[:-1], scores[1:], strict=True))
