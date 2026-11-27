"""Safety boundary tests enforcing NIDAN's strictly non-vital advisory guarantee."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


def test_no_vital_command_routes_registered() -> None:
    settings = get_settings().model_copy(update={"data_mode": "fixture"})
    application = create_app(settings=settings)
    banned = re.compile(
        r"/v1/(interlocking|signals|routes|points|track-circuits)/.*command",
        re.IGNORECASE,
    )
    paths = [getattr(route, "path", "") for route in application.routes]
    offenders = [p for p in paths if banned.search(p)]
    assert offenders == []


def test_vital_command_path_is_explicitly_rejected() -> None:
    settings = get_settings().model_copy(update={"data_mode": "fixture"})
    application = create_app(settings=settings)
    with TestClient(application) as client:
        resp = client.post("/v1/interlocking/ADRA-EI-1/command", json={"route": "R1"})
        assert resp.status_code == 403
        assert resp.json()["type"] == "urn:nidan:advisory-only"


def test_sql_schema_enforces_immutability_and_policy_rules() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "db" / "0001_init.sql"
    sql = schema_path.read_text(encoding="utf-8")
    for required_constraint in (
        "critical_rule",
        "warning_rule",
        "block_pairing",
        "deferral_complete",
        "smms_only_when_submitted",
        "risk_assessment_immutable",
        "alert_event_immutable",
        "audit_log_immutable",
        "field_observation_immutable",
    ):
        assert required_constraint in sql, (
            f"Missing safety invariant in 0001_init.sql: {required_constraint}"
        )


def test_phase4_smms_connector_and_deploy_preserve_non_vital_boundary() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    smms_src = (backend_dir / "app" / "connectors" / "smms.py").read_text(encoding="utf-8")
    assert "work_order_draft" not in smms_src
    assert "interlocking" not in smms_src.lower()

    netpol = (backend_dir / "deploy" / "k8s" / "networkpolicy.yaml").read_text(encoding="utf-8")
    assert "nidan-api-non-vital-egress" in netpol
    assert "5432" in netpol and "6379" in netpol

    realm = (backend_dir / "deploy" / "keycloak" / "nidan-realm.json").read_text(encoding="utf-8")
    assert '"division_ids"' in realm
    assert '"nidan-api"' in realm
