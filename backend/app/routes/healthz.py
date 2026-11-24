"""Liveness and readiness probes for Docker and Kubernetes."""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.models.common import ModelVersions, utc_now_iso

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz(request: Request) -> dict[str, object]:
    """Return API liveness, backing store status, and advisory boundary metadata."""
    db_status = await request.app.state.db.health_check()
    return {
        "status": "ok",
        "advisoryOnly": True,
        "vitalCommandCapable": False,
        "storage": db_status,
        "modelVersions": ModelVersions().model_dump(by_alias=True),
        "generatedAt": utc_now_iso(),
    }
