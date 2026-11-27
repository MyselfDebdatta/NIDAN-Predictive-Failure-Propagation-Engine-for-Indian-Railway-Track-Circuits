"""Phase 4 tests: read-only SMMS sync, search precedents, W3C traceparent, and deployment."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth import clear_jwks_cache
from app.cli.smms_sync import main as smms_cli_main
from app.config import get_settings
from app.main import create_app
from tests.test_phase2_features import _generate_rsa_jwk, _mint_token


@pytest.fixture()
def dev_client() -> TestClient:
    settings = get_settings().model_copy(update={"data_mode": "fixture", "auth_mode": "dev"})
    application = create_app(settings=settings)
    with TestClient(application) as tc:
        yield tc


def test_smms_read_only_sync_updates_asset_provenance_and_search(dev_client: TestClient) -> None:
    payload = {
        "assets": [
            {
                "id": "ADRA/TC/99T",
                "divisionId": "ADRA",
                "name": "99T East Yard Loop",
                "route": "ADRA-BKSC Loop",
                "circuitType": "DC",
                "lengthM": 640,
                "installedOn": "2018-04-12",
                "codalLifeYears": 15,
                "relayModel": "QTA2",
                "supplyId": "BX-2",
                "cableId": "CBL-99",
                "relayRoomId": "ADRA-RR-1",
                "weatherCellId": "WC-ADRA-E",
                "provenance": "CRIS SMMS asset register v4",
            }
        ],
        "precedents": [
            {
                "id": "SMMS-2026-409",
                "assetId": "ADRA/TC/99T",
                "divisionId": "ADRA",
                "failureMode": "F1",
                "confirmedCause": "Waterlogged ballast bed at culvert 12",
                "occurredOn": "2026-06-18",
                "summary": "Shunt current dropped after 68 mm rain",
            }
        ],
    }

    resp = dev_client.post("/v1/ingest/smms-sync", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["assetsSynced"] == 1
    assert body["precedentsSynced"] == 1
    assert body["advisoryOnly"] is True

    # Synced asset is visible with SMMS provenance
    asset_resp = dev_client.get("/v1/assets/ADRA%2FTC%2F99T")
    assert asset_resp.status_code == 200
    assert asset_resp.json()["record"]["provenance"] == "CRIS SMMS asset register v4"
    assert asset_resp.json()["record"]["lengthM"] == 640

    # Precedent appears in federated search
    search_resp = dev_client.get("/v1/search?q=409")
    assert search_resp.status_code == 200
    hits = search_resp.json()["hits"]
    assert any(h["kind"] == "smms" and h["id"] == "SMMS-2026-409" for h in hits)

    # Metrics reflect SMMS sync counts
    metrics_text = dev_client.get("/metrics").text
    assert 'nidan_smms_sync_records_total{entity="asset"}' in metrics_text
    assert 'nidan_smms_sync_records_total{entity="precedent"}' in metrics_text


def test_smms_sync_requires_service_role_in_oidc_mode() -> None:
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

    payload = {
        "precedents": [
            {
                "id": "SMMS-2026-500",
                "divisionId": "ADRA",
                "confirmedCause": "Loose insulated rail joint bolt",
            }
        ]
    }
    with TestClient(application) as client:
        op_tok = _mint_token(pem, sub="op-1", role="operator", divisions=["ADRA"])
        denied = client.post(
            "/v1/ingest/smms-sync",
            headers={"Authorization": f"Bearer {op_tok}"},
            json=payload,
        )
        assert denied.status_code == 403

        svc_tok = _mint_token(pem, sub="smms-sync", role="service", divisions=["*"])
        allowed = client.post(
            "/v1/ingest/smms-sync",
            headers={"Authorization": f"Bearer {svc_tok}"},
            json=payload,
        )
        assert allowed.status_code == 200
        assert allowed.json()["precedentsSynced"] == 1


def test_w3c_traceparent_header_propagation(dev_client: TestClient) -> None:
    incoming = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    resp = dev_client.get("/healthz", headers={"traceparent": incoming})
    assert resp.status_code == 200
    tp = resp.headers.get("traceparent", "")
    assert re.match(r"^00-4bf92f3577b34da6a3ce929d0e0e4736-[0-9a-f]{16}-01$", tp)
    assert resp.headers.get("x-trace-id") == "4bf92f3577b34da6a3ce"


def test_smms_sync_cli_smoke(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("NIDAN_DATA_MODE", "fixture")
    get_settings.cache_clear()
    try:
        sample = {
            "precedents": [
                {
                    "id": "SMMS-CLI-1",
                    "divisionId": "ADRA",
                    "confirmedCause": "Corroded bootleg riser",
                }
            ]
        }
        in_file = tmp_path / "smms.json"
        in_file.write_text(json.dumps(sample), encoding="utf-8")
        exit_code = smms_cli_main(["--input", str(in_file)])
        assert exit_code == 0
        out = json.loads(capsys.readouterr().out)
        assert out["precedentsSynced"] == 1
        assert out["advisoryOnly"] is True
    finally:
        get_settings.cache_clear()
