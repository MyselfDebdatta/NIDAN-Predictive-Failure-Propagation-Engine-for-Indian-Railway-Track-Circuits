"""Determinism tests: identical seed, scenario and code version yield byte-identical JSON."""

from __future__ import annotations

from nidan_ai.bench.manifest import canonical_json, sha256_canonical
from nidan_ai.worker.run import build_synthetic_dry_run_payload


def test_synthetic_payload_is_byte_identical_across_reruns() -> None:
    first = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    second = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    assert canonical_json(first) == canonical_json(second)
    assert sha256_canonical(first) == sha256_canonical(second)
