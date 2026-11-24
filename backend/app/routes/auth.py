"""Current operator role, division scope, and advisory capability metadata."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.models.summary import MeResponse
from app.routes.deps import get_summary_service
from app.services import SummaryService

router = APIRouter(prefix="/v1", tags=["auth"])


@router.get("/me", response_model=MeResponse, response_model_by_alias=True)
async def get_me(
    response: Response,
    service: Annotated[SummaryService, Depends(get_summary_service)],
):
    """Return authenticated operator identity, division scope, and advisory capabilities."""
    response.headers["Cache-Control"] = "private, max-age=600"
    return await service.get_me()
