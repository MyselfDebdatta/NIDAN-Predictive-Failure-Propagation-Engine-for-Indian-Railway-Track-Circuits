"""Model assurance, calibration, drift, and promotion gate endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.models.health import ModelHealth
from app.routes.deps import get_model_service
from app.services import ModelService

router = APIRouter(prefix="/v1/models", tags=["models"])


@router.get("/health", response_model=ModelHealth, response_model_by_alias=True)
async def get_model_health(
    response: Response,
    service: Annotated[ModelService, Depends(get_model_service)],
):
    """Return current calibration, reliability diagram, drift, and promotion gates."""
    response.headers["Cache-Control"] = "private, max-age=300"
    return await service.get_health()
