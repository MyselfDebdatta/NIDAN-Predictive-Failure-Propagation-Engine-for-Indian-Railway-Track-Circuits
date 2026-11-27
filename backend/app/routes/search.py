"""Federated search endpoint across alerts, assets, clusters, and SMMS precedents."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from app.auth import NidanPrincipal, get_current_principal
from app.models.summary import SearchResponse
from app.routes.deps import get_summary_service
from app.services import SummaryService

router = APIRouter(prefix="/v1/search", tags=["search"])


@router.get("", response_model=SearchResponse, response_model_by_alias=True)
async def search(
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[SummaryService, Depends(get_summary_service)],
    q: Annotated[str, Query(min_length=0, max_length=120)] = "",
):
    """Search across alert IDs, track circuits, clusters, and SMMS event precedents."""
    response.headers["Cache-Control"] = "no-store"
    data = await service.search(q)
    if principal.has_global_scope:
        return data
    scoped_hits = [
        h
        for h in data.get("hits", [])
        if h.get("kind") not in ("alert", "asset")
        or "/" not in h.get("title", "")
        or principal.can_access_division(h["title"].split("·", 1)[0].strip().split("/", 1)[0])
    ]
    return {**data, "hits": scoped_hits}
