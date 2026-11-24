"""FastAPI router registry."""

from app.routes import (
    alerts,
    assets,
    auth,
    blocks,
    clusters,
    field,
    healthz,
    models,
    search,
    summary,
    work_orders,
    ws,
)

ALL_ROUTERS = [
    healthz.router,
    alerts.router,
    assets.router,
    blocks.router,
    clusters.router,
    field.router,
    models.router,
    summary.router,
    work_orders.router,
    search.router,
    auth.router,
    ws.router,
]
