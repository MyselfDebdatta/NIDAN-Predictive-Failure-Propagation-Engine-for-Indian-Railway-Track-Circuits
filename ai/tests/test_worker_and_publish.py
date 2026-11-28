"""Phase A6 worker, atomic publish, idempotent replay, and report tests."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from app.config import get_settings as get_backend_settings
from app.main import create_app
from fastapi.testclient import TestClient

from nidan_ai.bench.generator import as_telemetry_samples, generate
from nidan_ai.config import Settings
from nidan_ai.worker.publish import PublishClient, PublishError, publish_snapshot
from nidan_ai.worker.run import build_synthetic_dry_run_payload, main, run_scoring_pipeline


def test_publish_batches_telemetry_retries_503_and_fails_closed_on_422() -> None:
    calls: list[tuple[str, str]] = []
    attempts = {"run": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/ingest/telemetry":
            body = json.loads(request.content)
            assert len(body["samples"]) <= 5000
            return httpx.Response(
                200,
                json={
                    "accepted": len(body["samples"]),
                    "deduplicated": 0,
                    "measuredCount": len(body["samples"]),
                    "interpolatedCount": 0,
                    "suspectCount": 0,
                    "generatedAt": "2026-07-14T00:00:00Z",
                },
            )
        if request.url.path == "/v1/ingest/model-run":
            attempts["run"] += 1
            if attempts["run"] == 1:
                return httpx.Response(503, json={"detail": "transient"})
            return httpx.Response(
                200,
                json={
                    "modelRunId": "run-1",
                    "snapshotId": "snap-1",
                    "assessmentsWritten": 3,
                    "alertsUpdated": 3,
                    "eventsPublished": ["alert.upserted:ADRA/TC/12T"],
                    "idempotentReplay": True,
                },
            )
        return httpx.Response(404)

    settings = Settings(
        api_base_url="http://testserver",
        auth_token="secret-token-never-logged",
        max_retries=2,
        retry_backoff_seconds=0.0,
    )
    payload = build_synthetic_dry_run_payload(scenario="monsoon-60d", seed=42)
    samples = [
        {
            "assetId": "ADRA/TC/12T",
            "signalKey": "relay_i",
            "observedAt": "2026-07-14T00:00:00Z",
            "value": 800.0,
            "quality": 0,
            "source": "nidan-bench",
        }
        for _ in range(5200)
    ]
    summary = publish_snapshot(
        payload=payload,
        samples=samples,
        settings=settings,
        transport=httpx.MockTransport(handler),
    )
    assert summary.batches_sent == 2
    assert summary.telemetry_accepted == 5200
    assert summary.idempotent_replay is True
    assert calls.count(("POST", "/v1/ingest/telemetry")) == 2
    assert calls.count(("POST", "/v1/ingest/model-run")) == 2

    # Verify fail-closed on 401 without leaking token
    def auth_fail(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "unauthorized"})

    with PublishClient(settings=settings, transport=httpx.MockTransport(auth_fail)) as client:
        with pytest.raises(PublishError) as exc_info:
            client.publish_model_run(payload)
        assert "secret-token-never-logged" not in str(exc_info.value)


class _SyncASGITransport(httpx.BaseTransport):
    """Wrap FastAPI's context-managed TestClient in a sync httpx.BaseTransport."""

    def __init__(self, app: Any) -> None:
        self._tc = TestClient(app)
        self._client = self._tc.__enter__()

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        resp = self._client.request(
            request.method,
            request.url.raw_path.decode("ascii"),
            headers=dict(request.headers),
            content=request.read(),
        )
        return httpx.Response(
            status_code=resp.status_code,
            headers=resp.headers,
            content=resp.content,
            request=request,
        )

    def close(self) -> None:
        self._tc.__exit__(None, None, None)


