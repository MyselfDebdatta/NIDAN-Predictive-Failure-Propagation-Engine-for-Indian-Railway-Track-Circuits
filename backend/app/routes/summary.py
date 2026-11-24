"""Command center KPI summary endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.models.summary import KpiSummary
from app.routes.deps import get_summary_service
from app.services import SummaryService

router = APIRouter(prefix="/v1/summary", tags=["summary"])


@router.get("", response_model=KpiSummary, response_model_by_alias=True)
async def get_summary(
    response: Response,
    service: Annotated[SummaryService, Depends(get_summary_service)],
):
    """Return command-center KPI metrics and queue breakdown."""
    response.headers["Cache-Control"] = "private, max-age=15"
    return await service.get_kpis()
