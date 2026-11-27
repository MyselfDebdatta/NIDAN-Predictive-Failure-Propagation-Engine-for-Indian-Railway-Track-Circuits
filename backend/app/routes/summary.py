"""Command center KPI summary endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth import NidanPrincipal, get_current_principal
from app.cache import RedisCache
from app.models.summary import KpiSummary
from app.routes.deps import get_cache, get_summary_service
from app.services import SummaryService

router = APIRouter(prefix="/v1/summary", tags=["summary"])


@router.get("", response_model=KpiSummary, response_model_by_alias=True)
async def get_summary(
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[SummaryService, Depends(get_summary_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
):
    """Return division-scoped command-center KPI metrics and queue breakdown."""
    response.headers["Cache-Control"] = "private, max-age=15"
    divisions = None if principal.has_global_scope else sorted(principal.division_ids)
    scope_key = "global" if divisions is None else ",".join(divisions)
    cache_key = f"summary:kpi:{scope_key}"
    data = await cache.get_json(cache_key)
    if data is None:
        data = await service.get_kpis(divisions=divisions)
        await cache.set_json(cache_key, data, ttl_seconds=15)
    return data
