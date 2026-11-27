"""SMMS draft work-order pre-fill endpoint (draft only; never submits to SMMS)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth import NidanPrincipal, require_operator_or_above
from app.models.summary import WorkOrderDraftRequest, WorkOrderDraftResponse
from app.routes.deps import get_alert_service, get_summary_service
from app.services import AlertService, SummaryService

router = APIRouter(prefix="/v1/work-orders", tags=["work-orders"])


@router.post(
    "/draft",
    response_model=WorkOrderDraftResponse,
    response_model_by_alias=True,
)
async def draft_work_order(
    body: WorkOrderDraftRequest,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(require_operator_or_above)],
    alert_service: Annotated[AlertService, Depends(get_alert_service)],
    service: Annotated[SummaryService, Depends(get_summary_service)],
):
    """Create a local SMMS draft work order (advisory pre-fill only; never submits)."""
    response.headers["Cache-Control"] = "no-store"
    existing = await alert_service.get_alert(body.alert_id)
    principal.assert_division(existing.get("division"))
    return await service.create_work_order_draft(
        alert_id=body.alert_id,
        action=body.action,
        block_id=body.block_id,
    )
