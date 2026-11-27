"""Rolling Block maintenance windows and jobs endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import Response as FRResponse

from app.auth import NidanPrincipal, get_current_principal
from app.cache import RedisCache, check_etag, make_etag
from app.models.blocks import BlocksResponse
from app.routes.deps import get_block_service, get_cache
from app.services import BlockService

router = APIRouter(prefix="/v1/blocks", tags=["blocks"])


@router.get("", response_model=BlocksResponse, response_model_by_alias=True)
async def get_blocks(
    request: Request,
    response: Response,
    _principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[BlockService, Depends(get_block_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
):
    """Return published Rolling Block windows and fitted maintenance jobs."""
    response.headers["Cache-Control"] = "private, max-age=300"
    cache_key = f"blocks:{date_from or ''}:{date_to or ''}"
    data = await cache.get_json(cache_key)
    if data is None:
        data = await service.get_blocks(date_from=date_from, date_to=date_to)
        await cache.set_json(cache_key, data, ttl_seconds=300)

    etag = make_etag(data)
    if check_etag(request, response, etag):
        return FRResponse(status_code=304, headers=dict(response.headers))
    return data
