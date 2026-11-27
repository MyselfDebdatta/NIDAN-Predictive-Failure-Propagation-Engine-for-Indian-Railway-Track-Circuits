"""FastAPI route dependencies pulling services from application state."""

from __future__ import annotations

from fastapi import Request

from app.cache import RedisCache
from app.services import (
    AlertService,
    AssetService,
    BlockService,
    ClusterService,
    FieldService,
    ModelService,
    StreamHub,
    SummaryService,
)


def get_alert_service(request: Request) -> AlertService:
    return request.app.state.alert_service


def get_asset_service(request: Request) -> AssetService:
    return request.app.state.asset_service


def get_block_service(request: Request) -> BlockService:
    return request.app.state.block_service


def get_cluster_service(request: Request) -> ClusterService:
    return request.app.state.cluster_service


def get_field_service(request: Request) -> FieldService:
    return request.app.state.field_service


def get_model_service(request: Request) -> ModelService:
    return request.app.state.model_service


def get_summary_service(request: Request) -> SummaryService:
    return request.app.state.summary_service


def get_stream_hub(request: Request) -> StreamHub:
    return request.app.state.stream_hub


def get_cache(request: Request) -> RedisCache:
    return request.app.state.cache
