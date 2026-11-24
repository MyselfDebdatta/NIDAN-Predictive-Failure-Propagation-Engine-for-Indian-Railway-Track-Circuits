"""WebSocket /v1/stream broadcast hub with optional Redis pub/sub backing."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import WebSocket

from app.models.common import utc_now_iso

logger = logging.getLogger("nidan.stream")
CHANNEL_NAME = "nidan:stream:events"


class StreamHub:
    """Manages active WebSocket subscribers and broadcasts invalidation events."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    def set_redis(self, redis_client: aioredis.Redis | None) -> None:
        self._redis = redis_client

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        await websocket.send_json({"type": "heartbeat", "at": utc_now_iso()})

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    async def publish(self, event: dict[str, Any]) -> None:
        """Broadcast an invalidation event to local sockets and Redis pub/sub."""
        if self._redis is not None:
            try:
                await self._redis.publish(CHANNEL_NAME, json.dumps(event))
            except Exception as exc:  # pragma: no cover
                logger.warning("Redis publish failed (%s); falling back to local broadcast", exc)
        await self._broadcast_local(event)

    async def _broadcast_local(self, event: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._connections)
        stale: list[WebSocket] = []
        for ws in targets:
            try:
                await ws.send_json(event)
            except Exception:
                stale.append(ws)
        if stale:
            async with self._lock:
                for ws in stale:
                    self._connections.discard(ws)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
