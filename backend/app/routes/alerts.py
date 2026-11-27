"""Alert queue, detail, acknowledgement, and deferral endpoints."""

from __future__ import annotations

import json
from typing import Annotated
from urllib.parse import unquote

from fastapi import APIRouter, Depends, Query, Request, Response
from fastapi.responses import Response as FRResponse

from app.auth import NidanPrincipal, get_current_principal, require_operator_or_above
from app.cache import RedisCache, check_etag, make_etag
from app.middleware import get_trace_id
from app.models.alerts import (
    AcknowledgeResponse,
    Alert,
    DeferRequest,
    DeferResponse,
)
from app.models.common import ModelVersions, utc_now_iso
from app.routes.deps import get_alert_service, get_cache
from app.services import AlertService

router = APIRouter(prefix="/v1/alerts", tags=["alerts"])


@router.get("", response_model=list[Alert], response_model_by_alias=True)
async def list_alerts(
    request: Request,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[AlertService, Depends(get_alert_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
    cursor: Annotated[
        int | None, Query(ge=1, description="Cursor: policyRank to start from (inclusive)")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max results to return")] = 200,
) -> list[Alert] | FRResponse:
    """Return the ranked advisory alert queue ordered by server policyRank."""
    response.headers["Cache-Control"] = "private, max-age=15"
    response.headers["X-NIDAN-Generated-At"] = utc_now_iso()
    response.headers["X-NIDAN-Model-Versions"] = json.dumps(
        ModelVersions().model_dump(by_alias=True)
    )

    alerts = await cache.get_json("alerts:all")
    if alerts is None:
        alerts = await service.list_alerts()
        await cache.set_json("alerts:all", alerts, ttl_seconds=15)

    if not principal.has_global_scope:
        alerts = [a for a in alerts if principal.can_access_division(a.get("division"))]

    if cursor is not None:
        alerts = [a for a in alerts if a["policyRank"] >= cursor]
    alerts = alerts[:limit]

    etag = make_etag(alerts)
    if check_etag(request, response, etag):
        return FRResponse(status_code=304, headers=dict(response.headers))

    return alerts  # type: ignore[return-value]


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
    request: Request,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(require_operator_or_above)],
    service: Annotated[AlertService, Depends(get_alert_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
) -> AcknowledgeResponse:
    """Record operator acknowledgement in the append-only alert_event log."""
    response.headers["Cache-Control"] = "no-store"
    decoded_id = unquote(alert_id)
    existing = await service.get_alert(decoded_id)
    principal.assert_division(existing.get("division"))
    result = await service.acknowledge_alert(
        decoded_id,
        actor_sub=principal.sub,
        actor_role=principal.role,
        request_id=get_trace_id(request),
    )
    await cache.invalidate_prefixes("alerts:", "summary:")
    return result  # type: ignore[return-value]


@router.post(
    "/{alert_id:path}/defer",
    response_model=DeferResponse,
    response_model_by_alias=True,
)
async def defer_alert(
    alert_id: str,
    body: DeferRequest,
    request: Request,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(require_operator_or_above)],
    service: Annotated[AlertService, Depends(get_alert_service)],
    cache: Annotated[RedisCache, Depends(get_cache)],
) -> DeferResponse:
    """Defer an alert with a mandatory reason (>=10 chars) and review date."""
    response.headers["Cache-Control"] = "no-store"
    decoded_id = unquote(alert_id)
    existing = await service.get_alert(decoded_id)
    principal.assert_division(existing.get("division"))
    result = await service.defer_alert(
        decoded_id,
        reason=body.reason,
        review_date=body.review_date,
        actor_sub=principal.sub,
        actor_role=principal.role,
        request_id=get_trace_id(request),
    )
    await cache.invalidate_prefixes("alerts:", "summary:")
    return result  # type: ignore[return-value]


@router.get("/{alert_id:path}", response_model=Alert, response_model_by_alias=True)
async def get_alert(
    alert_id: str,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[AlertService, Depends(get_alert_service)],
) -> Alert:
    """Return a single alert with its full three-lens explanation."""
    response.headers["Cache-Control"] = "private, max-age=30"
    alert = await service.get_alert(unquote(alert_id))
    principal.assert_division(alert.get("division"))
    return alert  # type: ignore[return-value]
