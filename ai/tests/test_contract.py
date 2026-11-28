"""Contract tests against the frozen backend Pydantic models (spec §3, §17)."""

from __future__ import annotations

import copy
import json
import re

import pytest
from pydantic import ValidationError

from nidan_ai.schemas import (
    validate_assessment,
    validate_model_health,
    validate_publish_payload,
)
from nidan_ai.worker.run import build_synthetic_dry_run_payload, main

_MODE_RE = re.compile(r"^F(?:[1-9]|1[0-2])$")


def test_dry_run_payload_validates_against_backend_contract() -> None:
    payload = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    validated = validate_publish_payload(payload)
    dumped = validated.model_dump(by_alias=True, mode="json")

    assert dumped["policyVersion"] == "policy-2026.07"
    assert len(dumped["assessments"]) >= 1
    seen_ranks: set[int] = set()
    for row in dumped["assessments"]:
        assert "h7d" in row
        assert "h7D" not in row
        assert 0.0 <= row["h24"] <= row["h72"] <= row["h7d"] <= 1.0
        assert 0 <= row["p10Days"] <= row["medianDays"] <= row["p90Days"]
        assert 1 <= len(row["likelyModes"]) <= 3
        for mode in row["likelyModes"]:
            assert _MODE_RE.match(mode)
        if row["level"] == "critical":
            assert row["h24"] > 0.5 or row["clusterRoot"]
            expected = row["h24"]
        elif row["level"] == "warning":
            assert row["h72"] > 0.3
            expected = row["h72"]
        else:
            expected = row["h7d"]
        assert abs(row["ranking"]["calibratedRisk"] - expected) < 1e-6
        assert (row["blockWindowId"] is None) == (row["blockFit"] is None)
        assert row["policyRank"] >= 1
        assert row["policyRank"] not in seen_ranks
        seen_ranks.add(row["policyRank"])
        assert row["explanation"]["physics"]["falsifier"]


def test_cli_dry_run_writes_valid_json(tmp_path) -> None:
    out_file = tmp_path / "payload.json"
    exit_code = main(
        [
            "--scenario",
            "monsoon-60d",
            "--seed",
            "42",
            "--dry-run",
            "--out",
            str(out_file),
        ]
    )
    assert exit_code == 0
    raw = json.loads(out_file.read_text(encoding="utf-8"))
    validate_publish_payload(raw)


def test_broken_assessments_are_rejected() -> None:
    payload = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    base = payload["assessments"][0]

    # 1. Horizon monotonicity violated
    bad_horizon = copy.deepcopy(base)
    bad_horizon["h24"] = 0.8
    bad_horizon["h72"] = 0.4
    with pytest.raises(ValidationError):
        validate_assessment(bad_horizon)

    # 2. RUL quantile ordering violated
    bad_rul = copy.deepcopy(base)
    bad_rul["p10Days"] = 20
    bad_rul["medianDays"] = 10
    with pytest.raises(ValidationError):
        validate_assessment(bad_rul)

    # 3. Critical rule violated
    bad_critical = copy.deepcopy(base)
    bad_critical["level"] = "critical"
    bad_critical["h24"] = 0.2
    bad_critical["clusterRoot"] = False
    with pytest.raises(ValidationError):
        validate_assessment(bad_critical)

    # 4. Warning rule violated
    bad_warning = copy.deepcopy(base)
    bad_warning["level"] = "warning"
    bad_warning["h72"] = 0.2
    with pytest.raises(ValidationError):
        validate_assessment(bad_warning)

    # 5. Block pairing violated
    bad_block = copy.deepcopy(base)
    bad_block["blockWindowId"] = "RB-28"
    bad_block["blockFit"] = None
    with pytest.raises(ValidationError):
        validate_assessment(bad_block)

    # 6. Invalid failure mode outside F1..F12
    bad_mode = copy.deepcopy(base)
    bad_mode["likelyModes"] = ["F99"]
    with pytest.raises(ValidationError):
        validate_assessment(bad_mode)

    # 7. Ranking calibratedRisk mismatch
    bad_rank = copy.deepcopy(base)
    bad_rank["ranking"]["calibratedRisk"] = 0.99
    with pytest.raises(ValueError):
        validate_assessment(bad_rank)


def test_duplicate_asset_id_is_rejected() -> None:
    payload = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    dup = copy.deepcopy(payload["assessments"][0])
    dup["policyRank"] = 99
    payload["assessments"].append(dup)
    with pytest.raises(ValueError, match="Duplicate assetId"):
        validate_publish_payload(payload)


def test_model_health_contract_validates() -> None:
    health = {
        "asOf": "2026-07-14T00:00:00Z",
        "window": "2026-06-01 to 2026-07-14",
        "ece": 0.031,
        "eceBins": 10,
        "coverage": 0.90,
        "heldOutN": 120,
        "activeModels": 5,
        "driftAmber": 0,
        "models": [
            {
                "name": "Physics twin",
                "version": "0.3.1",
                "trained": "2026-07-14T00:00:00Z",
                "window": "2026-06-01 to 2026-07-14",
                "owner": "S&T R&D",
                "state": "Active",
            }
        ],
        "reliability": [{"predicted": 0.1, "observed": 0.1, "n": 40}],
        "byLevel": [
            {
                "level": "watch",
                "predicted": 0.22,
                "observed": 0.21,
                "n": 80,
                "leadTime": "18 d median",
            }
        ],
        "byMode": [{"code": "F1", "precision": 0.85, "recall": 0.80, "n": 50}],
        "drift": [{"name": "Rainfall", "psi": 0.08, "threshold": 0.20, "state": "nominal"}],
        "dataTrust": {"division": 0.92, "lowTrustAssets": 1, "flags": []},
        "gates": [{"name": "Calibration", "rule": "ECE <= 0.05", "value": "0.031", "pass": True}],
        "signature": "nidan-ai/0.1.0",
        "modelVersions": {
            "twin": "0.3.1",
            "gnn": "0.2.0",
            "survival": "0.2.4",
            "classifier": "0.2.0",
        },
        "generatedAt": "2026-07-14T00:00:00Z",
    }
    validated = validate_model_health(health)
    assert validated.ece == pytest.approx(0.031)
