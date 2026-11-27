"""Phase 2 tests: OIDC RBAC, division scoping, ETag/cursor pagination, /metrics, ingest."""

from __future__ import annotations

import base64
import time
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt

from app.auth import clear_jwks_cache
from app.config import get_settings
from app.database import DatabaseManager
from app.main import create_app


def _b64uint(val: int) -> str:
    raw = val.to_bytes((val.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _generate_rsa_jwk(kid: str = "nidan-test-key") -> tuple[str, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_numbers = private_key.public_key().public_numbers()
    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": kid,
        "n": _b64uint(pub_numbers.n),
        "e": _b64uint(pub_numbers.e),
    }
    return pem, {"keys": [jwk]}


def _mint_token(
    pem: str,
    *,
    sub: str = "user-1",
    role: str = "operator",
    divisions: list[str] | None = None,
    exp_offset: int = 300,
    aud: str = "nidan-api",
    iss: str = "https://sso.nidan.local/realms/nidan",
    kid: str = "nidan-test-key",
) -> str:
    now = int(time.time())
    claims = {
        "sub": sub,
        "name": f"Test {role}",
        "iss": iss,
        "aud": aud,
        "iat": now,
        "exp": now + exp_offset,
        "realm_access": {"roles": [role]},
        "division_ids": divisions if divisions is not None else ["ADRA"],
    }
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": kid})


@pytest.fixture()
def dev_client() -> TestClient:
    settings = get_settings().model_copy(update={"data_mode": "fixture", "auth_mode": "dev"})
    application = create_app(settings=settings)
    with TestClient(application) as tc:
        yield tc


@pytest.fixture()
def oidc_env():
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
    with TestClient(application) as tc:
        yield tc, pem


def test_alerts_cursor_pagination_and_etag_304(dev_client: TestClient) -> None:
    full = dev_client.get("/v1/alerts")
    assert full.status_code == 200
    assert len(full.json()) == 11
    etag = full.headers.get("etag")
    assert etag and etag.startswith('W/"')

    # Conditional request with matching ETag -> 304 Not Modified
    not_modified = dev_client.get("/v1/alerts", headers={"If-None-Match": etag})
    assert not_modified.status_code == 304
    assert not_modified.headers.get("etag") == etag

    # Cursor + limit pagination
    paged = dev_client.get("/v1/alerts?cursor=3&limit=2")
    assert paged.status_code == 200
    items = paged.json()
    assert len(items) == 2
    assert [item["policyRank"] for item in items] == [3, 4]


def test_blocks_and_models_etag_304(dev_client: TestClient) -> None:
    blocks = dev_client.get("/v1/blocks")
    assert blocks.status_code == 200
    b_etag = blocks.headers["etag"]
    assert dev_client.get("/v1/blocks", headers={"If-None-Match": b_etag}).status_code == 304

    models = dev_client.get("/v1/models/health")
    assert models.status_code == 200
    m_etag = models.headers["etag"]
    assert dev_client.get("/v1/models/health", headers={"If-None-Match": m_etag}).status_code == 304


def test_metrics_endpoint_reports_prometheus_counters(dev_client: TestClient) -> None:
    dev_client.get("/v1/alerts")
    resp = dev_client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    text = resp.text
    assert "nidan_http_requests_total" in text
    assert "nidan_websocket_connections_active" in text
    assert "nidan_field_observations_total" in text


def test_ingest_model_run_in_dev_mode(dev_client: TestClient) -> None:
    payload = {
        "snapshotAsOf": "2026-07-14T00:35:00Z",
        "snapshotWeek": 29,
        "snapshotLabel": "14 Jul 2026 · 00:35 IST",
        "codeVersion": "twin-0.3.2",
        "inputWatermark": "2026-07-14T00:34:00Z",
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
                "computedAt": "2026-07-14T00:35:00Z",
            }
        ],
    }
    resp = dev_client.post("/v1/ingest/model-run", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["assessmentsWritten"] == 1
    assert "alert.upserted:ADRA/TC/12T" in body["eventsPublished"]


def test_oidc_rejects_missing_expired_and_wrong_audience(oidc_env) -> None:
    client, pem = oidc_env

    # No token -> 401 RFC 9457
    no_auth = client.get("/v1/alerts")
    assert no_auth.status_code == 401
    assert no_auth.headers["content-type"].startswith("application/problem+json")

    # Expired token -> 401
    expired = _mint_token(pem, exp_offset=-60)
    exp_resp = client.get("/v1/alerts", headers={"Authorization": f"Bearer {expired}"})
    assert exp_resp.status_code == 401
    assert exp_resp.json()["type"] == "urn:nidan:token-expired"

    # Wrong audience -> 401
    wrong_aud = _mint_token(pem, aud="other-app")
    aud_resp = client.get("/v1/alerts", headers={"Authorization": f"Bearer {wrong_aud}"})
    assert aud_resp.status_code == 401


def test_oidc_division_scoping_and_rbac_roles(oidc_env) -> None:
    client, pem = oidc_env

    # Operator scoped strictly to BKSC division
    bksc_op = _mint_token(pem, sub="op-bksc", role="operator", divisions=["BKSC"])
    headers = {"Authorization": f"Bearer {bksc_op}"}

    me = client.get("/v1/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["userId"] == "op-bksc"
    assert me.json()["divisions"] == ["BKSC"]

    alerts = client.get("/v1/alerts", headers=headers)
    assert alerts.status_code == 200
    assert all(a["division"] == "BKSC" for a in alerts.json())
    assert len(alerts.json()) == 1

    # Out-of-scope division read -> 403
    forbidden_alert = client.get("/v1/alerts/alr-7f3c", headers=headers)
    assert forbidden_alert.status_code == 403
    assert forbidden_alert.json()["type"] == "urn:nidan:forbidden-division"

    forbidden_asset = client.get("/v1/assets/ADRA%2FTC%2F12T", headers=headers)
    assert forbidden_asset.status_code == 403

    # Operator cannot call service-only ingest endpoint -> 403
    ingest_denied = client.post(
        "/v1/ingest/model-run",
        headers=headers,
        json={
            "snapshotAsOf": "2026-07-14T00:35:00Z",
            "snapshotWeek": 29,
            "snapshotLabel": "14 Jul 2026 · 00:35 IST",
            "codeVersion": "twin-0.3.2",
            "inputWatermark": "2026-07-14T00:34:00Z",
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
                    "computedAt": "2026-07-14T00:35:00Z",
                }
            ],
        },
    )
    assert ingest_denied.status_code == 403

    # Maintainer cannot acknowledge alerts -> 403
    maintainer_tok = _mint_token(pem, sub="esm-adra", role="maintainer", divisions=["ADRA"])
    ack_denied = client.post(
        "/v1/alerts/alr-7f3c/acknowledge",
        headers={"Authorization": f"Bearer {maintainer_tok}"},
    )
    assert ack_denied.status_code == 403
    assert ack_denied.json()["type"] == "urn:nidan:forbidden"

    # Service token can call /v1/ingest/model-run -> 200
    service_tok = _mint_token(pem, sub="model-runner", role="service", divisions=["*"])
    ingest_ok = client.post(
        "/v1/ingest/model-run",
        headers={"Authorization": f"Bearer {service_tok}"},
        json=ingest_denied_payload(),
    )
    assert ingest_ok.status_code == 200


def ingest_denied_payload() -> dict[str, Any]:
    return {
        "snapshotAsOf": "2026-07-14T00:35:00Z",
        "snapshotWeek": 29,
        "snapshotLabel": "14 Jul 2026 · 00:35 IST",
        "codeVersion": "twin-0.3.2",
        "inputWatermark": "2026-07-14T00:34:00Z",
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
                "computedAt": "2026-07-14T00:35:00Z",
            }
        ],
    }


async def test_database_manager_require_postgres_raises_when_unreachable() -> None:
    db = DatabaseManager(
        "postgresql://nidan:wrong@127.0.0.1:59999/nidan",
        "redis://127.0.0.1:59998/0",
        data_mode="postgres",
        require_postgres=True,
    )
    with pytest.raises(RuntimeError, match="NIDAN_REQUIRE_POSTGRES=true"):
        await db.connect()
