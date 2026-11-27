"""PostgreSQL repository backed by asyncpg and schema 0001_init.sql."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

import asyncpg

from app.middleware import ApiProblemException
from app.models.common import ModelVersions, utc_now_iso
from app.services.memory_repo import compute_params_hash


def _json_val(val: Any) -> Any:
    if isinstance(val, str):
        return json.loads(val)
    return val


def _row_to_alert(row: asyncpg.Record, snapshot_as_of: Any) -> dict[str, Any]:
    """Map joined alert + risk_assessment + asset + block_window row to Alert dict."""
    block: dict[str, Any] | None = None
    if row["block_window_id"] is not None:
        block = {
            "window": {
                "id": row["block_window_id"],
                "date": row["bw_service_date"].isoformat(),
                "start": row["bw_starts_at"].strftime("%H:%M"),
                "end": row["bw_ends_at"].strftime("%H:%M"),
                "durationMin": int(row["bw_duration_min"]),
                "kind": row["bw_kind"],
            },
            "fit": row["block_fit"],
            "minutes": int(row["block_minutes"]),
        }

    age_minutes = max(0, int((snapshot_as_of - row["opened_at"]).total_seconds() // 60))
    alert_dict: dict[str, Any] = {
        "id": row["alert_id"],
        "assetId": row["asset_id"],
        "assetName": row["asset_name"],
        "route": row["route"],
        "division": row["division_id"],
        "level": row["level"],
        "policyRank": int(row["policy_rank"]),
        "persistence": int(row["persistence"]),
        "risk": {
            "h24": float(row["h24"]),
            "h72": float(row["h72"]),
            "h7d": float(row["h7d"]),
            "eceZone": float(row["ece_zone"]),
        },
        "rul": {
            "p10Days": int(row["p10_days"]),
            "medianDays": int(row["median_days"]),
            "p90Days": int(row["p90_days"]),
            "coverage": float(row["rul_coverage"]),
            "heldOutN": int(row["held_out_n"]),
        },
        "likelyModes": list(row["likely_modes"]),
        "modeProbability": float(row["mode_probability"]),
        "modeSetCoverage": float(row["mode_set_coverage"]),
        "clusterId": row["cluster_id"],
        "dataTrust": {
            "score": float(row["data_trust_score"]),
            "flags": list(row["data_trust_flags"] or []),
        },
        "block": block,
        "explanation": _json_val(row["explanation"]),
        "ranking": _json_val(row["ranking"]),
        "ageMinutes": age_minutes,
        "modelVersions": _json_val(row["model_versions"]),
    }
    if row["status"] == "acknowledged":
        alert_dict["acknowledged"] = True
    if row["status"] == "deferred" and row["deferral_reason"] and row["deferral_review_date"]:
        alert_dict["deferral"] = {
            "reason": row["deferral_reason"],
            "reviewDate": row["deferral_review_date"].isoformat(),
        }
    return alert_dict


_ALERT_SELECT_SQL = """
select
  a.id as alert_id,
  a.asset_id,
  a.cluster_id,
  a.opened_at,
  a.status::text as status,
  a.deferral_reason,
  a.deferral_review_date,
  ast.name as asset_name,
  ast.route,
  ast.division_id,
  ra.level::text as level,
  ra.policy_rank,
  ra.persistence,
  ra.h24,
  ra.h72,
  ra.h7d,
  ra.ece_zone,
  ra.p10_days,
  ra.median_days,
  ra.p90_days,
  ra.rul_coverage,
  ra.held_out_n,
  ra.likely_modes,
  ra.mode_probability,
  ra.mode_set_coverage,
  ra.data_trust_score,
  ra.data_trust_flags,
  ra.block_window_id,
  ra.block_fit::text as block_fit,
  ra.block_minutes,
  ra.explanation,
  ra.ranking,
  ra.model_versions,
  bw.service_date as bw_service_date,
  bw.starts_at as bw_starts_at,
  bw.ends_at as bw_ends_at,
  bw.duration_min as bw_duration_min,
  bw.kind::text as bw_kind
