"""WebSocket /v1/stream invalidation channel with heartbeat."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.models.common import utc_now_iso

router = APIRouter(tags=["stream"])


@router.websocket("/v1/stream")
async def stream_events(websocket: WebSocket) -> None:
    """Push cache-invalidation events and 15 s heartbeats to connected clients."""
    hub = websocket.app.state.stream_hub
    await hub.connect(websocket)
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
