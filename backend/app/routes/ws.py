"""WebSocket /v1/stream invalidation channel with OIDC auth and 15 s heartbeat."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.auth import verify_websocket_principal
from app.middleware import ApiProblemException
from app.models.common import utc_now_iso

router = APIRouter(tags=["stream"])


@router.websocket("/v1/stream")
async def stream_events(websocket: WebSocket) -> None:
    """Push division-scoped cache-invalidation events and 15 s heartbeats."""
    try:
        principal = await verify_websocket_principal(websocket)
    except ApiProblemException:
        await websocket.close(code=1008)
        return

    hub = websocket.app.state.stream_hub
    scope = None if principal.has_global_scope else principal.division_ids
    await hub.connect(websocket, division_ids=scope)
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            except TimeoutError:
                await websocket.send_json({"type": "heartbeat", "at": utc_now_iso()})
    except WebSocketDisconnect:
        await hub.disconnect(websocket)
    except Exception:
        await hub.disconnect(websocket)