from alert a
join risk_assessment ra on ra.id = a.current_assessment_id
join asset ast on ast.id = a.asset_id
left join block_window bw on bw.id = ra.block_window_id
"""


class PostgresRepository:
    """Async PostgreSQL implementation of NidanRepository."""

    def __init__(self, pool: asyncpg.Pool) -> None:
        self.pool = pool

    def _model_versions(self) -> dict[str, str]:
        return ModelVersions().model_dump(by_alias=True)

    async def _latest_snapshot_as_of(self, conn: asyncpg.Connection) -> Any:
        val = await conn.fetchval("select as_of from snapshot order by as_of desc limit 1")
        return val

    async def list_alerts(self) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            as_of = await self._latest_snapshot_as_of(conn)
            rows = await conn.fetch(f"{_ALERT_SELECT_SQL} order by ra.policy_rank asc")
            return [_row_to_alert(row, as_of or row["opened_at"]) for row in rows]

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            as_of = await self._latest_snapshot_as_of(conn)
            row = await conn.fetchrow(
                f"{_ALERT_SELECT_SQL} where a.id = $1 or a.asset_id = $1 limit 1",
                alert_id,
            )
            if row is None:
                return None
            alert_dict = _row_to_alert(row, as_of or row["opened_at"])
            alert_dict["generatedAt"] = utc_now_iso()
            return alert_dict

    async def _resolve_actor_id(
        self, conn: asyncpg.Connection, actor_sub: str | None
    ) -> str | None:
        if not actor_sub:
            return None
        try:
            parsed = str(uuid.UUID(actor_sub))
        except ValueError:
            return None
        exists = await conn.fetchval("select id from app_user where id = $1", parsed)
        return str(exists) if exists else None

    async def _insert_audit_log(
        self,
        conn: asyncpg.Connection,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> None:
        actor_id = await self._resolve_actor_id(conn, actor_sub)
        enriched_after = dict(after or {})
        if actor_sub:
            enriched_after.setdefault("actorSub", actor_sub)
        await conn.execute(
            """
            insert into audit_log
              (actor_id, actor_role, action, entity_type, entity_id, before, after, request_id)
            values ($1, $2::user_role, $3, $4, $5, $6::jsonb, $7::jsonb, $8)
            """,
            actor_id,
            actor_role,
            action,
            entity_type,
            entity_id,
            json.dumps(before) if before is not None else None,
            json.dumps(enriched_after) if enriched_after else None,
            request_id,
        )

    async def acknowledge_alert(
        self,
        alert_id: str,
        *,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "select id, status::text as status from alert "
                    "where id = $1 or asset_id = $1 limit 1",
                    alert_id,
                )
                if row is None:
                    return None
                resolved_id = row["id"]
                actor_id = await self._resolve_actor_id(conn, actor_sub)
                await conn.execute(
                    "update alert set status = 'acknowledged'::alert_status where id = $1",
                    resolved_id,
                )
                ev_payload: dict[str, Any] = {"previousStatus": row["status"]}
                if actor_sub:
                    ev_payload["actorSub"] = actor_sub
                await conn.execute(
                    "insert into alert_event (alert_id, kind, actor_id, payload) "
                    "values ($1, 'acknowledged', $2, $3::jsonb)",
                    resolved_id,
                    actor_id,
                    json.dumps(ev_payload),
                )
                await self._insert_audit_log(
                    conn,
                    action="alert.acknowledged",
                    entity_type="alert",
                    entity_id=resolved_id,
                    before={"status": row["status"]},
                    after={"status": "acknowledged"},
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    request_id=request_id,
                )
                return {
                    "acknowledged": True,
                    "alertId": resolved_id,
                    "status": "acknowledged",
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }

    async def defer_alert(
        self,
        alert_id: str,
        *,
        reason: str,
        review_date: str,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    "select id, status::text as status from alert "
                    "where id = $1 or asset_id = $1 limit 1",
                    alert_id,
                )
                if row is None:
                    return None
                resolved_id = row["id"]
                actor_id = await self._resolve_actor_id(conn, actor_sub)
                clean_reason = reason.strip()
                await conn.execute(
                    "update alert set status = 'deferred'::alert_status, "
                    "deferral_reason = $2, deferral_review_date = $3::date where id = $1",
                    resolved_id,
                    clean_reason,
                    review_date,
                )
                deferral = {"reason": clean_reason, "reviewDate": review_date}
                ev_payload = dict(deferral)
                if actor_sub:
                    ev_payload["actorSub"] = actor_sub
                await conn.execute(
                    "insert into alert_event (alert_id, kind, actor_id, payload) "
                    "values ($1, 'deferred', $2, $3::jsonb)",
                    resolved_id,
                    actor_id,
                    json.dumps(ev_payload),
                )
                await self._insert_audit_log(
                    conn,
                    action="alert.deferred",
                    entity_type="alert",
                    entity_id=resolved_id,
                    before={"status": row["status"]},
                    after={"status": "deferred", **deferral},
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    request_id=request_id,
                )
                return {
                    "deferred": True,
                    "alertId": resolved_id,
                    "status": "deferred",
                    "deferral": deferral,
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }

    async def get_asset_detail(self, asset_id: str) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            rec_row = await conn.fetchrow(
                """
                select
                  ast.*,
                  src.provenance
                from asset ast
                left join asset_record_source src on src.asset_id = ast.id
                where ast.id = $1
                """,
                asset_id,
            )
            if rec_row is None:
                return None

            as_of = await self._latest_snapshot_as_of(conn)
            alert_row = await conn.fetchrow(
                f"{_ALERT_SELECT_SQL} where a.asset_id = $1 order by a.opened_at desc limit 1",
                asset_id,
            )
            alert_dict = (
                _row_to_alert(alert_row, as_of or alert_row["opened_at"])
                if alert_row is not None
                else None
            )

            tel_rows = await conn.fetch(
                """
                select
                  tr.signal_key,
                  sc.label,
                  sc.unit,
                  sc.baseline,
                  sc.normal_band,
                  tr.value
                from telemetry_reading tr
                join signal_catalog sc on sc.key = tr.signal_key
                where tr.asset_id = $1
                order by tr.signal_key, tr.observed_at asc
                """,
                asset_id,
            )
            series_map: dict[str, dict[str, Any]] = {}
            for r in tel_rows:
                key = r["signal_key"]
                if key not in series_map:
                    series_map[key] = {
                        "key": key,
                        "label": r["label"],
                        "unit": r["unit"],
                        "baseline": float(r["baseline"]),
                        "normalBand": r["normal_band"],
                        "values": [],
                    }
                series_map[key]["values"].append(float(r["value"]))

            modes = _derive_modes_from_alert(alert_dict)
            record = {
                "id": rec_row["id"],
                "lengthM": int(rec_row["length_m"]),
                "circuitType": rec_row["circuit_type"],
                "installed": rec_row["installed_on"].isoformat() if rec_row["installed_on"] else "",
                "codalLifeYears": int(rec_row["codal_life_years"] or 15),
                "relay": rec_row["relay_model"] or "",
                "supply": rec_row["supply_id"] or "",
                "cable": rec_row["cable_id"] or "",
                "relayRoom": rec_row["relay_room_id"] or "",
                "weatherCell": rec_row["weather_cell_id"] or "",
                "provenance": rec_row["provenance"] or "SMMS asset register",
            }
            return {
                "alert": alert_dict,
                "record": record,
                "signals": list(series_map.values()),
                "modes": modes,
                "modelVersions": self._model_versions(),
                "generatedAt": utc_now_iso(),
            }

    async def get_blocks(self) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            win_rows = await conn.fetch(
                "select id, service_date, starts_at, ends_at, duration_min, kind::text as kind "
                "from block_window order by service_date asc, starts_at asc"
            )
            job_rows = await conn.fetch(
                """
                select
                  bj.id,
                  bj.title,
                  bj.block_window_id,
                  bj.duration_min,
                  bj.fit::text as fit,
                  bj.crew,
                  coalesce(
                    array_agg(bja.asset_id order by bja.asset_id)
                      filter (where bja.asset_id is not null),
                    '{}'
                  ) as assets
                from block_job bj
                left join block_job_asset bja on bja.job_id = bj.id
                group by bj.id
                order by bj.id asc
                """
            )
            windows = [
                {
                    "id": w["id"],
                    "date": w["service_date"].isoformat(),
                    "start": w["starts_at"].strftime("%H:%M"),
                    "end": w["ends_at"].strftime("%H:%M"),
                    "durationMin": int(w["duration_min"]),
                    "kind": w["kind"],
                }
                for w in win_rows
            ]
            jobs = [
                {
                    "id": j["id"],
                    "title": j["title"],
                    "assets": list(j["assets"]),
                    "blockId": j["block_window_id"],
                    "durationMin": int(j["duration_min"]),
                    "fit": j["fit"],
                    "crew": j["crew"],
                }
                for j in job_rows
            ]
            return {
                "windows": windows,
                "jobs": jobs,
                "modelVersions": self._model_versions(),
                "generatedAt": utc_now_iso(),
            }

    async def get_clusters(self) -> list[dict[str, Any]]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select
                  c.*,
                  coalesce(
                    array_agg(a.asset_id order by ra.policy_rank asc)
                      filter (where a.asset_id is not null),
                    '{}'
                  ) as members
                from cluster c
                left join alert a on a.cluster_id = c.id
                left join risk_assessment ra on ra.id = a.current_assessment_id
                group by c.id
                order by c.id asc
                """
            )
            clusters: list[dict[str, Any]] = []
            for r in rows:
                members = list(r["members"])
                item: dict[str, Any] = {
                    "id": r["id"],
                    "title": r["title"],
                    "state": r["state"],
                    "summary": r["summary"],
                    "alertsFolded": len(members),
                    "decisions": _json_val(r["decisions"]),
                    "savedBlockHours": float(r["saved_block_hours"]),
                    "weatherCell": r["weather_cell_id"] or "",
                    "sharedEdges": _json_val(r["shared_edges"]),
                    "members": members,
                }
                if r["predicted_cascade_asset"]:
                    item["predictedCascade"] = {
                        "assetId": r["predicted_cascade_asset"],
                        "inDays": {
                            "min": int(r["cascade_min_days"]),
                            "max": int(r["cascade_max_days"]),
                        },
                    }
                clusters.append(item)
            return clusters

    async def merge_cluster(
        self,
        cluster_id: str,
        alert_ids: list[str],
        *,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                exists = await conn.fetchval("select 1 from cluster where id = $1", cluster_id)
                if not exists:
                    return None
                rows = await conn.fetch(
                    "update alert set cluster_id = $1 "
                    "where id = any($2::text[]) or asset_id = any($2::text[]) returning id",
                    cluster_id,
                    alert_ids,
                )
                merged = [r["id"] for r in rows]
                if not merged:
                    raise ApiProblemException(
                        status=404,
                        title="No matching alerts",
                        detail="None of the supplied alertIds exist.",
                        error_type="urn:nidan:not-found",
                    )
                await self._insert_audit_log(
                    conn,
                    action="cluster.merged",
                    entity_type="cluster",
                    entity_id=cluster_id,
                    after={"mergedAlertIds": merged},
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    request_id=request_id,
                )
        clusters = await self.get_clusters()
        updated = next(c for c in clusters if c["id"] == cluster_id)
        return {
            "cluster": updated,
            "mergedAlertIds": merged,
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }

    async def get_field_tasks(self) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                select
                  ft.*,
                  ast.route,
                  ast.length_m
                from field_task ft
                join asset ast on ast.id = ft.asset_id
                order by ft.service_date asc, ft.starts_at asc
                """
            )
            tasks: list[dict[str, Any]] = []
            for r in rows:
                tel = await conn.fetch(
                    """
                    select distinct on (signal_key) signal_key, value
                    from telemetry_reading
                    where asset_id = $1
                    order by signal_key, observed_at desc
                    """,
                    r["asset_id"],
                )
                latest = {row["signal_key"]: _fmt_reading(row["value"]) for row in tel}
                tasks.append(
                    {
                        "id": r["id"],
                        "assetId": r["asset_id"],
                        "title": r["title"],
                        "titleHi": r["title_hi"] or r["title"],
                        "route": r["route"],
                        "lengthM": int(r["length_m"]),
                        "blockId": r["block_window_id"] or "",
                        "date": r["service_date"].isoformat(),
                        "start": r["starts_at"].strftime("%H:%M"),
                        "end": r["ends_at"].strftime("%H:%M"),
                        "level": r["level"],
                        "hypothesis": r["hypothesis"],
                        "hypothesisHi": r["hypothesis_hi"] or r["hypothesis"],
                        "falsifier": r["falsifier"],
                        "falsifierHi": r["falsifier_hi"] or r["falsifier"],
                        "lastReadings": {
                            "relayCurrent": latest.get("relay_i", ""),
                            "ballastConductance": latest.get("ballast_g", ""),
                            "cableInsulation": latest.get("cable_ir", ""),
                            "feedVoltage": latest.get("feed_v", ""),
                        },
                    }
                )
            queued = await conn.fetchval(
                "select count(*) from field_observation where synced_at is null"
            )
            return {
                "tasks": tasks,
                "sync": {
                    "lastSync": "13 Jul · 23:52 IST",
                    "queuedOffline": int(queued or 0),
                },
                "modelVersions": self._model_versions(),
                "generatedAt": utc_now_iso(),
            }

    async def submit_observation(
        self,
        *,
        idempotency_key: str,
        payload: dict[str, Any],
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        comparable = {
            "taskId": payload["taskId"],
            "finding": payload["finding"],
            "measurements": payload["measurements"],
            "note": payload.get("note", ""),
        }
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                existing = await conn.fetchrow(
                    "select task_id, finding::text as finding, measurements, note "
                    "from field_observation where idempotency_key = $1",
                    idempotency_key,
                )
                if existing is not None:
                    server_comp = {
                        "taskId": existing["task_id"],
                        "finding": existing["finding"],
                        "measurements": _json_val(existing["measurements"]),
                        "note": existing["note"],
                    }
                    if server_comp != comparable:
                        raise ApiProblemException(
                            status=409,
                            title="Idempotency conflict",
                            detail=(
                                "An observation with this idempotencyKey already exists with "
                                "different measurements or finding."
                            ),
                            error_type="urn:nidan:idempotency-conflict",
                            extra={"serverRecord": server_comp, "localRecord": comparable},
                        )
                    return {
                        "queued": True,
                        "receipt": f"rcpt-{idempotency_key[:8]}",
                        "replayed": True,
                        "modelVersions": self._model_versions(),
                        "generatedAt": utc_now_iso(),
                    }, True

                task = await conn.fetchrow(
                    "select id, asset_id from field_task where id = $1",
                    payload["taskId"],
                )
                if task is None:
                    raise ApiProblemException(
                        status=404,
                        title="Field task not found",
                        detail=f"Unknown field task '{payload['taskId']}'.",
                        error_type="urn:nidan:not-found",
                    )

                await conn.execute(
                    """
                    insert into field_observation
                      (task_id, asset_id, idempotency_key, finding, measurements, note, synced_at)
                    values
                      ($1, $2, $3, $4::field_finding, $5::jsonb, $6, now())
                    """,
                    task["id"],
                    task["asset_id"],
                    idempotency_key,
                    payload["finding"],
                    json.dumps(payload["measurements"]),
                    payload.get("note", ""),
                )
                await conn.execute(
                    "update field_task set status = 'submitted'::task_status where id = $1",
                    task["id"],
                )
                await self._insert_audit_log(
                    conn,
                    action="field.observation.submitted",
                    entity_type="field_task",
                    entity_id=task["id"],
                    after={"idempotencyKey": idempotency_key, "finding": payload["finding"]},
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    request_id=request_id,
                )
                return {
                    "queued": True,
                    "receipt": f"rcpt-{idempotency_key[:8]}",
                    "replayed": False,
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }, False

    async def get_model_health(self) -> dict[str, Any]:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "select payload from model_health_snapshot order by as_of desc limit 1"
            )
            if row is None:
                raise ApiProblemException(
                    status=404,
                    title="Model health snapshot missing",
                    detail="No model_health_snapshot rows found.",
                    error_type="urn:nidan:not-found",
                )
            data = _json_val(row["payload"])
            data["modelVersions"] = self._model_versions()
            data["generatedAt"] = utc_now_iso()
            return data

    async def get_kpi_summary(self, *, divisions: list[str] | None = None) -> dict[str, Any]:
        alerts = await self.list_alerts()
        if divisions is not None and "*" not in divisions:
            allowed = set(divisions)
            alerts = [a for a in alerts if a.get("division") in allowed]
        critical = sum(1 for a in alerts if a["level"] == "critical")
        warning = sum(1 for a in alerts if a["level"] == "warning")
        watch = sum(1 for a in alerts if a["level"] == "watch")
        ages = sorted(a["ageMinutes"] / 60.0 for a in alerts)
        median_age = round(ages[len(ages) // 2], 1) if ages else 0.0
        fits_or_extends = sum(
            1 for a in alerts if a.get("block") and a["block"]["fit"] in ("fits", "extends")
        )
        block_fit_ratio = round(fits_or_extends / len(alerts), 2) if alerts else 0.0
        return {
            "openAlerts": {"value": len(alerts), "delta": "+2 since yesterday"},
            "criticalShift": {"value": critical, "delta": "07T · 21 min"},
            "clusterAdjusted": {"value": 5, "delta": "5 alerts → 4 jobs"},
            "blockFit": {"value": block_fit_ratio, "delta": "+6 pts wk 28"},
            "queue": {
                "open": len(alerts),
                "critical": critical,
                "warning": warning,
                "watch": watch,
                "medianAgeHours": median_age,
            },
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }

    async def create_work_order_draft(
        self,
        *,
        alert_id: str,
        action: str,
        block_id: str,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any] | None:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                resolved_id = await conn.fetchval(
                    "select id from alert where id = $1 or asset_id = $1 limit 1",
                    alert_id,
                )
                if resolved_id is None:
                    return None
                bw_id = await conn.fetchval(
                    "select id from block_window where id = $1",
                    block_id,
                )
                actor_id = await self._resolve_actor_id(conn, actor_sub)
                draft_uuid = await conn.fetchval(
                    "insert into work_order_draft "
                    "(alert_id, action, block_window_id, status, created_by) "
                    "values ($1, $2, $3, 'draft'::work_order_status, $4) returning id",
                    resolved_id,
                    action,
                    bw_id,
                    actor_id,
                )
                draft_id = f"SMMS-draft-{str(draft_uuid)[:8]}"
                await self._insert_audit_log(
                    conn,
                    action="work_order.drafted",
                    entity_type="work_order_draft",
                    entity_id=draft_id,
                    after={"alertId": resolved_id, "blockId": block_id},
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    request_id=request_id,
                )
                return {
                    "id": draft_id,
                    "status": "draft",
                    "alertId": resolved_id,
                    "blockId": block_id,
                    "advisoryOnly": True,
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }

    async def search(self, query: str) -> list[dict[str, Any]]:
        q = query.strip()
        if not q:
            return []
        pattern = f"%{q}%"
        hits: list[dict[str, Any]] = []
        async with self.pool.acquire() as conn:
            alert_rows = await conn.fetch(
                """
                select
                  a.id,
                  a.asset_id,
                  ra.level::text as level,
                  ra.explanation->'physics'->>'headline' as headline
                from alert a
                join risk_assessment ra on ra.id = a.current_assessment_id
                join asset ast on ast.id = a.asset_id
                where a.id ilike $1
                   or a.asset_id ilike $1
                   or ast.name ilike $1
                   or ast.route ilike $1
                limit 10
                """,
                pattern,
            )
            for r in alert_rows:
                hits.append(
                    {
                        "kind": "alert",
                        "id": r["id"],
                        "title": f"{r['asset_id']} · {r['level'].upper()}",
                        "subtitle": r["headline"] or "",
                        "href": f"/alerts/{r['id']}",
                    }
                )
            asset_rows = await conn.fetch(
                "select id, circuit_type::text as circuit_type, length_m, relay_model from asset "
                "where id ilike $1 or cable_id ilike $1 or relay_model ilike $1 limit 10",
                pattern,
            )
            for r in asset_rows:
                hits.append(
                    {
                        "kind": "asset",
                        "id": r["id"],
                        "title": r["id"],
                        "subtitle": f"{r['circuit_type']} · {r['length_m']} m · {r['relay_model']}",
                        "href": f"/assets/{r['id']}",
                    }
                )
            cluster_rows = await conn.fetch(
                "select id, title, summary from cluster "
                "where id ilike $1 or title ilike $1 or summary ilike $1 limit 5",
                pattern,
            )
            for r in cluster_rows:
                hits.append(
                    {
                        "kind": "cluster",
                        "id": r["id"],
                        "title": f"{r['id']} · {r['title']}",
                        "subtitle": r["summary"],
                        "href": "/clusters",
                    }
                )
        return hits[:20]

    async def ingest_telemetry(self, samples: list[dict[str, Any]]) -> dict[str, int]:
        """Persist QC-annotated telemetry samples idempotently by (asset, signal, observed_at)."""

        def _as_dt(val: Any) -> Any:
            if isinstance(val, str):
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            return val

        accepted = 0
        deduplicated = 0
        try:
            async with self.pool.acquire() as conn:
                async with conn.transaction():
                    for s in samples:
                        inserted = await conn.fetchval(
                            """
                            insert into telemetry_reading
                              (asset_id, signal_key, observed_at, value, quality, source)
                            values ($1, $2, $3, $4, $5, $6)
                            on conflict (asset_id, signal_key, observed_at) do nothing
                            returning 1
                            """,
                            s["assetId"],
                            s["signalKey"],
                            _as_dt(s["observedAt"]),
                            s["value"],
                            int(s.get("quality", 0)),
                            s.get("source", "logger"),
                        )
                        if inserted:
                            accepted += 1
                        else:
                            deduplicated += 1
        except asyncpg.exceptions.ForeignKeyViolationError as exc:
            raise ApiProblemException(
                status=404,
                title="Unknown asset or signal key",
                detail=f"Telemetry sample references unknown asset or signal: {exc}",
                error_type="urn:nidan:not-found",
            ) from exc
        return {"accepted": accepted, "deduplicated": deduplicated}

    async def _has_phase3_model_run_columns(self, conn: asyncpg.Connection) -> bool:
        count = await conn.fetchval(
            """
            select count(*) from information_schema.columns
            where table_name = 'model_run'
              and column_name in ('snapshot_id', 'params_hash', 'dataset_hash', 'error_detail')
            """
        )
        return int(count or 0) == 4

    async def _record_failed_model_run(
        self,
        *,
        snapshot_id: str | None,
        code_version: str,
        params: dict[str, Any],
        params_hash: str,
        dataset_hash: str | None,
        input_watermark: Any,
        error_detail: str,
    ) -> None:
        try:
            async with self.pool.acquire() as conn:
                has_v2 = await self._has_phase3_model_run_columns(conn)
                if has_v2:
                    await conn.execute(
                        """
                        insert into model_run
                          (id, started_at, finished_at, input_watermark, code_version, params,
                           status, snapshot_id, params_hash, dataset_hash, error_detail)
                        values ($1, now(), now(), $2, $3, $4::jsonb, 'failed', $5, $6, $7, $8)
                        """,
                        str(uuid.uuid4()),
                        input_watermark,
                        code_version,
                        json.dumps(params),
                        snapshot_id,
                        params_hash,
                        dataset_hash,
                        error_detail[:500],
                    )
                else:
                    await conn.execute(
                        """
                        insert into model_run
                          (id, started_at, finished_at, input_watermark,
                           code_version, params, status)
                        values ($1, now(), now(), $2, $3, $4::jsonb, 'failed')
                        """,
                        str(uuid.uuid4()),
                        input_watermark,
                        code_version,
                        json.dumps({**params, "errorDetail": error_detail[:500]}),
                    )
        except Exception:  # pragma: no cover - best-effort audit on failure
            pass

    async def publish_model_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Atomically write model_run + snapshot + clusters + risk_assessments and advance alerts.

        Enforces idempotency on (snapshot_id, code_version, params_hash) when migration 0002
        is applied, and fails closed with a failed model_run row on policy/FK errors.
        """

        def _as_dt(val: Any) -> Any:
            if isinstance(val, str):
                return datetime.fromisoformat(val.replace("Z", "+00:00"))
            return val

        code_version = str(payload.get("codeVersion", "unknown"))
        params = payload.get("params") or {}
        params_hash = compute_params_hash(params)
        dataset_hash = payload.get("datasetHash")
        input_watermark = _as_dt(payload.get("inputWatermark"))
        snapshot_as_of = _as_dt(payload.get("snapshotAsOf"))
        resolved_snapshot_id: str | None = None

        try:
            async with self.pool.acquire() as conn:
                has_v2 = await self._has_phase3_model_run_columns(conn)
                async with conn.transaction():
                    # 1. Resolve or insert snapshot first so idempotency key includes snapshot_id
                    candidate_snap_id = str(uuid.uuid4())
                    await conn.execute(
                        """
                        insert into snapshot (id, as_of, week, label)
                        values ($1, $2, $3, $4)
                        on conflict (as_of) do nothing
                        """,
                        candidate_snap_id,
                        snapshot_as_of,
                        payload.get("snapshotWeek", 1),
                        payload.get("snapshotLabel", ""),
                    )
                    real_snapshot_id = await conn.fetchval(
                        "select id from snapshot where as_of = $1",
                        snapshot_as_of,
                    )
                    snapshot_id = str(real_snapshot_id or candidate_snap_id)
                    resolved_snapshot_id = snapshot_id

                    # 2. Check idempotency on (snapshot_id, code_version, params_hash)
                    if has_v2:
                        existing_run_id = await conn.fetchval(
                            """
                            select id from model_run
                            where snapshot_id = $1
                              and code_version = $2
                              and params_hash = $3
                              and status = 'succeeded'
                            limit 1
                            """,
                            snapshot_id,
                            code_version,
                            params_hash,
                        )
                        if existing_run_id is not None:
                            return {
                                "model_run_id": str(existing_run_id),
                                "snapshot_id": snapshot_id,
                                "assessments_written": 0,
                                "alerts_updated": 0,
                                "updated_asset_ids": [],
                                "clusters_updated": [],
                                "idempotent_replay": True,
                            }

                    # 3. Insert model_run row
                    model_run_id = str(uuid.uuid4())
                    if has_v2:
                        await conn.execute(
                            """
                            insert into model_run
                              (id, started_at, finished_at, input_watermark, code_version,
                               params, status, snapshot_id, params_hash, dataset_hash)
                            values ($1, now(), now(), $2, $3, $4::jsonb, 'succeeded', $5, $6, $7)
                            """,
                            model_run_id,
                            input_watermark,
                            code_version,
                            json.dumps(params),
                            snapshot_id,
                            params_hash,
                            dataset_hash,
                        )
                    else:
                        await conn.execute(
                            """
                            insert into model_run
                              (id, started_at, finished_at, input_watermark,
                               code_version, params, status)
                            values ($1, now(), now(), $2, $3, $4::jsonb, 'succeeded')
                            """,
                            model_run_id,
                            input_watermark,
                            code_version,
                            json.dumps(params),
                        )

                    updated_asset_ids: list[str] = []
                    clusters_updated: set[str] = set()

                    # 4. Upsert any common-cause clusters produced by GNN
                    for cl in payload.get("clusters", []) or []:
                        await conn.execute(
                            """
                            insert into cluster (
                              id, title, state, summary, weather_cell_id, saved_block_hours,
                              predicted_cascade_asset, cascade_min_days, cascade_max_days,
                              shared_edges, decisions
                            ) values (
                              $1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb
                            )
                            on conflict (id) do update set
                              title = excluded.title,
                              state = excluded.state,
                              summary = excluded.summary,
                              saved_block_hours = excluded.saved_block_hours,
                              shared_edges = excluded.shared_edges,
                              decisions = excluded.decisions
                            """,
                            cl["id"],
                            cl["title"],
                            cl.get("state", "open"),
                            cl["summary"],
                            cl.get("weatherCell") or None,
                            cl.get("savedBlockHours", 0),
                            cl.get("predictedCascadeAsset"),
                            cl.get("cascadeMinDays"),
                            cl.get("cascadeMaxDays"),
                            json.dumps(cl.get("sharedEdges", [])),
                            json.dumps(cl.get("decisions", [])),
                        )
                        clusters_updated.add(cl["id"])

                    # 5. Insert risk_assessment rows and advance/open alerts
                    for ra in payload.get("assessments", []):
                        asset_id = ra.get("assetId") or ra.get("asset_id")
                        if not asset_id:
                            continue
                        ra_id_val = str(uuid.uuid4())
                        await conn.execute(
                            """
                            insert into risk_assessment (
                              id, asset_id, snapshot_id, model_run_id, policy_version,
                              level, policy_rank, persistence, h24, h72, h7d, ece_zone,
                              p10_days, median_days, p90_days, rul_coverage, held_out_n,
                              likely_modes, mode_probability, mode_set_coverage,
                              data_trust_score, data_trust_flags, cluster_root,
                              block_window_id, block_fit, block_minutes,
                              explanation, ranking, model_versions, computed_at
                            ) values (
                              $1, $2, $3, $4, $5,
                              $6::alert_level, $7, $8, $9, $10, $11, $12,
                              $13, $14, $15, $16, $17,
                              $18::text[], $19, $20,
                              $21, $22::text[], $23,
                              $24, $25::block_fit, $26,
                              $27::jsonb, $28::jsonb, $29::jsonb, $30
                            )
                            """,
                            ra_id_val,
                            asset_id,
                            snapshot_id,
                            model_run_id,
                            ra.get(
                                "policyVersion",
                                payload.get("policyVersion", "policy-2026.07"),
                            ),
                            ra["level"],
                            ra["policyRank"],
                            ra.get("persistence", 0),
                            ra["h24"],
                            ra["h72"],
                            ra["h7d"],
                            ra["eceZone"],
                            ra["p10Days"],
                            ra["medianDays"],
                            ra["p90Days"],
                            ra["rulCoverage"],
                            ra.get("heldOutN", 0),
                            ra.get("likelyModes", ["F1"]),
                            ra.get("modeProbability", 0.5),
                            ra.get("modeSetCoverage", 0.9),
                            ra.get("dataTrustScore", 1.0),
                            ra.get("dataTrustFlags", []),
                            ra.get("clusterRoot", False),
                            ra.get("blockWindowId"),
                            ra.get("blockFit"),
                            ra.get("blockMinutes"),
                            json.dumps(ra.get("explanation", {})),
                            json.dumps(ra.get("ranking", {})),
                            json.dumps(ra.get("modelVersions", {})),
                            _as_dt(ra.get("computedAt")),
                        )

                        cluster_id_for_ra = ra.get("clusterId")
                        alert_row = await conn.fetchrow(
                            "select id, cluster_id from alert "
                            "where asset_id = $1 and status in ('open', 'acknowledged') "
                            "order by opened_at desc limit 1",
                            asset_id,
                        )
                        if alert_row:
                            await conn.execute(
                                "update alert set current_assessment_id = $1, "
                                "cluster_id = coalesce($2, cluster_id) where id = $3",
                                ra_id_val,
                                cluster_id_for_ra,
                                alert_row["id"],
                            )
                            eff_cluster = cluster_id_for_ra or alert_row["cluster_id"]
                            if eff_cluster:
                                clusters_updated.add(eff_cluster)
                        else:
                            new_alert_id = f"alr-{uuid.uuid4().hex[:8]}"
                            await conn.execute(
                                """
                                insert into alert
                                  (id, asset_id, cluster_id, opened_at, status,
                                   current_assessment_id)
                                values ($1, $2, $3, coalesce($4, now()), 'open', $5)
                                """,
                                new_alert_id,
                                asset_id,
                                cluster_id_for_ra,
                                snapshot_as_of,
                                ra_id_val,
                            )
                            await conn.execute(
                                "insert into alert_event (alert_id, kind, payload) "
                                "values ($1, 'opened', $2::jsonb)",
                                new_alert_id,
                                json.dumps({"modelRunId": model_run_id, "level": ra["level"]}),
                            )
                            if cluster_id_for_ra:
                                clusters_updated.add(cluster_id_for_ra)

                        updated_asset_ids.append(asset_id)

                    # 6. Optionally record model_health_snapshot materialisation
                    if payload.get("modelHealth"):
                        await conn.execute(
                            "insert into model_health_snapshot (as_of, payload) "
                            "values ($1, $2::jsonb)",
                            snapshot_as_of,
                            json.dumps(payload["modelHealth"]),
                        )
        except asyncpg.exceptions.CheckViolationError as exc:
            await self._record_failed_model_run(
                snapshot_id=resolved_snapshot_id,
                code_version=code_version,
                params=params,
                params_hash=params_hash,
                dataset_hash=dataset_hash,
                input_watermark=input_watermark,
                error_detail=str(exc),
            )
            raise ApiProblemException(
                status=422,
                title="Policy rule violation",
                detail=f"Assessment violates SQL policy constraint: {exc.constraint_name or exc}",
                error_type="urn:nidan:policy-violation",
            ) from exc
        except asyncpg.exceptions.ForeignKeyViolationError as exc:
            await self._record_failed_model_run(
                snapshot_id=resolved_snapshot_id,
                code_version=code_version,
                params=params,
                params_hash=params_hash,
                dataset_hash=dataset_hash,
                input_watermark=input_watermark,
                error_detail=str(exc),
            )
            raise ApiProblemException(
                status=404,
                title="Referenced entity not found",
                detail=f"Model run references unknown asset, cluster, or block: {exc}",
                error_type="urn:nidan:not-found",
            ) from exc

        return {
            "model_run_id": model_run_id,
            "snapshot_id": snapshot_id,
            "assessments_written": len(updated_asset_ids),
            "alerts_updated": len(updated_asset_ids),
            "updated_asset_ids": updated_asset_ids,
            "clusters_updated": list(clusters_updated),
            "idempotent_replay": False,
        }


def _fmt_reading(val: Any) -> str:
    num = float(val)
    if num.is_integer():
        return str(int(num))
    return str(round(num, 2))


def _derive_modes_from_alert(alert: dict[str, Any] | None) -> list[dict[str, Any]]:
    if alert is None:
        return []
    primary = alert["likelyModes"][0]
    mode_set = alert["explanation"]["model"]["modeSet"]
    alternatives = [m for m in mode_set if m != primary]
    remaining = max(0.0, 1.0 - float(alert["modeProbability"]))
    weights = [1.0 / (idx + 1) for idx in range(len(alternatives))]
    total = sum(weights)
    rows: list[dict[str, Any]] = [
        {"code": primary, "probability": alert["modeProbability"], "inSet": True}
    ]
    for idx, code in enumerate(alternatives):
        prob = (remaining * weights[idx]) / total if total > 0 else 0.0
        rows.append({"code": code, "probability": prob, "inSet": True})
    if not alternatives and remaining > 0:
        rows.append(
            {
                "code": "F12",
                "probability": remaining,
                "inSet": False,
                "excluded": "Residual mass stays no-fault-found until the falsifier is checked",
            }
        )
    return rows
