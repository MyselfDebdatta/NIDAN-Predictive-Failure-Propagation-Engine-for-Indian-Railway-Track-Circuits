"""PostgreSQL repository backed by asyncpg and schema 0001_init.sql."""

from __future__ import annotations

import json
from typing import Any

import asyncpg

from app.middleware import ApiProblemException
from app.models.common import ModelVersions, utc_now_iso


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

    async def acknowledge_alert(self, alert_id: str) -> dict[str, Any] | None:
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
                await conn.execute(
                    "update alert set status = 'acknowledged'::alert_status where id = $1",
                    resolved_id,
                )
                await conn.execute(
                    "insert into alert_event (alert_id, kind, payload) "
                    "values ($1, 'acknowledged', $2::jsonb)",
                    resolved_id,
                    json.dumps({"previousStatus": row["status"]}),
                )
                await conn.execute(
                    "insert into audit_log (action, entity_type, entity_id, before, after) "
                    "values ('alert.acknowledged', 'alert', $1, $2::jsonb, $3::jsonb)",
                    resolved_id,
                    json.dumps({"status": row["status"]}),
                    json.dumps({"status": "acknowledged"}),
                )
                return {
                    "acknowledged": True,
                    "alertId": resolved_id,
                    "status": "acknowledged",
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }

    async def defer_alert(
        self, alert_id: str, *, reason: str, review_date: str
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
                clean_reason = reason.strip()
                await conn.execute(
                    "update alert set status = 'deferred'::alert_status, "
                    "deferral_reason = $2, deferral_review_date = $3::date where id = $1",
                    resolved_id,
                    clean_reason,
                    review_date,
                )
                deferral = {"reason": clean_reason, "reviewDate": review_date}
                await conn.execute(
                    "insert into alert_event (alert_id, kind, payload) "
                    "values ($1, 'deferred', $2::jsonb)",
                    resolved_id,
                    json.dumps(deferral),
                )
                await conn.execute(
                    "insert into audit_log (action, entity_type, entity_id, before, after) "
                    "values ('alert.deferred', 'alert', $1, $2::jsonb, $3::jsonb)",
                    resolved_id,
                    json.dumps({"status": row["status"]}),
                    json.dumps({"status": "deferred", **deferral}),
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

    async def merge_cluster(self, cluster_id: str, alert_ids: list[str]) -> dict[str, Any] | None:
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
                await conn.execute(
                    "insert into audit_log (action, entity_type, entity_id, after) "
                    "values ('cluster.merged', 'cluster', $1, $2::jsonb)",
                    cluster_id,
                    json.dumps({"mergedAlertIds": merged}),
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
        self, *, idempotency_key: str, payload: dict[str, Any]
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
                await conn.execute(
                    "insert into audit_log (action, entity_type, entity_id, after) "
                    "values ('field.observation.submitted', 'field_task', $1, $2::jsonb)",
                    task["id"],
                    json.dumps({"idempotencyKey": idempotency_key, "finding": payload["finding"]}),
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

    async def get_kpi_summary(self) -> dict[str, Any]:
        alerts = await self.list_alerts()
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
        self, *, alert_id: str, action: str, block_id: str
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
                draft_uuid = await conn.fetchval(
                    "insert into work_order_draft (alert_id, action, block_window_id, status) "
                    "values ($1, $2, $3, 'draft'::work_order_status) returning id",
                    resolved_id,
                    action,
                    bw_id,
                )
                draft_id = f"SMMS-draft-{str(draft_uuid)[:8]}"
                await conn.execute(
                    "insert into audit_log (action, entity_type, entity_id, after) "
                    "values ('work_order.drafted', 'work_order_draft', $1, $2::jsonb)",
                    draft_id,
                    json.dumps({"alertId": resolved_id, "blockId": block_id}),
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
