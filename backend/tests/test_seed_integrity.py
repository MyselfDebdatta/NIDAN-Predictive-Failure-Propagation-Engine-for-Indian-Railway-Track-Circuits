"""Integrity tests for generated seed.sql and fixtures_snapshot.json."""

from __future__ import annotations

import json
from pathlib import Path


def test_fixtures_snapshot_and_seed_sql_stay_consistent() -> None:
    db_dir = Path(__file__).resolve().parents[1] / "db"
    snapshot = json.loads((db_dir / "fixtures_snapshot.json").read_text(encoding="utf-8"))
    seed_sql = (db_dir / "seed.sql").read_text(encoding="utf-8")

    alerts = snapshot["alertFixtures"]
    assert len(alerts) == 11
    assert len(snapshot["assetRecords"]) == 11
    assert len(snapshot["blockFixtures"]) == 7
    assert len(snapshot["blockJobs"]) == 8
    assert len(snapshot["clusterFixtures"]) == 2
    assert len(snapshot["fieldTaskFixtures"]) == 3

    for alert in alerts:
        assert alert["id"] in seed_sql
        assert alert["assetId"] in seed_sql
        if alert["level"] == "critical":
            assert alert["risk"]["h24"] > 0.5
        elif alert["level"] == "warning":
            assert alert["risk"]["h72"] > 0.3
        else:
            assert alert["risk"]["h24"] <= 0.5
            assert alert["risk"]["h72"] <= 0.3

    for task in snapshot["fieldTaskFixtures"]:
        assert task["id"] in seed_sql
        series = snapshot["signalFixturesByAsset"][task["assetId"]]
        by_key = {s["key"]: str(s["values"][-1]) for s in series}
        if "relay_i" in by_key:
            assert by_key["relay_i"] == task["lastReadings"]["relayCurrent"]
        if "ballast_g" in by_key:
            assert by_key["ballast_g"] == task["lastReadings"]["ballastConductance"]
