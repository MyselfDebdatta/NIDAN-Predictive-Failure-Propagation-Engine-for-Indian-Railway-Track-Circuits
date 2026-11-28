"""Safety boundary tests for the AI/ML engine (spec §2, §17)."""

from __future__ import annotations

import re
from pathlib import Path

from nidan_ai.config import ALLOWED_INGEST_PATHS

AI_PACKAGE_DIR = Path(__file__).resolve().parents[1] / "nidan_ai"

_FORBIDDEN_ENDPOINT_RE = re.compile(
    r"/v1/(?:interlocking|signals|routes|points|track-circuits)/[^\s'\"]*command",
    re.IGNORECASE,
)
_V1_ROUTE_RE = re.compile(r"/v1/[a-zA-Z0-9_/\-]+")
_ALLOWED_V1_PATHS = frozenset(ALLOWED_INGEST_PATHS) | {
    "/v1/alerts",
    "/v1/blocks",
    "/v1/assets",
    "/v1/clusters",
    "/v1/models/health",
}


def test_only_allowed_ingest_paths_configured() -> None:
    assert tuple(ALLOWED_INGEST_PATHS) == ("/v1/ingest/telemetry", "/v1/ingest/model-run")


def test_no_vital_command_routes_or_actuation_in_ai_package() -> None:
    offenders: list[str] = []
    for path in sorted(AI_PACKAGE_DIR.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        if _FORBIDDEN_ENDPOINT_RE.search(source):
            offenders.append(f"{path}: forbidden vital command route")
        for match in _V1_ROUTE_RE.finditer(source):
            route = match.group(0)
            if route not in _ALLOWED_V1_PATHS and not route.startswith("/v1/assets/"):
                offenders.append(f"{path}: unexpected /v1 route {route!r}")
        for forbidden_call in ("actuate_point", "set_signal_aspect", "command_interlocking"):
            if forbidden_call in source:
                offenders.append(f"{path}: forbidden symbol {forbidden_call}")
    assert offenders == []


def test_canonical_loader_is_strictly_read_only() -> None:
    canonical_src = (AI_PACKAGE_DIR / "data" / "canonical.py").read_text(encoding="utf-8")
    assert "set transaction read only" in canonical_src
    for write_kw in ("insert into", "update telemetry_reading", "delete from"):
        assert write_kw not in canonical_src.lower()
