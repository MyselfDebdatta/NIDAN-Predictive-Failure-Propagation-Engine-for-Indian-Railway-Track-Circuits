"""Live PostgreSQL integration tests for Phase 2.

Requires a running Postgres 16 instance with 0001_init.sql + seed.sql applied.

Run locally:
    cd backend
    docker compose up -d postgres redis
    pytest -v -m integration

In CI: the backend-ci job spins up a postgres:16-alpine service container and
runs these automatically alongside the fixture-based contract tests.

Environment variable required:
    NIDAN_TEST_DATABASE_URL  — defaults to the same DATABASE_URL in .env /
                               Settings but can be overridden for the test PG.
"""

from __future__ import annotations

import os
import uuid

import asyncpg
import pytest

INTEGRATION_DB_URL = os.environ.get(
    "NIDAN_TEST_DATABASE_URL",
    "postgresql://nidan:nidan_dev_password@localhost:5432/nidan",
)


# ---------------------------------------------------------------------------
# Shared pool fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
async def pg_pool():
    """Function-scoped asyncpg pool for live Postgres tests."""
    try:
        pool = await asyncpg.create_pool(dsn=INTEGRATION_DB_URL, min_size=1, max_size=4)
    except Exception as exc:
        pytest.skip(f"Postgres unavailable at {INTEGRATION_DB_URL}: {exc}")
    yield pool
    await pool.close()


# ---------------------------------------------------------------------------
# Schema verification
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_schema_tables_present(pg_pool: asyncpg.Pool) -> None:
    """All 0001_init.sql tables must exist in the live database."""
    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'public'
            order by table_name
            """
        )
    names = {r["table_name"] for r in rows}
    required = {
        "alert",
        "alert_event",
        "app_user",
        "asset",
        "asset_record_source",
        "audit_log",
        "block_job",
        "block_job_asset",
        "block_window",
        "cluster",
        "division",
        "field_observation",
        "field_task",
        "model_health_snapshot",
        "model_registry",
        "model_run",
        "relay_room",
        "risk_assessment",
        "signal_catalog",
        "snapshot",
        "telemetry_reading",
        "weather_cell",
        "work_order_draft",
    }
    missing = required - names
    assert not missing, f"Missing tables in live DB: {missing}"


@pytest.mark.integration
async def test_immutability_trigger_risk_assessment(pg_pool: asyncpg.Pool) -> None:
    """risk_assessment rows must be append-only (UPDATE must raise restrict_violation)."""
    async with pg_pool.acquire() as conn:
        # Grab any existing risk_assessment id
        row = await conn.fetchrow("select id from risk_assessment limit 1")
        if row is None:
            pytest.skip("No risk_assessment rows in test database.")
        ra_id = row["id"]
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await conn.execute(
                "update risk_assessment set policy_rank = policy_rank where id = $1",
                ra_id,
            )


@pytest.mark.integration
async def test_immutability_trigger_audit_log(pg_pool: asyncpg.Pool) -> None:
    """audit_log rows must be append-only (DELETE must raise restrict_violation)."""
    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            insert into audit_log (action, entity_type, entity_id)
            values ('integration-test', 'test', 'immut-check')
            """
        )
        row = await conn.fetchrow(
            "select id from audit_log where entity_id = 'immut-check' limit 1"
        )
        with pytest.raises(asyncpg.exceptions.RestrictViolationError):
            await conn.execute("delete from audit_log where id = $1", row["id"])


