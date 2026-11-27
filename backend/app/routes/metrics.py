"""Prometheus metrics endpoint for NIDAN advisory API."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.metrics import metrics_registry

router = APIRouter(tags=["observability"])


@router.get("/metrics", include_in_schema=False)
async def get_metrics(request: Request) -> PlainTextResponse:
    """Expose Prometheus metrics (latency, WS connections, DB pool, field sync)."""
    hub = getattr(request.app.state, "stream_hub", None)
    ws_count = hub.connection_count if hub is not None else 0

    db = getattr(request.app.state, "db", None)
    pool = getattr(db, "pool", None) if db is not None else None
    pool_size = pool.get_size() if pool is not None else 0
    pool_idle = pool.get_idle_size() if pool is not None else 0

    body = metrics_registry.render_prometheus(
        ws_connections=ws_count,
        db_pool_size=pool_size,
        db_pool_idle=pool_idle,
    )
    return PlainTextResponse(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )
