"""HTTP ETag and short-TTL Redis caching utilities."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as aioredis
from fastapi import Request, Response

logger = logging.getLogger("nidan.cache")

_CACHE_PREFIX = "nidan:cache:"


def make_etag(data: Any) -> str:
    """Return a weak ETag for the given JSON-serialisable data."""
    serialised = json.dumps(data, default=str, sort_keys=True)
    digest = hashlib.sha1(serialised.encode()).hexdigest()[:16]  # noqa: S324
    return f'W/"{digest}"'


def check_etag(request: Request, response: Response, etag: str) -> bool:
    """Set ETag on response; return True if client's If-None-Match matches."""
    response.headers["ETag"] = etag
    if_none_match = request.headers.get("if-none-match", "").strip()
    return if_none_match == etag


class RedisCache:
    """Optional short-TTL JSON cache backed by Redis (no-op when Redis is absent)."""

    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client

    async def get_json(self, key: str) -> Any | None:
        if self._redis is None:
            return None
        try:
            raw = await self._redis.get(f"{_CACHE_PREFIX}{key}")
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:  # pragma: no cover
            logger.debug("Redis cache get failed for %s: %s", key, exc)
            return None

    async def set_json(self, key: str, value: Any, *, ttl_seconds: int) -> None:
        if self._redis is None:
            return
        try:
            await self._redis.set(
                f"{_CACHE_PREFIX}{key}",
                json.dumps(value, default=str),
                ex=ttl_seconds,
            )
        except Exception as exc:  # pragma: no cover
            logger.debug("Redis cache set failed for %s: %s", key, exc)

    async def invalidate_prefixes(self, *prefixes: str) -> None:
        """Delete cached keys matching any of the given prefixes."""
        if self._redis is None:
            return
        try:
            for prefix in prefixes:
                keys = [k async for k in self._redis.scan_iter(match=f"{_CACHE_PREFIX}{prefix}*")]
                if keys:
                    await self._redis.delete(*keys)
        except Exception as exc:  # pragma: no cover
            logger.debug("Redis cache invalidation failed: %s", exc)