@pytest.mark.integration
async def test_policy_check_critical_rule(pg_pool: asyncpg.Pool) -> None:
    """critical_rule CHECK: level='critical' requires h24>0.5 or cluster_root=true."""
    async with pg_pool.acquire() as conn:
        # Get a valid snapshot + model_run + asset to reference
        snapshot_id = await conn.fetchval("select id from snapshot limit 1")
        asset_id = await conn.fetchval("select id from asset limit 1")
        if not snapshot_id or not asset_id:
            pytest.skip("No seed data in test database.")
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                insert into risk_assessment (
                  asset_id, snapshot_id, policy_version, level, policy_rank,
                  persistence, h24, h72, h7d, ece_zone,
                  p10_days, median_days, p90_days, rul_coverage, held_out_n,
                  likely_modes, mode_probability, mode_set_coverage,
                  data_trust_score, cluster_root, explanation, ranking,
                  model_versions, computed_at
                ) values (
                  $1, $2, 'policy-test', 'critical', 999,
                  1, 0.3, 0.3, 0.3, 0.05,
                  5, 10, 20, 0.88, 100,
                  ARRAY['F1'], 0.9, 0.9,
                  0.9, false, '{}', '{}',
                  '{}', now()
                )
                """,
                asset_id,
                snapshot_id,
            )


@pytest.mark.integration
async def test_policy_check_warning_rule(pg_pool: asyncpg.Pool) -> None:
    """warning_rule CHECK: level='warning' requires h72>0.3."""
    async with pg_pool.acquire() as conn:
        snapshot_id = await conn.fetchval("select id from snapshot limit 1")
        asset_id = await conn.fetchval("select id from asset limit 1")
        if not snapshot_id or not asset_id:
            pytest.skip("No seed data in test database.")
        with pytest.raises(asyncpg.exceptions.CheckViolationError):
            await conn.execute(
                """
                insert into risk_assessment (
                  asset_id, snapshot_id, policy_version, level, policy_rank,
                  persistence, h24, h72, h7d, ece_zone,
                  p10_days, median_days, p90_days, rul_coverage, held_out_n,
                  likely_modes, mode_probability, mode_set_coverage,
                  data_trust_score, cluster_root, explanation, ranking,
                  model_versions, computed_at
                ) values (
                  $1, $2, 'policy-test', 'warning', 998,
                  1, 0.1, 0.1, 0.3, 0.05,
                  5, 10, 20, 0.88, 100,
                  ARRAY['F2'], 0.8, 0.9,
                  0.9, false, '{}', '{}',
                  '{}', now()
                )
                """,
                asset_id,
                snapshot_id,
            )


@pytest.mark.integration
async def test_field_observation_idempotency_key_unique(pg_pool: asyncpg.Pool) -> None:
    """field_observation.idempotency_key must be UNIQUE (second insert raises error)."""
    async with pg_pool.acquire() as conn:
        task_id = await conn.fetchval("select id from field_task limit 1")
        asset_id = await conn.fetchval("select id from asset limit 1")
        if not task_id or not asset_id:
            pytest.skip("No seed data in test database.")
        key = str(uuid.uuid4())
        await conn.execute(
            """
            insert into field_observation (task_id, asset_id, idempotency_key, finding, note)
            values ($1, $2, $3, 'confirmed', 'integration test')
            """,
            task_id,
            asset_id,
            key,
        )
        with pytest.raises(asyncpg.exceptions.UniqueViolationError):
            await conn.execute(
                """
                insert into field_observation (task_id, asset_id, idempotency_key, finding, note)
                values ($1, $2, $3, 'not-found', 'duplicate attempt')
                """,
                task_id,
                asset_id,
                key,
            )


# ---------------------------------------------------------------------------
# PostgresRepository round-trip
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_postgres_repo_list_alerts(pg_pool: asyncpg.Pool) -> None:
    """PostgresRepository.list_alerts returns correctly ordered advisory alerts."""
    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    alerts = await repo.list_alerts()
    assert len(alerts) >= 1
    ranks = [a["policyRank"] for a in alerts]
    assert ranks == sorted(ranks), "Alerts must be ordered by policyRank ascending"
    for alert in alerts:
        assert "assetId" in alert
        assert "level" in alert
        assert alert["level"] in {"critical", "warning", "watch"}


@pytest.mark.integration
async def test_postgres_repo_field_observations_idempotency(pg_pool: asyncpg.Pool) -> None:
    """PostgresRepository: submit→replay returns replayed=True; conflict returns 409 body."""
    from app.middleware import ApiProblemException
    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    task_id = await pg_pool.fetchval("select id from field_task limit 1")
    if not task_id:
        pytest.skip("No field_task rows in test database.")

    key = str(uuid.uuid4())
    payload = {
        "taskId": task_id,
        "finding": "confirmed",
        "measurements": {"relayCurrent": "120", "ballastConductance": "1.5"},
        "note": "Integration test observation",
        "createdAt": "2026-11-27T00:00:00Z",
    }
    # First submission
    result, replayed = await repo.submit_observation(idempotency_key=key, payload=payload)
    assert replayed is False
    assert result["queued"] is True
    assert result["replayed"] is False

    # Identical replay → 200 replayed
    result2, replayed2 = await repo.submit_observation(idempotency_key=key, payload=payload)
    assert replayed2 is True
    assert result2["replayed"] is True
    assert result2["receipt"] == result["receipt"]

    # Divergent replay → 409 ApiProblemException
    conflict_payload = {**payload, "finding": "not-found"}
    with pytest.raises(ApiProblemException) as exc_info:
        await repo.submit_observation(idempotency_key=key, payload=conflict_payload)
    assert exc_info.value.status == 409


@pytest.mark.integration
async def test_postgres_repo_acknowledge_alert(pg_pool: asyncpg.Pool) -> None:
    """PostgresRepository.acknowledge_alert appends an alert_event row."""
    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    alert_id = await pg_pool.fetchval("select id from alert where status = 'open' limit 1")
    if not alert_id:
        pytest.skip("No open alerts in test database.")
    result = await repo.acknowledge_alert(alert_id)
    assert result["acknowledged"] is True
    # Verify alert_event row was inserted
    event_count = await pg_pool.fetchval(
        "select count(*) from alert_event where alert_id = $1 and kind = 'acknowledged'",
        alert_id,
    )
    assert event_count >= 1


@pytest.mark.integration
async def test_redis_stream_hub_publish(pg_pool: asyncpg.Pool) -> None:
    """StreamHub.publish sends to Redis channel (or in-process when Redis absent)."""
    import asyncio

    import redis.asyncio as aioredis

    from app.services.stream_hub import StreamHub

    redis_url = os.environ.get("NIDAN_TEST_REDIS_URL", "redis://localhost:6379/0")
    try:
        client = aioredis.from_url(redis_url, decode_responses=True)
        await client.ping()
    except Exception:
        pytest.skip("Redis unavailable; skipping StreamHub Redis fan-out test.")

    hub = StreamHub(redis_client=client)
    pubsub = client.pubsub()
    await pubsub.subscribe("nidan:stream:events")

    # Give the subscription a moment to register
    await asyncio.sleep(0.1)

    test_event = {"type": "integration.test", "id": str(uuid.uuid4())}
    await hub.publish(test_event)

    msg = None
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 2.0
    while loop.time() < deadline:
        msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=0.25)
        if msg is not None:
            break
        await asyncio.sleep(0.05)

    await pubsub.unsubscribe("nidan:stream:events")
    await client.aclose()

    assert msg is not None, "Expected a message on nidan:stream:events channel"
    import json

    received = json.loads(msg["data"])
    assert received["type"] == "integration.test"


@pytest.mark.integration
async def test_postgres_repo_publish_model_run(pg_pool: asyncpg.Pool) -> None:
    """PostgresRepository.publish_model_run inserts model_run, snapshot, and risk_assessment."""
    from datetime import UTC, datetime

    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    asset_id = await pg_pool.fetchval("select asset_id from alert where status = 'open' limit 1")
    if not asset_id:
        pytest.skip("No open alerts in test database.")

    ts = datetime(2026, 11, 27, 12, 0, 0, tzinfo=UTC)
    result = await repo.publish_model_run(
        {
            "snapshotAsOf": ts,
            "snapshotWeek": 48,
            "snapshotLabel": "27 Nov 2026 · 17:30 IST",
            "codeVersion": "integration-test-0.2.0",
            "inputWatermark": ts,
            "assessments": [
                {
                    "assetId": asset_id,
                    "level": "watch",
                    "policyRank": 2,
                    "persistence": 2,
                    "h24": 0.05,
                    "h72": 0.14,
                    "h7d": 0.25,
                    "eceZone": 0.04,
                    "p10Days": 8,
                    "medianDays": 15,
                    "p90Days": 26,
                    "rulCoverage": 0.9,
                    "heldOutN": 3180,
                    "likelyModes": ["F1"],
                    "modeProbability": 0.72,
                    "modeSetCoverage": 0.91,
                    "dataTrustScore": 0.97,
                    "computedAt": ts,
                }
            ],
        }
    )
    assert result["assessments_written"] == 1
    assert asset_id in result["updated_asset_ids"]


@pytest.mark.integration
async def test_postgres_repo_ingest_telemetry_deduplication(pg_pool: asyncpg.Pool) -> None:
    """PostgresRepository.ingest_telemetry persists QC readings and deduplicates replays."""
    from datetime import UTC, datetime

    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    asset_id = await pg_pool.fetchval("select id from asset limit 1")
    if not asset_id:
        pytest.skip("No asset rows in test database.")

    ts = datetime(2026, 11, 27, 14, 0, 0, tzinfo=UTC)
    samples = [
        {
            "assetId": asset_id,
            "signalKey": "relay_i",
            "observedAt": ts,
            "value": 122.5,
            "quality": 0,
            "source": "integration-test",
        }
    ]
    first = await repo.ingest_telemetry(samples)
    assert first == {"accepted": 1, "deduplicated": 0}

    second = await repo.ingest_telemetry(samples)
    assert second == {"accepted": 0, "deduplicated": 1}


@pytest.mark.integration
async def test_postgres_repo_model_run_idempotency_and_fail_closed(pg_pool: asyncpg.Pool) -> None:
    """Model-run replay is idempotent on (snapshot_id, code_version, params_hash)."""
    from datetime import UTC, datetime

    from app.middleware import ApiProblemException
    from app.services.postgres_repo import PostgresRepository

    repo = PostgresRepository(pg_pool)
    asset_id = await pg_pool.fetchval("select asset_id from alert where status = 'open' limit 1")
    if not asset_id:
        pytest.skip("No open alerts in test database.")

    ts = datetime(2026, 11, 27, 15, 30, 0, tzinfo=UTC)
    payload = {
        "snapshotAsOf": ts,
        "snapshotWeek": 48,
        "snapshotLabel": "27 Nov 2026 · 21:00 IST",
        "codeVersion": "phase3-idem-0.3.0",
        "params": {"alpha": 0.1},
        "inputWatermark": ts,
        "assessments": [
            {
                "assetId": asset_id,
                "level": "watch",
                "policyRank": 2,
                "persistence": 2,
                "h24": 0.05,
                "h72": 0.14,
                "h7d": 0.25,
                "eceZone": 0.04,
                "p10Days": 8,
                "medianDays": 15,
                "p90Days": 26,
                "rulCoverage": 0.9,
                "heldOutN": 3180,
                "likelyModes": ["F1"],
                "modeProbability": 0.72,
                "modeSetCoverage": 0.91,
                "dataTrustScore": 0.97,
                "computedAt": ts,
            }
        ],
    }

    first = await repo.publish_model_run(payload)
    assert first["idempotent_replay"] is False
    assert first["assessments_written"] == 1

    replay = await repo.publish_model_run(payload)
    assert replay["idempotent_replay"] is True
    assert replay["assessments_written"] == 0
    assert replay["model_run_id"] == first["model_run_id"]

    # Violating critical_rule must fail closed (422) and insert failed model_run
    bad_ts = datetime(2026, 11, 27, 16, 0, 0, tzinfo=UTC)
    bad_payload = {
        **payload,
        "snapshotAsOf": bad_ts,
        "codeVersion": "phase3-fail-0.3.0",
        "assessments": [{**payload["assessments"][0], "level": "critical", "h24": 0.2}],
    }
    with pytest.raises(ApiProblemException) as exc_info:
        await repo.publish_model_run(bad_payload)
    assert exc_info.value.status == 422

    failed_count = await pg_pool.fetchval(
        "select count(*) from model_run "
        "where code_version = 'phase3-fail-0.3.0' and status = 'failed'"
    )
    assert failed_count >= 1
