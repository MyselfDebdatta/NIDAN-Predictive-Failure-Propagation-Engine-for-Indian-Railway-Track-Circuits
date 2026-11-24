"""Database and Redis lifecycle management using asyncpg and redis.asyncio."""

from __future__ import annotations

import logging
from typing import Any

import asyncpg
import redis.asyncio as aioredis

logger = logging.getLogger("nidan.database")


class DatabaseManager:
    """Manages optional asyncpg pool and Redis client with graceful fallback."""

    def __init__(self, database_url: str, redis_url: str, data_mode: str = "postgres") -> None:
        self.database_url = database_url
        self.redis_url = redis_url
        self.data_mode = data_mode
        self.pool: asyncpg.Pool | None = None
        self.redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        """Open PostgreSQL and Redis connections when configured."""
        if self.data_mode == "fixture":
            logger.info("NIDAN_DATA_MODE=fixture — using seeded in-memory fixture store")
            return

        try:
            self.pool = await asyncpg.create_pool(
                dsn=self.database_url,
                min_size=2,
                max_size=10,
                command_timeout=15.0,
            )
            logger.info("Connected to PostgreSQL pool")
        except Exception as exc:  # pragma: no cover - depends on external daemon
            logger.warning("PostgreSQL unavailable (%s); falling back to fixture store", exc)
            self.pool = None

        try:
            client = aioredis.from_url(self.redis_url, decode_responses=True)
            await client.ping()
            self.redis = client
            logger.info("Connected to Redis")
        except Exception as exc:  # pragma: no cover - depends on external daemon
            logger.warning("Redis unavailable (%s); using in-process stream hub", exc)
            self.redis = None

    async def disconnect(self) -> None:
        """Close open database and Redis connections cleanly."""
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None

    async def health_check(self) -> dict[str, Any]:
        """Return connectivity status for PostgreSQL and Redis."""
        pg_ok = False
        redis_ok = False
        if self.pool is not None:
            try:
                async with self.pool.acquire() as conn:
                    await conn.fetchval("select 1")
                pg_ok = True
            except Exception:
                pg_ok = False
        if self.redis is not None:
            try:
                redis_ok = bool(await self.redis.ping())
            except Exception:
                redis_ok = False
        return {
            "mode": "postgres" if pg_ok else "fixture",
            "postgres": "up" if pg_ok else "unavailable",
            "redis": "up" if redis_ok else "in-memory",
        }
