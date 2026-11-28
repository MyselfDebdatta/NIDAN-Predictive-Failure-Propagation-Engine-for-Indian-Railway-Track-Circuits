"""Determinism tests: identical seed, scenario and code version yield byte-identical JSON."""

from __future__ import annotations

from nidan_ai.bench.manifest import canonical_json, sha256_canonical
from nidan_ai.worker.run import build_synthetic_dry_run_payload, run_scoring_pipeline


def test_synthetic_payload_is_byte_identical_across_reruns() -> None:
    first = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    second = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    assert canonical_json(first) == canonical_json(second)
    assert sha256_canonical(first) == sha256_canonical(second)


def test_full_scoring_pipeline_is_byte_identical_across_reruns() -> None:
    p1, _, _ = run_scoring_pipeline(scenario="monsoon-60d", seed=42)
    p2, _, _ = run_scoring_pipeline(scenario="monsoon-60d", seed=42)
    assert canonical_json(p1) == canonical_json(p2)
    assert sha256_canonical(p1) == sha256_canonical(p2)