def test_end_to_end_pipeline_publishes_and_replays_idempotently_against_backend(tmp_path) -> None:
    backend_settings = get_backend_settings().model_copy(
        update={"data_mode": "fixture", "auth_mode": "dev"}
    )
    app = create_app(settings=backend_settings)
    transport = _SyncASGITransport(app)
    ai_settings = Settings(api_base_url="http://testserver", auth_mode="dev")

    try:
        with PublishClient(settings=ai_settings, transport=transport) as client:
            alerts_before = client.fetch_alerts()
            target_ids = [str(item["assetId"]) for item in alerts_before if item.get("assetId")]
            blocks = list(client.fetch_blocks().get("windows", []))

        report_dir = tmp_path / "report"
        payload, samples, metrics = run_scoring_pipeline(
            scenario="monsoon-60d",
            seed=42,
            report_dir=report_dir,
            target_asset_ids=target_ids,
            block_windows=blocks,
            include_samples=True,
            settings=ai_settings,
        )
        assert (report_dir / "model_card.md").exists()
        assert (report_dir / "metrics.json").exists()
        assert (report_dir / "calibration.svg").exists()
        assert metrics["assets_scored"] == float(len(payload["assessments"]))
        assert metrics["ece_mean"] <= 0.05

        # Publish a small recent sample slice + full atomic model run
        recent_samples = samples[-200:]
        first = publish_snapshot(
            payload=payload, samples=recent_samples, settings=ai_settings, transport=transport
        )
        assert first.idempotent_replay is False
        assert first.assessments_written == len(payload["assessments"])
        assert first.alerts_updated == len(payload["assessments"])
        assert any(ev.startswith("alert.upserted:") for ev in first.events_published)

        # Second run with identical snapshot + params must replay idempotently
        replay = publish_snapshot(
            payload=payload, samples=recent_samples, settings=ai_settings, transport=transport
        )
        assert replay.idempotent_replay is True
        assert replay.assessments_written == 0
        assert replay.model_run_id == first.model_run_id

        # Read back /v1/alerts and /v1/models/health from backend API to confirm live update
        with httpx.Client(transport=transport, base_url="http://testserver") as reader:
            health_resp = reader.get("/v1/models/health")
            assert health_resp.status_code == 200
            assert health_resp.json()["signature"] == payload["modelHealth"]["signature"]
            alerts_after = reader.get("/v1/alerts").json()
            assert len(alerts_after) >= len(payload["assessments"])
            by_asset = {a["assetId"]: a for a in alerts_after}
            published_by_asset = {a["assetId"]: a for a in payload["assessments"]}
            for aid, sent in published_by_asset.items():
                assert (
                    by_asset[aid]["explanation"]["physics"]["headline"]
                    == (sent["explanation"]["physics"]["headline"])
                )
                assert by_asset[aid]["ranking"]["calibratedRisk"] == pytest.approx(
                    sent["ranking"]["calibratedRisk"]
                )
    finally:
        transport.close()


def test_load_readonly_database_and_source_db_worker_pipeline(monkeypatch, tmp_path) -> None:
    import sys
    import types

    stream = generate("monsoon-60d", seed=42, days=15)
    samples = as_telemetry_samples(stream)
    db_rows = [
        (s["assetId"], s["signalKey"], s["observedAt"], s["value"], s["quality"]) for s in samples
    ]
    executed_sql: list[str] = []

    class _FakeCursor:
        def __enter__(self) -> _FakeCursor:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def execute(self, sql: str, _params: object = None) -> None:
            executed_sql.append(sql.strip().lower())

        def fetchall(self) -> list[tuple[object, ...]]:
            return db_rows

    class _FakeConn:
        def __enter__(self) -> _FakeConn:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def cursor(self) -> _FakeCursor:
            return _FakeCursor()

    from nidan_ai.config import get_settings

    fake_psycopg = types.ModuleType("psycopg")
    fake_psycopg.connect = lambda _dsn, autocommit=False: _FakeConn()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setenv("NIDAN_AI_READONLY_DATABASE_URL", "postgresql://readonly@db/nidan")
    get_settings.cache_clear()

    out_file = tmp_path / "db_out.json"
    try:
        rc = main(
            [
                "--source",
                "db",
                "--as-of",
                stream.timestamps[-1].isoformat(),
                "--out",
                str(out_file),
            ]
        )
    finally:
        get_settings.cache_clear()
    assert rc == 0
    assert executed_sql[0] == "set transaction read only"
    assert executed_sql[1].startswith("select asset_id, signal_key")
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(parsed["assessments"]) == len(stream.assets)


def test_worker_cli_rejects_conflicting_flags_and_writes_dry_run_reports(tmp_path) -> None:
    assert main(["--dry-run", "--publish"]) == 2
    out_file = tmp_path / "out.json"
    rep_dir = tmp_path / "rep"
    assert (
        main(
            [
                "--scenario",
                "monsoon-60d",
                "--seed",
                "42",
                "--dry-run",
                "--out",
                str(out_file),
                "--report-dir",
                str(rep_dir),
            ]
        )
        == 0
    )
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(parsed["assessments"]) == 12
    assert (rep_dir / "model_card.md").exists()


def test_worker_export_source_and_fail_closed_validation(tmp_path) -> None:
    stream = generate("monsoon-60d", seed=42, days=15)
    samples = as_telemetry_samples(stream)
    export_file = tmp_path / "export.json"
    export_file.write_text(json.dumps({"samples": samples}), encoding="utf-8")

    out_file = tmp_path / "export_out.json"
    rc = main(
        [
            "--source",
            "export",
            "--input",
            str(export_file),
            "--out",
            str(out_file),
        ]
    )
    assert rc == 0
    parsed = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(parsed["assessments"]) == len(stream.assets)

    with pytest.raises(ValueError, match="Unsupported --source"):
        run_scoring_pipeline(source="invalid-source")

    with pytest.raises(ValueError, match="--input is required when --source export"):
        run_scoring_pipeline(source="export")


@pytest.mark.slow
def test_500_circuit_cpu_scoring_under_60s() -> None:
    payload, _, metrics = run_scoring_pipeline(
        scenario="monsoon-60d",
        seed=42,
        limit=500,
    )
    assert len(payload["assessments"]) == 500
    assert metrics["scoring_s"] < 60.0
