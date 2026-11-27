"""Phase 3 tests: telemetry QC, CCSP/RDPMS adapters, idempotent model-run, WS auth, rate limit."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.auth import clear_jwks_cache
from app.config import get_settings
from app.ingestion import (
    KafkaTelemetryConsumer,
    MqttTelemetryConsumer,
    TelemetryIngestProcessor,
    TelemetrySample,
    evaluate_sample_qc,
)
from app.main import create_app
from app.services.memory_repo import MemoryRepository
from tests.test_phase2_features import _generate_rsa_jwk, _mint_token


@pytest.fixture()
def dev_client() -> TestClient:
    settings = get_settings().model_copy(update={"data_mode": "fixture", "auth_mode": "dev"})
    application = create_app(settings=settings)
    with TestClient(application) as tc:
        yield tc


def test_stream_qc_detects_outliers_clock_skew_stuck_runs_and_gaps() -> None:
    now = datetime(2026, 7, 14, 12, 0, 0, tzinfo=UTC)
    samples = [
        # 7h gap between first two valid points -> logger_gap_6h
        TelemetrySample(
            assetId="ADRA/TC/12T",
            signalKey="relay_i",
            observedAt=now - timedelta(hours=8),
            value=118.0,
        ),
        TelemetrySample(
            assetId="ADRA/TC/12T",
            signalKey="relay_i",
            observedAt=now - timedelta(minutes=30),
            value=117.5,
        ),
        # Out-of-range physical value -> quality=2 + shunt_pattern_review
        TelemetrySample(
            assetId="ADRA/TC/12T",
            signalKey="relay_i",
            observedAt=now - timedelta(minutes=10),
            value=5000.0,
        ),
        # Future clock skew -> quality=2 + clock_skew
        TelemetrySample(
            assetId="ADRA/TC/12T",
            signalKey="relay_i",
            observedAt=now + timedelta(hours=2),
            value=118.0,
        ),
    ]
    # Add 30 identical readings on ballast_g -> stuck_value_run + quality=2 on 30th sample
    for idx in range(30):
        samples.append(
            TelemetrySample(
                assetId="ADRA/TC/12T",
                signalKey="ballast_g",
                observedAt=now - timedelta(minutes=60 - idx),
                value=1.25,
            )
        )

    res = evaluate_sample_qc(samples, now=now)
    flags = res.flags_by_asset["ADRA/TC/12T"]
    assert "logger_gap_6h" in flags
    assert "clock_skew" in flags
    assert "shunt_pattern_review" in flags
    assert "stuck_value_run" in flags
    assert 0.05 <= res.trust_by_asset["ADRA/TC/12T"] < 0.7

    qualities = [s.quality for s in res.samples]
    assert qualities.count(2) >= 3


def test_ingest_telemetry_canonical_ccsp_and_rdpms_endpoints(dev_client: TestClient) -> None:
    now = datetime.now(UTC)
    canonical = {
        "samples": [
            {
                "assetId": "ADRA/TC/12T",
                "signalKey": "relay_i",
                "observedAt": (now - timedelta(minutes=5)).isoformat(),
                "value": 119.0,
            }
        ]
    }
    r1 = dev_client.post("/v1/ingest/telemetry", json=canonical)
    assert r1.status_code == 200
    assert r1.json()["accepted"] == 1
    assert r1.json()["measuredCount"] == 1

    # Replay same sample -> deduplicated
    r1_dup = dev_client.post("/v1/ingest/telemetry", json=canonical)
    assert r1_dup.status_code == 200
    assert r1_dup.json()["accepted"] == 0
    assert r1_dup.json()["deduplicated"] == 1

    # C-DOT CCSP / oneM2M envelope
    ccsp = {
        "m2m:cin": {
            "ri": "cin-9001",
            "con": {
                "assetId": "ADRA/TC/12T",
                "observedAt": (now - timedelta(minutes=3)).isoformat(),
                "signals": {"feedVoltage": 6.2, "ballastConductance": 1.38},
            },
        }
    }
    r2 = dev_client.post("/v1/ingest/telemetry?protocol=ccsp", json=ccsp)
    assert r2.status_code == 200
    assert r2.json()["accepted"] == 2

    # RDSO/SPN/257/2025 RDPMS frame auto-detected
    rdpms = {
        "stationCode": "ADRA",
        "circuitId": "12T",
        "timestamp": (now - timedelta(minutes=1)).isoformat(),
        "signals": {"relayCurrentMa": 117.4},
    }
    r3 = dev_client.post("/v1/ingest/telemetry", json=rdpms)
    assert r3.status_code == 200
    assert r3.json()["accepted"] == 1

    # Verify /metrics reflects telemetry samples
    metrics_text = dev_client.get("/metrics").text
    assert 'nidan_telemetry_samples_total{quality="measured"}' in metrics_text


async def test_kafka_and_mqtt_consumer_adapters_decode_and_ingest() -> None:
    cfg = get_settings()
    repo = MemoryRepository(cfg.fixtures_snapshot_path)
    processor = TelemetryIngestProcessor(repo)
    kafka = KafkaTelemetryConsumer(processor, bootstrap_servers="localhost:9092")
    mqtt = MqttTelemetryConsumer(processor, hostname="localhost")

    now = datetime.now(UTC)
    k_res = await kafka.handle_message_bytes(
        json.dumps(
            {
                "samples": [
                    {
                        "assetId": "ADRA/TC/12T",
                        "signalKey": "relay_i",
                        "observedAt": (now - timedelta(minutes=2)).isoformat(),
                        "value": 115.0,
                    }
                ]
            }
        ).encode("utf-8")
    )
    assert k_res["accepted"] == 1

    m_res = await mqtt.handle_message_bytes(
        json.dumps(
            {
                "m2m:cin": {
                    "con": json.dumps(
                        {
                            "assetId": "ADRA/TC/14T",
                            "signalKey": "relay_i",
                            "observedAt": (now - timedelta(minutes=1)).isoformat(),
                            "value": 128.0,
                        }
                    )
                }
            }
        ).encode("utf-8")
    )
    assert m_res["accepted"] == 1


def _valid_model_run_payload() -> dict[str, Any]:
    return {
        "snapshotAsOf": "2026-07-14T00:40:00Z",
        "snapshotWeek": 29,
        "snapshotLabel": "14 Jul 2026 · 00:40 IST",
        "codeVersion": "twin-0.3.3",
        "params": {"windowMin": 15},
        "datasetHash": "sha256:abc123",
        "inputWatermark": "2026-07-14T00:39:00Z",
        "clusters": [
            {
                "id": "c-9917",
                "title": "Adra east ballast saturation group",
                "state": "open",
                "summary": "Updated by GNN phase-3 test",
            }
        ],
        "assessments": [
            {
                "assetId": "ADRA/TC/12T",
                "level": "watch",
                "policyRank": 2,
                "persistence": 3,
                "h24": 0.05,
                "h72": 0.12,
                "h7d": 0.25,
                "eceZone": 0.04,
                "p10Days": 8,
                "medianDays": 14,
                "p90Days": 24,
                "rulCoverage": 0.897,
                "heldOutN": 3180,
                "likelyModes": ["F1"],
                "modeProbability": 0.72,
                "modeSetCoverage": 0.91,
                "dataTrustScore": 0.96,
                "clusterId": "c-9917",
                "computedAt": "2026-07-14T00:40:00Z",
            }
        ],
    }


def test_model_run_idempotent_replay_and_spec_invariants(dev_client: TestClient) -> None:
    payload = _valid_model_run_payload()
    first = dev_client.post("/v1/ingest/model-run", json=payload)
    assert first.status_code == 200
    assert first.json()["idempotentReplay"] is False
    assert first.json()["assessmentsWritten"] == 1

    # Exact replay -> idempotentReplay=True, zero writes, no duplicate events
    replay = dev_client.post("/v1/ingest/model-run", json=payload)
    assert replay.status_code == 200
    assert replay.json()["idempotentReplay"] is True
    assert replay.json()["assessmentsWritten"] == 0
    assert replay.json()["eventsPublished"] == []

    # Spec invariants: h24 > h72 rejected (422)
    bad_horizon = _valid_model_run_payload()
    bad_horizon["assessments"][0]["h24"] = 0.4
    bad_horizon["assessments"][0]["h72"] = 0.2
    assert dev_client.post("/v1/ingest/model-run", json=bad_horizon).status_code == 422

    # Critical without h24 > 0.5 and clusterRoot=false rejected (422)
    bad_critical = _valid_model_run_payload()
    bad_critical["assessments"][0]["level"] = "critical"
    assert dev_client.post("/v1/ingest/model-run", json=bad_critical).status_code == 422

    # Invalid failure mode outside F1..F12 rejected (422)
    bad_mode = _valid_model_run_payload()
    bad_mode["assessments"][0]["likelyModes"] = ["F99"]
    assert dev_client.post("/v1/ingest/model-run", json=bad_mode).status_code == 422


def test_websocket_oidc_auth_and_division_scoped_summary() -> None:
    clear_jwks_cache()
    pem, jwks = _generate_rsa_jwk()
    settings = get_settings().model_copy(
        update={
            "data_mode": "fixture",
            "auth_mode": "oidc",
            "oidc_issuer": "https://sso.nidan.local/realms/nidan",
            "oidc_audience": "nidan-api",
        }
    )
    application = create_app(settings=settings)
    application.state.jwks_override = jwks

    with TestClient(application) as client:
        # Unauthenticated WS connection rejected with 1008
        with pytest.raises(WebSocketDisconnect) as ws_exc:
            with client.websocket_connect("/v1/stream"):
                pass
        assert ws_exc.value.code == 1008

        # Authenticated WS with query token connects and receives heartbeat
        bksc_tok = _mint_token(pem, sub="op-bksc", role="operator", divisions=["BKSC"])
        with client.websocket_connect(f"/v1/stream?token={bksc_tok}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "heartbeat"

        # /v1/summary is division-scoped (BKSC only has 1 alert in fixtures)
        summary = client.get("/v1/summary", headers={"Authorization": f"Bearer {bksc_tok}"})
        assert summary.status_code == 200
        assert summary.json()["openAlerts"]["value"] == 1


def test_rate_limiter_returns_429_rfc9457() -> None:
    settings = get_settings().model_copy(
        update={"data_mode": "fixture", "auth_mode": "dev", "rate_limit_per_min": 2}
    )
    application = create_app(settings=settings)
    with TestClient(application) as client:
        assert client.get("/v1/alerts").status_code == 200
        assert client.get("/v1/alerts").status_code == 200
        limited = client.get("/v1/alerts")
        assert limited.status_code == 429
        assert limited.headers["content-type"].startswith("application/problem+json")
        assert limited.json()["type"] == "urn:nidan:rate-limited"
        assert limited.json()["retryable"] is True
        assert int(limited.headers["retry-after"]) >= 1
        # /healthz and /metrics bypass rate limit
        assert client.get("/healthz").status_code == 200
        assert client.get("/metrics").status_code == 200
