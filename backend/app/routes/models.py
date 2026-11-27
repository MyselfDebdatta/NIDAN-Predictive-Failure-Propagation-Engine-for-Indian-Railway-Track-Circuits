"""Model assurance, calibration, drift, and promotion gate endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import Response as FRResponse

from app.auth import NidanPrincipal, get_current_principal
from app.cache import RedisCache, check_etag, make_etag
from app.models.health import ModelHealth
from app.routes.deps import get_cache, get_model_service
from app.services import ModelService

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("/health", response_model=ModelHealth, response_model_by_alias=True)
async def get_model_health(
    request: Request,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[ModelService, Depends(get_model_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
):
    """Return current calibration, reliability diagram, drift, and promotion gates."""
    response.headers["Cache-Control"] = "private, max-age=300"
    data = await cache.get_json("models:health")
    if data is None:
        data = await service.get_health()
        await cache.set_json("models:health", data, ttl_seconds=300)

    etag = make_etag(data)
    if check_etag(request, response, etag):
        return FRResponse(status_code=304, headers=dict(response.headers))
    return data
