"""Alert queue, detail, acknowledgement, and deferral endpoints."""

from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Response

from app.models.alerts import (
    AcknowledgeResponse,
    Alert,
    DeferRequest,
    DeferResponse,
)
from app.models.common import ModelVersions, utc_now_iso
from app.routes.deps import get_alert_service
from app.services import AlertService

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert], response_model_by_alias=True)
async def list_alerts(
    response: Response,
    service: Annotated[AlertService, Depends(get_alert_service)],
):
    """Return the ranked advisory alert queue ordered by server policyRank."""
    response.headers["Cache-Control"] = "private, max-age=15"
    response.headers["X-NIDAN-Generated-At"] = utc_now_iso()
    response.headers["X-NIDAN-Model-Versions"] = json.dumps(
        ModelVersions().model_dump(by_alias=True)
    )
    return await service.list_alerts()


@router.get("/{alert_id:path}/acknowledge", include_in_schema=False)
async def _ack_get_not_used() -> None:  # pragma: no cover
    pass


@router.post(
    "/{alert_id:path}/acknowledge",
    response_model=AcknowledgeResponse,
    response_model_by_alias=True,
)
async def acknowledge_alert(
    alert_id: str,
    response: Response,
    service: Annotated[AlertService, Depends(get_alert_service)],
):
    """Record operator acknowledgement in the append-only alert_event log."""
    response.headers["Cache-Control"] = "no-store"
    return await service.acknowledge_alert(unquote(alert_id))


@router.post(
    "/{alert_id:path}/defer",
    response_model=DeferResponse,
    response_model_by_alias=True,
)
async def defer_alert(
    alert_id: str,
    body: DeferRequest,
    response: Response,
    service: Annotated[AlertService, Depends(get_alert_service)],
):
    """Defer an alert with a mandatory reason (>=10 chars) and review date."""
    response.headers["Cache-Control"] = "no-store"
    return await service.defer_alert(
        unquote(alert_id),
        reason=body.reason,
        review_date=body.review_date,
    )


@router.get("/{alert_id:path}", response_model=Alert, response_model_by_alias=True)
async def get_alert(
    alert_id: str,
    response: Response,
    service: Annotated[AlertService, Depends(get_alert_service)],
):
    """Return a single alert with its full three-lens explanation."""
    response.headers["Cache-Control"] = "private, max-age=30"
    return await service.get_alert(unquote(alert_id))
