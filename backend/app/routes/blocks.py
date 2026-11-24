"""Rolling Block maintenance windows and jobs endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.models.blocks import BlocksResponse
from app.routes.deps import get_block_service
from app.services import BlockService

router = APIRouter(prefix="/v1/blocks", tags=["blocks"])


@router.get("", response_model=BlocksResponse, response_model_by_alias=True)
async def get_blocks(
    response: Response,
    service: Annotated[BlockService, Depends(get_block_service)],
    date_from: Annotated[str | None, Query(alias="from")] = None,
    date_to: Annotated[str | None, Query(alias="to")] = None,
):
    """Return published Rolling Block windows and fitted maintenance jobs."""
    response.headers["Cache-Control"] = "private, max-age=300"
    return await service.get_blocks(date_from=date_from, date_to=date_to)
