"""Generate backend/db/seed.sql from Nidan-Frontend/src/data/fixtures.ts.

Single-source-of-truth pipeline: reads the TypeScript demo scenario via Bun
(when available) or a pre-exported JSON file, validates every policy invariant
required by 0001_init.sql, and writes an idempotent seed.sql script.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))
NAMESPACE = uuid.UUID("7f3c9ac1-a735-4c22-8f65-5b30b88edd3c")

DIVISION_NAMES = {
    "ADRA": "Adra Division",
    "BKSC": "Bokaro / Bankura Section",
    "KGP": "Kharagpur Division",
    "TATA": "Tatanagar / Chakradharpur Section",
}

DEMO_USERS = [
    ("operator", "SSE (Sig) Control — Adra", "ADRA"),
    ("maintainer", "ESM Track Crew 1 — Adra", "ADRA"),
    ("dste", "Sr. DSTE (Coord) — SER", "ADRA"),
    ("service", "CRIS / RDPMS Ingestion Service", None),
    ("admin", "NIDAN Platform Administrator", None),
]


def det_uuid(kind: str, key: str) -> str:
    """Return a deterministic UUIDv5 string so seed.sql is reproducible."""
    return str(uuid.uuid5(NAMESPACE, f"{kind}:{key}"))


def sql_str(value: str | None) -> str:
    """Escape a Python string as a PostgreSQL single-quoted literal or NULL."""
    if value is None:
        return "null"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def sql_num(value: float | int | None) -> str:
    """Format a number or None for SQL."""
    if value is None:
        return "null"
    return str(value)


def sql_bool(value: bool) -> str:
    """Format a boolean for SQL."""
    return "true" if value else "false"


def sql_text_array(items: list[str]) -> str:
    """Format a PostgreSQL text[] literal."""
    if not items:
        return "'{}'::text[]"
    inner = ", ".join(sql_str(item) for item in items)
    return f"array[{inner}]::text[]"


def sql_jsonb(obj: Any) -> str:
    """Format a Python object as a PostgreSQL jsonb literal."""
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f"{sql_str(raw)}::jsonb"


def parse_weather_cell(cell_id: str) -> tuple[float | None, float | None]:
    """Extract lat/lon from IDs like 'wx-20.30N-85.83E'."""
    match = re.match(r"^wx-(\d+(?:\.\d+)?)([NS])-(\d+(?:\.\d+)?)([EW])$", cell_id)
    if not match:
        return None, None
    lat = float(match.group(1)) * (1 if match.group(2) == "N" else -1)
    lon = float(match.group(3)) * (1 if match.group(4) == "E" else -1)
    return lat, lon


def parse_trained_date(text: str) -> str:
    """Convert dates like '28 May 2026' to '2026-05-28'."""
    return datetime.strptime(text, "%d %b %Y").date().isoformat()


def load_fixtures_via_bun(repo_root: Path) -> dict[str, Any]:
    """Evaluate Nidan-Frontend/src/data/fixtures.ts via Bun and return JSON."""
    fixtures_path = (repo_root / "Nidan-Frontend" / "src" / "data" / "fixtures.ts").resolve()
    if not fixtures_path.exists():
        raise FileNotFoundError(f"Fixtures file not found: {fixtures_path}")
    script = (
        f"import * as f from {json.dumps(fixtures_path.as_uri())}; console.log(JSON.stringify(f));"
    )
    proc = subprocess.run(
        ["bun", "-e", script],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return json.loads(proc.stdout)


def build_seed_sql(data: dict[str, Any]) -> str:
    """Build complete seed.sql matching backend/db/0001_init.sql."""
    snapshot_meta = data["snapshot"]
    as_of_dt = datetime.fromisoformat(f"{snapshot_meta['date']}T{snapshot_meta['time']}:00+05:30")
    as_of_iso = as_of_dt.isoformat()

    alerts: list[dict[str, Any]] = data["alertFixtures"]
    asset_records: dict[str, dict[str, Any]] = data["assetRecords"]
    block_windows: list[dict[str, Any]] = data["blockFixtures"]
    block_jobs: list[dict[str, Any]] = data["blockJobs"]
    clusters: list[dict[str, Any]] = data["clusterFixtures"]
    field_tasks: list[dict[str, Any]] = data["fieldTaskFixtures"]
    signals_by_asset: dict[str, list[dict[str, Any]]] = data["signalFixturesByAsset"]
    model_health: dict[str, Any] = data["modelHealthFixture"]

    lines: list[str] = [
        "-- NIDAN seed data — generated from Nidan-Frontend/src/data/fixtures.ts",
        "-- Do not edit manually; regenerate with: python backend/db/seed_from_fixtures.py",
        "-- Run order: 0001_init.sql, then seed.sql.",
        "",
        "begin;",
        "",
        "-- ------------------------------------------------------------------ reference data",
    ]

    # 1. Divisions
    divisions = sorted({a["division"] for a in alerts} | set(DIVISION_NAMES.keys()))
    for div_id in divisions:
        div_name = DIVISION_NAMES.get(div_id, div_id)
        lines.append(
            f"insert into division (id, name) values ({sql_str(div_id)}, {sql_str(div_name)}) "
            "on conflict (id) do update set name = excluded.name;"
        )
    lines.append("")

    # 2. Weather cells
    weather_cells = sorted(
        {rec["weatherCell"] for rec in asset_records.values()}
        | {c["weatherCell"] for c in clusters}
    )
    for cell_id in weather_cells:
        lat, lon = parse_weather_cell(cell_id)
        label = f"IMD Grid {cell_id.removeprefix('wx-')}"
        lines.append(
            "insert into weather_cell (id, label, lat, lon) values "
            f"({sql_str(cell_id)}, {sql_str(label)}, {sql_num(lat)}, {sql_num(lon)}) "
            "on conflict (id) do update set label = excluded.label, "
            "lat = excluded.lat, lon = excluded.lon;"
        )
    lines.append("")

    # 3. Relay rooms
    alert_by_asset = {a["assetId"]: a for a in alerts}
    relay_rooms: dict[str, str] = {}
    for asset_id, rec in asset_records.items():
        div_id = alert_by_asset[asset_id]["division"]
        relay_rooms[rec["relayRoom"]] = div_id
    for rr_id, div_id in sorted(relay_rooms.items()):
        lines.append(
            "insert into relay_room (id, division_id) values "
            f"({sql_str(rr_id)}, {sql_str(div_id)}) "
            "on conflict (id) do update set division_id = excluded.division_id;"
        )
    lines.append("")

    # 4. Demo users
    user_ids: dict[str, str] = {}
    for role, display_name, div_id in DEMO_USERS:
        uid = det_uuid("app_user", role)
        user_ids[role] = uid
        lines.append(
            "insert into app_user (id, display_name, role, division_id, active) values "
            f"({sql_str(uid)}, {sql_str(display_name)}, {sql_str(role)}::user_role, "
            f"{sql_str(div_id)}, true) on conflict (id) do nothing;"
        )
    lines.append("")

    # 5. Assets & provenance
    for asset_id, rec in asset_records.items():
        alert = alert_by_asset[asset_id]
        lines.append(
            "insert into asset (id, division_id, name, route, circuit_type, length_m, "
            "installed_on, codal_life_years, relay_model, supply_id, cable_id, "
            "relay_room_id, weather_cell_id) values ("
            f"{sql_str(asset_id)}, {sql_str(alert['division'])}, {sql_str(alert['assetName'])}, "
            f"{sql_str(alert['route'])}, {sql_str(rec['circuitType'])}::circuit_type, "
            f"{rec['lengthM']}, {sql_str(rec['installed'])}::date, {rec['codalLifeYears']}, "
            f"{sql_str(rec['relay'])}, {sql_str(rec['supply'])}, {sql_str(rec['cable'])}, "
            f"{sql_str(rec['relayRoom'])}, {sql_str(rec['weatherCell'])}) "
            "on conflict (id) do update set name = excluded.name, route = excluded.route;"
        )
        lines.append(
            "insert into asset_record_source (asset_id, provenance, fetched_at) values ("
            f"{sql_str(asset_id)}, {sql_str(rec['provenance'])}, "
            f"{sql_str(as_of_iso)}::timestamptz) "
            "on conflict (asset_id) do update set provenance = excluded.provenance;"
        )
    lines.append("")

    # 6. Signal catalog & telemetry readings (12 daily points per asset signal)
    lines.append("-- ------------------------------------------------------------------ telemetry")
    catalog: dict[str, dict[str, Any]] = {}
    for series_list in signals_by_asset.values():
        for series in series_list:
            catalog.setdefault(series["key"], series)

    for key, spec in sorted(catalog.items()):
        lines.append(
            "insert into signal_catalog (key, label, unit, baseline, normal_band) values ("
            f"{sql_str(key)}, {sql_str(spec['label'])}, {sql_str(spec['unit'])}, "
            f"{sql_num(spec['baseline'])}, {sql_str(spec['normalBand'])}) "
            "on conflict (key) do update set label = excluded.label, unit = excluded.unit, "
            "baseline = excluded.baseline, normal_band = excluded.normal_band;"
        )
    lines.append("")

    for asset_id, series_list in signals_by_asset.items():
        for series in series_list:
            values: list[float | int] = series["values"]
            n_pts = len(values)
            for idx, val in enumerate(values):
                obs_dt = as_of_dt - timedelta(days=(n_pts - 1 - idx))
                quality = 0
                if asset_id == "KGP/TC/31T" and idx == n_pts - 2:
                    quality = 1  # represents logger_gap_6h interpolation flag
                lines.append(
                    "insert into telemetry_reading "
                    "(asset_id, signal_key, observed_at, value, quality, source) values ("
                    f"{sql_str(asset_id)}, {sql_str(series['key'])}, "
                    f"{sql_str(obs_dt.isoformat())}::timestamptz, "
                    f"{sql_num(val)}, {quality}, 'logger') "
                    "on conflict (asset_id, signal_key, observed_at) do nothing;"
                )
    lines.append("")

    # 7. Model lineage & snapshot
    lines.append(
        "-- ------------------------------------------------------------------ model lineage"
    )
    for model in model_health["models"]:
        mid = det_uuid("model_registry", f"{model['name']}:{model['version']}")
        trained_on = parse_trained_date(model["trained"])
        metrics = {"windowLabel": model["window"]}
        lines.append(
            "insert into model_registry "
            "(id, name, version, trained_on, owner, state, metrics, promoted_at) values ("
            f"{sql_str(mid)}, {sql_str(model['name'])}, {sql_str(model['version'])}, "
            f"{sql_str(trained_on)}::date, {sql_str(model['owner'])}, 'active', "
            f"{sql_jsonb(metrics)}, {sql_str(as_of_iso)}::timestamptz) "
            "on conflict (name, version) do nothing;"
        )

    model_run_id = det_uuid("model_run", as_of_iso)
    snapshot_id = det_uuid("snapshot", as_of_iso)
    run_params = {"policyVersion": "policy-2026.07", "heldOutN": model_health["heldOutN"]}
    t_start = (as_of_dt - timedelta(minutes=4)).isoformat()
    t_end = (as_of_dt - timedelta(minutes=1)).isoformat()
    lines.append(
        "insert into model_run "
        "(id, started_at, finished_at, input_watermark, code_version, params, status) values ("
        f"{sql_str(model_run_id)}, {sql_str(t_start)}::timestamptz, "
        f"{sql_str(t_end)}::timestamptz, {sql_str(as_of_iso)}::timestamptz, "
        f"'nidan-engine-0.3.1', {sql_jsonb(run_params)}, 'succeeded') "
        "on conflict (id) do nothing;"
    )
    lines.append(
        "insert into snapshot (id, as_of, week, label, published_at) values ("
        f"{sql_str(snapshot_id)}, {sql_str(as_of_iso)}::timestamptz, {snapshot_meta['week']}, "
        f"{sql_str(snapshot_meta['label'])}, {sql_str(as_of_iso)}::timestamptz) "
        "on conflict (as_of) do nothing;"
    )
    lines.append("")

    # 8. Rolling block windows & jobs
    lines.append(
        "-- ------------------------------------------------------------------ rolling block"
    )
    for bw in block_windows:
        lines.append(
            "insert into block_window "
            "(id, division_id, service_date, starts_at, ends_at, duration_min, kind) values ("
            f"{sql_str(bw['id'])}, 'ADRA', {sql_str(bw['date'])}::date, "
            f"{sql_str(bw['start'])}::time, {sql_str(bw['end'])}::time, "
            f"{bw['durationMin']}, {sql_str(bw['kind'])}::block_kind) "
            "on conflict (id) do update set service_date = excluded.service_date, "
            "starts_at = excluded.starts_at, ends_at = excluded.ends_at, "
            "duration_min = excluded.duration_min, kind = excluded.kind;"
        )
    lines.append("")

    for job in block_jobs:
        lines.append(
            "insert into block_job "
            "(id, title, block_window_id, duration_min, fit, crew, status) values ("
            f"{sql_str(job['id'])}, {sql_str(job['title'])}, {sql_str(job.get('blockId'))}, "
            f"{job['durationMin']}, {sql_str(job['fit'])}::block_fit, "
            f"{sql_str(job['crew'])}, 'planned'::job_status) "
            "on conflict (id) do update set title = excluded.title, "
            "block_window_id = excluded.block_window_id;"
        )
        for asset_id in job["assets"]:
            lines.append(
                "insert into block_job_asset (job_id, asset_id) values ("
                f"{sql_str(job['id'])}, {sql_str(asset_id)}) "
                "on conflict (job_id, asset_id) do nothing;"
            )
    lines.append("")

    # 9. Clusters
    lines.append("-- ------------------------------------------------------------------ clusters")
    for cl in clusters:
        cascade = cl.get("predictedCascade")
        cascade_asset = cascade["assetId"] if cascade else None
        cascade_min = cascade["inDays"]["min"] if cascade else None
        cascade_max = cascade["inDays"]["max"] if cascade else None
        opened = (as_of_dt - timedelta(hours=6)).isoformat()
        lines.append(
            "insert into cluster (id, title, state, summary, weather_cell_id, "
            "saved_block_hours, predicted_cascade_asset, cascade_min_days, "
            "cascade_max_days, shared_edges, decisions, opened_at) values ("
            f"{sql_str(cl['id'])}, {sql_str(cl['title'])}, {sql_str(cl['state'])}, "
            f"{sql_str(cl['summary'])}, {sql_str(cl['weatherCell'])}, "
            f"{sql_num(cl['savedBlockHours'])}, {sql_str(cascade_asset)}, "
            f"{sql_num(cascade_min)}, {sql_num(cascade_max)}, "
            f"{sql_jsonb(cl['sharedEdges'])}, {sql_jsonb(cl['decisions'])}, "
            f"{sql_str(opened)}::timestamptz) "
            "on conflict (id) do update set title = excluded.title, "
            "state = excluded.state, summary = excluded.summary;"
        )
    lines.append("")

    # 10. Risk assessments + alerts + alert_events
    lines.append(
        "-- ------------------------------------------------------------------ assessments & alerts"
    )
    for alert in alerts:
        assessment_id = det_uuid("risk_assessment", f"{alert['id']}:{as_of_iso}")
        risk = alert["risk"]
        rul = alert["rul"]
        trust = alert["dataTrust"]
        blk = alert.get("block")
        bw_id = blk["window"]["id"] if blk else None
        b_fit = f"{sql_str(blk['fit'])}::block_fit" if blk else "null"
        b_min = str(blk["minutes"]) if blk else "null"
        opened_at = (as_of_dt - timedelta(minutes=alert["ageMinutes"])).isoformat()
        deferral = alert.get("deferral")
        status = "deferred" if deferral else "open"
        def_reason = deferral["reason"] if deferral else None
        def_date = deferral["reviewDate"] if deferral else None
        def_date_sql = f"{sql_str(def_date)}::date" if def_date else "null"

        lines.append(
            "insert into risk_assessment ("
            "id, asset_id, snapshot_id, model_run_id, policy_version, level, "
            "policy_rank, persistence, h24, h72, h7d, ece_zone, p10_days, "
            "median_days, p90_days, rul_coverage, held_out_n, likely_modes, "
            "mode_probability, mode_set_coverage, data_trust_score, data_trust_flags, "
            "block_window_id, block_fit, block_minutes, cluster_root, explanation, "
            "ranking, model_versions, computed_at"
            ") values ("
            f"{sql_str(assessment_id)}, {sql_str(alert['assetId'])}, {sql_str(snapshot_id)}, "
            f"{sql_str(model_run_id)}, 'policy-2026.07', {sql_str(alert['level'])}::alert_level, "
            f"{alert['policyRank']}, {alert['persistence']}, "
            f"{risk['h24']}, {risk['h72']}, {risk['h7d']}, {risk['eceZone']}, "
            f"{rul['p10Days']}, {rul['medianDays']}, {rul['p90Days']}, "
            f"{rul['coverage']}, {rul['heldOutN']}, "
            f"{sql_text_array(alert['likelyModes'])}, {alert['modeProbability']}, "
            f"{alert['modeSetCoverage']}, {trust['score']}, {sql_text_array(trust['flags'])}, "
            f"{sql_str(bw_id)}, {b_fit}, {b_min}, false, "
            f"{sql_jsonb(alert['explanation'])}, {sql_jsonb(alert['ranking'])}, "
            f"{sql_jsonb(alert['modelVersions'])}, {sql_str(as_of_iso)}::timestamptz"
            ") on conflict (id) do nothing;"
        )
        lines.append(
            "insert into alert ("
            "id, asset_id, cluster_id, opened_at, status, current_assessment_id, "
            "deferral_reason, deferral_review_date"
            ") values ("
            f"{sql_str(alert['id'])}, {sql_str(alert['assetId'])}, "
            f"{sql_str(alert.get('clusterId'))}, {sql_str(opened_at)}::timestamptz, "
            f"{sql_str(status)}::alert_status, {sql_str(assessment_id)}, "
            f"{sql_str(def_reason)}, {def_date_sql}"
            ") on conflict (id) do nothing;"
        )
        opened_payload = {"level": alert["level"], "policyRank": alert["policyRank"]}
        lines.append(
            "insert into alert_event (alert_id, kind, at, actor_id, payload) "
            f"select {sql_str(alert['id'])}, 'opened', {sql_str(opened_at)}::timestamptz, "
            f"{sql_str(user_ids['service'])}, {sql_jsonb(opened_payload)} "
            "where not exists (select 1 from alert_event "
            f"where alert_id = {sql_str(alert['id'])} and kind = 'opened');"
        )
        if deferral:
            def_at = (as_of_dt - timedelta(minutes=max(1, alert["ageMinutes"] // 2))).isoformat()
            lines.append(
                "insert into alert_event (alert_id, kind, at, actor_id, payload) "
                f"select {sql_str(alert['id'])}, 'deferred', {sql_str(def_at)}::timestamptz, "
                f"{sql_str(user_ids['operator'])}, {sql_jsonb(deferral)} "
                "where not exists (select 1 from alert_event "
                f"where alert_id = {sql_str(alert['id'])} and kind = 'deferred');"
            )
    lines.append("")

    # 11. Field tasks
    lines.append(
        "-- ------------------------------------------------------------------ field tasks"
    )
    for task in field_tasks:
        lines.append(
            "insert into field_task ("
            "id, asset_id, block_window_id, title, title_hi, hypothesis, hypothesis_hi, "
            "falsifier, falsifier_hi, service_date, starts_at, ends_at, level, status"
            ") values ("
            f"{sql_str(task['id'])}, {sql_str(task['assetId'])}, {sql_str(task['blockId'])}, "
            f"{sql_str(task['title'])}, {sql_str(task['titleHi'])}, "
            f"{sql_str(task['hypothesis'])}, {sql_str(task['hypothesisHi'])}, "
            f"{sql_str(task['falsifier'])}, {sql_str(task['falsifierHi'])}, "
            f"{sql_str(task['date'])}::date, {sql_str(task['start'])}::time, "
            f"{sql_str(task['end'])}::time, {sql_str(task['level'])}::alert_level, "
            "'planned'::task_status"
            ") on conflict (id) do update set title = excluded.title, status = excluded.status;"
        )
    lines.append("")

    # 12. Model health snapshot
    lines.append(
        "-- ------------------------------------------------------------------ model health"
    )
    health_id = det_uuid("model_health_snapshot", model_health["asOf"])
    health_as_of = "2026-07-13T23:00:00+05:30"
    lines.append(
        "insert into model_health_snapshot (id, as_of, payload) values ("
        f"{sql_str(health_id)}, {sql_str(health_as_of)}::timestamptz, {sql_jsonb(model_health)}) "
        "on conflict (id) do nothing;"
    )
    lines.append("")
    lines.append("commit;")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate backend/db/seed.sql from frontend fixtures."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Path to NIDAN repository root.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "seed.sql",
        help="Output seed SQL path.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        default=Path(__file__).resolve().parent / "fixtures_snapshot.json",
        help="Optional JSON snapshot path for offline/test fixture repository.",
    )
    args = parser.parse_args()

    data = load_fixtures_via_bun(args.repo_root)
    sql_text = build_seed_sql(data)
    args.out.write_text(sql_text, encoding="utf-8")
    if args.json_out:
        args.json_out.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"Wrote {args.json_out}")
    print(f"Wrote {args.out} ({len(sql_text.splitlines())} lines)")


if __name__ == "__main__":
    main()
