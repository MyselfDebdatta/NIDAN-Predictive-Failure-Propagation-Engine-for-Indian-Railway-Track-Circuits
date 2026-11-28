"""Tests for spec §13 promotion gates, 28-day shadow registry, parity, and rollback."""

from __future__ import annotations

import json

from nidan_ai.eval.shadow import ModelRegistry, ShadowObservation, evaluate_promotion_gates
from nidan_ai.worker.run import main


def _passing_obs(as_of: str) -> ShadowObservation:
    return ShadowObservation(
        as_of=as_of,
        ece=0.02,
        coverage=0.90,
        mean_set_size=1.0,
        rul_coverage=0.80,
        division_coverage_gap=0.02,
        max_psi=0.08,
        contract_valid=True,
        vital_writes=0,
        dataset_hash="bench-hash",
        bench_version="nidan-bench/0.1",
    )


def test_promotion_gates_require_28_days_and_all_seven_checks(tmp_path) -> None:
    reg_path = tmp_path / "registry.json"
    registry = ModelRegistry()

    # Record v1 as previously active
    v1_day0 = _passing_obs("2026-06-01T00:00:00Z")
    v1_day29 = _passing_obs("2026-06-30T00:00:00Z")
    registry.record_observation("nidan-ai/0.0.9", v1_day0, promote_if_ready=True)
    entry_v1 = registry.record_observation("nidan-ai/0.0.9", v1_day29, promote_if_ready=True)
    assert entry_v1.state == "active"
    assert registry.active_version == "nidan-ai/0.0.9"

    # Candidate v2 on day 0 fails Shadow period (<28d) even if metrics pass
    v2_day0 = _passing_obs("2026-07-01T00:00:00Z")
    entry_v2 = registry.record_observation("nidan-ai/0.1.0", v2_day0, promote_if_ready=True)
    assert entry_v2.state == "shadow"
    assert any("Shadow period" in reason for reason in entry_v2.demotion_reasons)
    assert registry.active_version == "nidan-ai/0.0.9"

    # Parity violation (>0.04), drift violation (>0.20), vital write (>0) all block promotion
    bad = ShadowObservation(
        as_of="2026-07-30T00:00:00Z",
        ece=0.08,
        coverage=0.90,
        mean_set_size=1.0,
        rul_coverage=0.80,
        division_coverage_gap=0.07,
        max_psi=0.35,
        contract_valid=False,
        vital_writes=1,
    )
    ok, _, failures = evaluate_promotion_gates(bad, shadow_days=29.0)
    assert ok is False
    assert len(failures) == 5

    # After 29 clean shadow days, v2 promotes active
    v2_day29 = _passing_obs("2026-07-30T00:00:00Z")
    entry_v2 = registry.record_observation("nidan-ai/0.1.0", v2_day29, promote_if_ready=True)
    assert entry_v2.state == "active"
    assert registry.active_version == "nidan-ai/0.1.0"
    assert registry.previous_active_version == "nidan-ai/0.0.9"

    # Subsequent gate failure on v2 demotes it back to shadow & rolls back pointer to v1
    drifted = ShadowObservation(
        as_of="2026-08-02T00:00:00Z",
        ece=0.02,
        coverage=0.90,
        mean_set_size=1.0,
        rul_coverage=0.80,
        division_coverage_gap=0.02,
        max_psi=0.45,
        contract_valid=True,
        vital_writes=0,
    )
    entry_v2 = registry.record_observation("nidan-ai/0.1.0", drifted, promote_if_ready=True)
    assert entry_v2.state == "shadow"
    assert registry.active_version == "nidan-ai/0.0.9"

    registry.save(reg_path)
    reloaded = ModelRegistry.load(reg_path)
    assert reloaded.active_version == "nidan-ai/0.0.9"


def test_worker_cli_shadow_mode_updates_registry(tmp_path, capsys) -> None:
    reg_path = tmp_path / "shadow_registry.json"
    rc = main(
        [
            "--scenario",
            "monsoon-60d",
            "--seed",
            "42",
            "--shadow",
            "--registry-path",
            str(reg_path),
        ]
    )
    assert rc == 0
    captured = json.loads(capsys.readouterr().out)
    assert captured["state"] == "shadow"
    assert captured["activeVersion"] is None
    assert reg_path.exists()
