"""API contract tests verifying every endpoint against Nidan-Frontend expectations."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture()
def client() -> TestClient:
    settings = get_settings().model_copy(update={"data_mode": "fixture"})
    application = create_app(settings=settings)
    with TestClient(application) as tc:
        yield tc


def test_healthz_and_advisory_headers(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["advisoryOnly"] is True
    assert body["vitalCommandCapable"] is False
    assert resp.headers["x-nidan-mode"] == "advisory-non-vital"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"


def test_list_and_get_alerts_camel_case(client: TestClient) -> None:
    resp = client.get("/v1/alerts")
    assert resp.status_code == 200
    alerts = resp.json()
    assert len(alerts) == 11
    ranks = [a["policyRank"] for a in alerts]
    assert ranks == sorted(ranks)
    assert "x-nidan-generated-at" in resp.headers
    assert "x-nidan-model-versions" in resp.headers

    detail = client.get("/v1/alerts/alr-7f3c")
    assert detail.status_code == 200
    item = detail.json()
    assert item["assetId"] == "ADRA/TC/12T"
    assert item["explanation"]["physics"]["headline"]
    assert item["explanation"]["model"]["shapTop"]
    assert item["explanation"]["precedents"]


def test_alert_not_found_returns_rfc9457(client: TestClient) -> None:
    resp = client.get("/v1/alerts/does-not-exist")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/problem+json")
    problem = resp.json()
    assert problem["status"] == 404
    assert problem["type"] == "urn:nidan:not-found"
    assert problem["traceId"]


def test_acknowledge_and_defer_workflow(client: TestClient) -> None:
    ack = client.post("/v1/alerts/alr-7f3c/acknowledge")
    assert ack.status_code == 200
    assert ack.json()["acknowledged"] is True

    bad_defer = client.post(
        "/v1/alerts/alr-7f3c/defer",
        json={"reason": "short", "reviewDate": "2026-07-20"},
    )
    assert bad_defer.status_code == 422
    assert bad_defer.json()["traceId"]

    good_defer = client.post(
        "/v1/alerts/alr-7f3c/defer",
        json={
            "reason": "Scheduled drain rodding booked with PWay crew for RB-28",
            "reviewDate": "2026-07-16",
        },
    )
    assert good_defer.status_code == 200
    assert good_defer.json()["deferred"] is True


def test_asset_detail_and_explanation_with_slash_ids(client: TestClient) -> None:
    encoded = client.get("/v1/assets/ADRA%2FTC%2F12T")
    assert encoded.status_code == 200
    body = encoded.json()
    assert body["record"]["id"] == "ADRA/TC/12T"
    assert len(body["signals"]) == 4
    relay_series = next(s for s in body["signals"] if s["key"] == "relay_i")
    assert relay_series["values"][-1] == 118

    expl = client.get("/v1/assets/ADRA%2FTC%2F12T/explanation")
    assert expl.status_code == 200
    expl_body = expl.json()
    assert expl_body["alertId"] == "alr-7f3c"
    assert expl_body["physics"]["falsifier"]


def test_blocks_clusters_and_merge(client: TestClient) -> None:
    blocks = client.get("/v1/blocks").json()
    assert len(blocks["windows"]) == 7
    assert len(blocks["jobs"]) == 8

    filtered = client.get("/v1/blocks?from=2026-07-16&to=2026-07-18").json()
    assert len(filtered["windows"]) == 3

    clusters = client.get("/v1/clusters").json()
    assert len(clusters) == 2
    c9917 = next(c for c in clusters if c["id"] == "c-9917")
    assert c9917["members"] == ["ADRA/TC/12T", "ADRA/TC/14T", "ADRA/TC/16T"]

    merged = client.post("/v1/clusters/c-9917/merge", json={"alertIds": ["alr-1f42"]})
    assert merged.status_code == 200
    assert "ADRA/TC/09T" in merged.json()["cluster"]["members"]


def test_field_tasks_and_idempotent_observations(client: TestClient) -> None:
    tasks_resp = client.get("/v1/field/tasks")
    assert tasks_resp.status_code == 200
    tasks_body = tasks_resp.json()
    assert len(tasks_body["tasks"]) == 3
    assert tasks_body["tasks"][0]["titleHi"]

    key = "0191a2b3-c4d5-7e8f-9a0b-1c2d3e4f5a6b"
    payload = {
        "idempotencyKey": key,
        "taskId": "task-12t",
        "finding": "confirmed",
        "measurements": {
            "relayCurrent": "116",
            "ballastConductance": "1.34",
            "cableInsulation": "0.58",
            "feedVoltage": "6.1",
        },
        "note": "Water pooling near chainage 4 cess drain",
        "createdAt": "2026-07-14T00:25:00Z",
    }
    first = client.post(
        "/v1/field/observations",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    assert first.status_code == 200
    assert first.json()["queued"] is True
    assert first.json()["replayed"] is False

    replay = client.post(
        "/v1/field/observations",
        headers={"Idempotency-Key": key},
        json=payload,
    )
    assert replay.status_code == 200
    assert replay.json()["receipt"] == first.json()["receipt"]
    assert replay.json()["replayed"] is True

    conflict_payload = {**payload, "finding": "not-found"}
    conflict = client.post(
        "/v1/field/observations",
        headers={"Idempotency-Key": key},
        json=conflict_payload,
    )
    assert conflict.status_code == 409
    assert conflict.json()["serverRecord"]["finding"] == "confirmed"
    assert conflict.json()["localRecord"]["finding"] == "not-found"


def test_models_summary_search_me_and_draft_work_order(client: TestClient) -> None:
    health = client.get("/v1/models/health").json()
    assert health["ece"] == 0.031
    assert len(health["models"]) == 5

    summary = client.get("/v1/summary").json()
    assert summary["openAlerts"]["value"] == 11
    assert summary["queue"]["critical"] == 1

    search = client.get("/v1/search?q=12T").json()
    assert len(search["hits"]) >= 2

    me = client.get("/v1/me").json()
    assert me["advisoryOnly"] is True
    assert me["vitalCommandCapable"] is False

    draft = client.post(
        "/v1/work-orders/draft",
        json={
            "alertId": "alr-7f3c",
            "action": "Ballast clearing + drain rodding",
            "blockId": "RB-28",
        },
    )
    assert draft.status_code == 200
    assert draft.json()["status"] == "draft"
    assert draft.json()["advisoryOnly"] is True


def test_websocket_stream_heartbeat(client: TestClient) -> None:
    with client.websocket_connect("/v1/stream") as ws:
        msg = ws.receive_json()
        assert msg["type"] == "heartbeat"
        assert msg["at"].endswith("Z")
