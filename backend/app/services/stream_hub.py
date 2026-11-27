"""WebSocket /v1/stream broadcast hub with Redis pub/sub fan-out.

Phase 2 adds a background Redis subscriber task so events published by external
workers (model runners, ingestion services) on the ``nidan:stream:events``
channel are forwarded to all connected WebSocket clients across API replicas.
"""

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
    """Manages active WebSocket subscribers and broadcasts cache-invalidation events.

    When a Redis client is provided the hub both *publishes* events to the
    Redis channel (so other API replicas receive them) and *subscribes* to that
    same channel in a background task so external publishers (model runners,
    ingestion workers) are relayed to local WebSocket connections automatically.
    """

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._subscriber_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start the Redis subscriber background task (call from lifespan)."""
        if self._redis is not None and self._subscriber_task is None:
            self._subscriber_task = asyncio.create_task(
                self._redis_subscriber_loop(), name="nidan-stream-subscriber"
            )
            logger.info("StreamHub: Redis subscriber task started on %s", CHANNEL_NAME)

    async def stop(self) -> None:
        """Cancel the Redis subscriber task (call from lifespan shutdown)."""
        if self._subscriber_task is not None:
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                pass
            self._subscriber_task = None
            logger.info("StreamHub: Redis subscriber task stopped.")

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
        """Broadcast an invalidation event to Redis channel and local sockets."""
        if self._redis is not None:
            try:
                await self._redis.publish(CHANNEL_NAME, json.dumps(event))
                if self._subscriber_task is not None and not self._subscriber_task.done():
                    # Subscriber loop delivers to local sockets once; avoid duplicate sends.
                    return
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

    async def _redis_subscriber_loop(self) -> None:
        """Subscribe to the Redis channel and forward messages to WebSockets."""
        while True:
            try:
                pubsub = self._redis.pubsub()  # type: ignore[union-attr]
                await pubsub.subscribe(CHANNEL_NAME)
                logger.debug("StreamHub subscribed to Redis channel %s", CHANNEL_NAME)
                async for message in pubsub.listen():
                    if message.get("type") != "message":
                        continue
                    try:
                        event: dict[str, Any] = json.loads(message["data"])
                    except (json.JSONDecodeError, TypeError):
                        continue
                    await self._broadcast_local(event)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("StreamHub Redis subscriber error (%s); reconnecting in 5 s", exc)
                await asyncio.sleep(5)

    @property
    def connection_count(self) -> int:
        return len(self._connections)
