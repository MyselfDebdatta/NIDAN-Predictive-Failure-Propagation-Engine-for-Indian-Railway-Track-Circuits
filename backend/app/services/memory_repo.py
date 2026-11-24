"""In-memory repository seeded from fixtures_snapshot.json for offline/test runs."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from app.middleware import ApiProblemException
from app.models.common import ModelVersions, utc_now_iso


class MemoryRepository:
    """Thread-safe/async-safe in-memory NIDAN store loaded from the fixture snapshot."""

    def __init__(self, snapshot_path: Path) -> None:
        raw = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self._alerts: list[dict[str, Any]] = copy.deepcopy(raw["alertFixtures"])
        self._asset_records: dict[str, dict[str, Any]] = copy.deepcopy(raw["assetRecords"])
        self._signals_by_asset: dict[str, list[dict[str, Any]]] = copy.deepcopy(
            raw["signalFixturesByAsset"]
        )
        self._modes_by_asset: dict[str, list[dict[str, Any]]] = copy.deepcopy(
            raw["modeDistributionByAsset"]
        )
        self._windows: list[dict[str, Any]] = copy.deepcopy(raw["blockFixtures"])
        self._jobs: list[dict[str, Any]] = copy.deepcopy(raw["blockJobs"])
        self._clusters: list[dict[str, Any]] = copy.deepcopy(raw["clusterFixtures"])
        self._field_tasks: list[dict[str, Any]] = copy.deepcopy(raw["fieldTaskFixtures"])
        self._field_sync: dict[str, Any] = copy.deepcopy(raw["fieldSyncFixture"])
        self._model_health: dict[str, Any] = copy.deepcopy(raw["modelHealthFixture"])
        self._kpi_base: dict[str, Any] = copy.deepcopy(raw["kpiFixture"])
        self._smms_ids: list[str] = list(raw.get("searchIndex", {}).get("smms", []))
        self._observations_by_key: dict[str, dict[str, Any]] = {}
        self._draft_counter = 2048
        self._work_orders: list[dict[str, Any]] = []
        self._audit_log: list[dict[str, Any]] = []

    def _model_versions(self) -> dict[str, str]:
        return ModelVersions().model_dump(by_alias=True)

    async def list_alerts(self) -> list[dict[str, Any]]:
        return sorted(copy.deepcopy(self._alerts), key=lambda a: a["policyRank"])

    async def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        for alert in self._alerts:
            if alert["id"] == alert_id or alert["assetId"] == alert_id:
                item = copy.deepcopy(alert)
                item["generatedAt"] = utc_now_iso()
                return item
        return None

    async def acknowledge_alert(self, alert_id: str) -> dict[str, Any] | None:
        for alert in self._alerts:
            if alert["id"] == alert_id or alert["assetId"] == alert_id:
                alert["acknowledged"] = True
                self._audit_log.append(
                    {
                        "action": "alert.acknowledged",
                        "entityType": "alert",
                        "entityId": alert["id"],
                        "at": utc_now_iso(),
                    }
                )
                return {
                    "acknowledged": True,
                    "alertId": alert["id"],
                    "status": "acknowledged",
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }
        return None

    async def defer_alert(
        self, alert_id: str, *, reason: str, review_date: str
    ) -> dict[str, Any] | None:
        for alert in self._alerts:
            if alert["id"] == alert_id or alert["assetId"] == alert_id:
                deferral = {"reason": reason.strip(), "reviewDate": review_date}
                alert["deferral"] = deferral
                self._audit_log.append(
                    {
                        "action": "alert.deferred",
                        "entityType": "alert",
                        "entityId": alert["id"],
                        "after": deferral,
                        "at": utc_now_iso(),
                    }
                )
                return {
                    "deferred": True,
                    "alertId": alert["id"],
                    "status": "deferred",
                    "deferral": deferral,
                    "modelVersions": self._model_versions(),
                    "generatedAt": utc_now_iso(),
                }
        return None

    async def get_asset_detail(self, asset_id: str) -> dict[str, Any] | None:
        record = self._asset_records.get(asset_id)
        if record is None:
            return None
        alert = next((a for a in self._alerts if a["assetId"] == asset_id), None)
        return {
            "alert": copy.deepcopy(alert),
            "record": copy.deepcopy(record),
            "signals": copy.deepcopy(self._signals_by_asset.get(asset_id, [])),
            "modes": copy.deepcopy(self._modes_by_asset.get(asset_id, [])),
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }

    async def get_blocks(self) -> dict[str, Any]:
        return {
            "windows": copy.deepcopy(self._windows),
            "jobs": copy.deepcopy(self._jobs),
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }

    async def get_clusters(self) -> list[dict[str, Any]]:
        clusters = copy.deepcopy(self._clusters)
        for cluster in clusters:
            members = [a["assetId"] for a in self._alerts if a.get("clusterId") == cluster["id"]]
            cluster["members"] = members
            cluster["alertsFolded"] = len(members)
        return clusters

    async def merge_cluster(self, cluster_id: str, alert_ids: list[str]) -> dict[str, Any] | None:
        target = next((c for c in self._clusters if c["id"] == cluster_id), None)
        if target is None:
            return None
        merged: list[str] = []
        for alert in self._alerts:
            if alert["id"] in alert_ids or alert["assetId"] in alert_ids:
                alert["clusterId"] = cluster_id
                merged.append(alert["id"])
        if not merged:
            raise ApiProblemException(
                status=404,
                title="No matching alerts",
                detail="None of the supplied alertIds exist.",
                error_type="urn:nidan:not-found",
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
        return {
            "tasks": copy.deepcopy(self._field_tasks),
            "sync": copy.deepcopy(self._field_sync),
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }

    async def submit_observation(
        self, *, idempotency_key: str, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        existing = self._observations_by_key.get(idempotency_key)
        comparable = {
            "taskId": payload["taskId"],
            "finding": payload["finding"],
            "measurements": payload["measurements"],
            "note": payload.get("note", ""),
        }
        if existing is not None:
            if existing["comparable"] != comparable:
                raise ApiProblemException(
                    status=409,
                    title="Idempotency conflict",
                    detail=(
                        "An observation with this idempotencyKey already exists with "
                        "different measurements or finding."
                    ),
                    error_type="urn:nidan:idempotency-conflict",
                    extra={"serverRecord": existing["comparable"], "localRecord": comparable},
                )
            replayed_receipt = copy.deepcopy(existing["receipt"])
            replayed_receipt["replayed"] = True
            return replayed_receipt, True

        task = next((t for t in self._field_tasks if t["id"] == payload["taskId"]), None)
        if task is None:
            raise ApiProblemException(
                status=404,
                title="Field task not found",
                detail=f"Unknown field task '{payload['taskId']}'.",
                error_type="urn:nidan:not-found",
            )

        receipt = {
            "queued": True,
            "receipt": f"rcpt-{idempotency_key[:8]}",
            "replayed": False,
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }
        self._observations_by_key[idempotency_key] = {
            "comparable": comparable,
            "receipt": receipt,
        }
        self._audit_log.append(
            {
                "action": "field.observation.submitted",
                "entityType": "field_task",
                "entityId": task["id"],
                "at": utc_now_iso(),
            }
        )
        return copy.deepcopy(receipt), False

    async def get_model_health(self) -> dict[str, Any]:
        data = copy.deepcopy(self._model_health)
        data["modelVersions"] = self._model_versions()
        data["generatedAt"] = utc_now_iso()
        return data

    async def get_kpi_summary(self) -> dict[str, Any]:
        open_alerts = [a for a in self._alerts if not a.get("deferral")]
        critical = sum(1 for a in self._alerts if a["level"] == "critical")
        warning = sum(1 for a in self._alerts if a["level"] == "warning")
        watch = sum(1 for a in self._alerts if a["level"] == "watch")
        summary = copy.deepcopy(self._kpi_base)
        summary["openAlerts"]["value"] = len(self._alerts)
        summary["criticalShift"]["value"] = critical
        summary["queue"] = {
            "open": len(open_alerts) + (len(self._alerts) - len(open_alerts)),
            "critical": critical,
            "warning": warning,
            "watch": watch,
            "medianAgeHours": self._kpi_base["queue"]["medianAgeHours"],
        }
        summary["modelVersions"] = self._model_versions()
        summary["generatedAt"] = utc_now_iso()
        return summary

    async def create_work_order_draft(
        self, *, alert_id: str, action: str, block_id: str
    ) -> dict[str, Any] | None:
        alert = next(
            (a for a in self._alerts if a["id"] == alert_id or a["assetId"] == alert_id),
            None,
        )
        if alert is None:
            return None
        self._draft_counter += 1
        draft_id = f"SMMS-draft-{self._draft_counter}"
        record = {
            "id": draft_id,
            "status": "draft",
            "alertId": alert["id"],
            "blockId": block_id,
            "action": action,
            "advisoryOnly": True,
            "modelVersions": self._model_versions(),
            "generatedAt": utc_now_iso(),
        }
        self._work_orders.append(record)
        self._audit_log.append(
            {
                "action": "work_order.drafted",
                "entityType": "work_order_draft",
                "entityId": draft_id,
                "at": utc_now_iso(),
            }
        )
        return record

    async def search(self, query: str) -> list[dict[str, Any]]:
        q = query.strip().lower()
        if not q:
            return []
        hits: list[dict[str, Any]] = []
        for alert in self._alerts:
            hay = f"{alert['id']} {alert['assetId']} {alert['assetName']} {alert['route']}".lower()
            if q in hay:
                hits.append(
                    {
                        "kind": "alert",
                        "id": alert["id"],
                        "title": f"{alert['assetId']} · {alert['level'].upper()}",
                        "subtitle": alert["explanation"]["physics"]["headline"],
                        "href": f"/alerts/{alert['id']}",
                    }
                )
        for asset_id, rec in self._asset_records.items():
            if q in asset_id.lower() or q in rec["cable"].lower() or q in rec["relay"].lower():
                hits.append(
                    {
                        "kind": "asset",
                        "id": asset_id,
                        "title": asset_id,
                        "subtitle": f"{rec['circuitType']} · {rec['lengthM']} m · {rec['relay']}",
                        "href": f"/assets/{asset_id}",
                    }
                )
        for cl in self._clusters:
            if q in cl["id"].lower() or q in cl["title"].lower() or q in cl["summary"].lower():
                hits.append(
                    {
                        "kind": "cluster",
                        "id": cl["id"],
                        "title": f"{cl['id']} · {cl['title']}",
                        "subtitle": cl["summary"],
                        "href": "/clusters",
                    }
                )
        for smms_id in self._smms_ids:
            if q in smms_id.lower():
                hits.append(
                    {
                        "kind": "smms",
                        "id": smms_id,
                        "title": smms_id,
                        "subtitle": "Historical SMMS failure precedent",
                        "href": "/alerts",
                    }
                )
        return hits[:20]
