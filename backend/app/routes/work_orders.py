"""SMMS draft work-order pre-fill endpoint (draft only; never submits to SMMS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.models.summary import WorkOrderDraftRequest, WorkOrderDraftResponse
from app.routes.deps import get_summary_service
from app.services import SummaryService

router = APIRouter(prefix="/v1/work-orders", tags=["work-orders"])


@router.post(
    "/draft",
    response_model=WorkOrderDraftResponse,
    response_model_by_alias=True,
)
async def draft_work_order(
    body: WorkOrderDraftRequest,
    response: Response,
    service: Annotated[SummaryService, Depends(get_summary_service)],
):
    """Create a local SMMS draft work order (advisory pre-fill only; never submits)."""
    response.headers["Cache-Control"] = "no-store"
    return await service.create_work_order_draft(
        alert_id=body.alert_id,
        action=body.action,
        block_id=body.block_id,
    )
