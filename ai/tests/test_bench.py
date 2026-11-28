"""Phase A2 NIDAN-Bench tests: reproducibility, manifest hash, scenarios, and wire samples."""

from __future__ import annotations

import numpy as np

from nidan_ai.bench.generator import as_telemetry_samples, generate
from nidan_ai.bench.manifest import canonical_json
from nidan_ai.bench.scenarios import SCENARIO_NAMES, scenario_manifest


def test_bench_seed_reproducibility_and_manifest_hash() -> None:
    s1 = generate("monsoon-60d", seed=42)
    s2 = generate("monsoon-60d", seed=42)
    s3 = generate("monsoon-60d", seed=7)

    assert s1.manifest.hash == s2.manifest.hash
    assert s1.manifest.hash != s3.manifest.hash
    assert canonical_json(scenario_manifest()) == canonical_json(s1.manifest.scenarios)
    assert s1.asset_ids == s2.asset_ids
    assert [e.event_day for e in s1.events] == [e.event_day for e in s2.events]
    for aid in s1.asset_ids:
        for key in s1.series[aid]:
            assert np.array_equal(s1.series[aid][key], s2.series[aid][key], equal_nan=True)


def test_all_twelve_scenarios_generate_with_ground_truth_events() -> None:
    assert len(SCENARIO_NAMES) == 12
    for name in SCENARIO_NAMES:
        stream = generate(name, seed=42, days=12 if name == "relay-ageing" else None)
        assert len(stream.assets) == stream.scenario_def.asset_count
        assert len(stream.events) >= 1
        assert all(event.mode == stream.scenario_def.event_mode for event in stream.events)


def test_as_telemetry_samples_emits_utc_canonical_rows() -> None:
    stream = generate("monsoon-60d", seed=42, days=5)
    samples = as_telemetry_samples(stream, asset_ids=[stream.asset_ids[0]])
    assert len(samples) > 0
    first = samples[0]
    assert first["assetId"] == stream.asset_ids[0]
    assert first["observedAt"].endswith("Z")
    assert first["quality"] in (0, 1, 2)
    assert np.isfinite(first["value"])
