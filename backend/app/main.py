"""FastAPI application factory and lifespan setup for NIDAN."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.cache import RedisCache
from app.config import Settings, get_settings
from app.database import DatabaseManager
from app.middleware import register_middleware_and_handlers
from app.routes import ALL_ROUTERS
from app.services import (
    AlertService,
    AssetService,
    BlockService,
    ClusterService,
    FieldService,
    MemoryRepository,
    ModelService,
    NidanRepository,
    PostgresRepository,
    StreamHub,
    SummaryService,
)


def create_app(
    settings: Settings | None = None,
    *,
    repo_override: NidanRepository | None = None,
) -> FastAPI:
    """Construct and wire the NIDAN advisory FastAPI application."""
    cfg = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app_instance: FastAPI):
        db = DatabaseManager(
            cfg.database_url,
            cfg.redis_url,
            data_mode=cfg.data_mode,
            require_postgres=cfg.require_postgres,
        )
        await db.connect()

        if repo_override is not None:
            repo: NidanRepository = repo_override
        elif db.pool is not None:
            repo = PostgresRepository(db.pool)
        else:
            repo = MemoryRepository(cfg.fixtures_snapshot_path)

        stream_hub = StreamHub(redis_client=db.redis)
        cache = RedisCache(redis_client=db.redis)
        app_instance.state.settings = cfg
        app_instance.state.db = db
        app_instance.state.repo = repo
        app_instance.state.cache = cache
        app_instance.state.stream_hub = stream_hub
        app_instance.state.alert_service = AlertService(repo, stream_hub)
        app_instance.state.asset_service = AssetService(repo)
        app_instance.state.block_service = BlockService(repo)
        app_instance.state.cluster_service = ClusterService(repo, stream_hub)
        app_instance.state.field_service = FieldService(repo, stream_hub)
        app_instance.state.model_service = ModelService(repo)
        app_instance.state.summary_service = SummaryService(repo)

        # Phase 2: start Redis pub/sub subscriber for multi-replica fan-out
        await stream_hub.start()

        try:
            yield
        finally:
            await stream_hub.stop()
            await db.disconnect()

    application = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description=(
            "Advisory, non-vital predictive failure propagation API for Indian Railway track "
            "circuits. This API holds no command path and cannot write to interlocking, "
            "signals, routes, points, or track circuits."
        ),
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    register_middleware_and_handlers(application)

    for router in ALL_ROUTERS:
        application.include_router(router)

    return application


app = create_app()
