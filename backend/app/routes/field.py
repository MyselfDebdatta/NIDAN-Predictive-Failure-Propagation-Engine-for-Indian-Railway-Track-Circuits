"""Field tablet task sync and idempotent observation intake routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response

from app.auth import NidanPrincipal, get_current_principal, require_maintainer_or_above
from app.middleware import ApiProblemException, get_trace_id
from app.models.field import (
    FieldObservationReceipt,
    FieldObservationRequest,
    FieldTasksResponse,
)
from app.routes.deps import get_field_service
from app.services import FieldService

router = APIRouter(prefix="/v1/field", tags=["field"])


@router.get("/tasks", response_model=FieldTasksResponse, response_model_by_alias=True)
async def get_field_tasks(
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
    service: Annotated[FieldService, Depends(get_field_service)],
):
    """Return bilingual field verification tasks and sync status."""
    response.headers["Cache-Control"] = "private, max-age=30"
    data = await service.get_tasks()
    if not principal.has_global_scope:
        filtered = [
            t
            for t in data.get("tasks", [])
            if "/" not in t.get("assetId", "")
            or principal.can_access_division(t["assetId"].split("/", 1)[0])
        ]
        return {**data, "tasks": filtered}
    return data


@router.post(
    "/observations",
    response_model=FieldObservationReceipt,
    response_model_by_alias=True,
)
async def submit_observation(
    body: FieldObservationRequest,
    request: Request,
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(require_maintainer_or_above)],
    service: Annotated[FieldService, Depends(get_field_service)],
    idempotency_key: Annotated[str | None, Header(alias="idempotency-key")] = None,
):
    """Accept an idempotent field observation from the offline-first field PWA."""
    response.headers["Cache-Control"] = "no-store"
    resolved_key = (idempotency_key or body.idempotency_key).strip()
    if not resolved_key:
        raise ApiProblemException(
            status=400,
            title="Missing Idempotency-Key",
            detail="An Idempotency-Key header or idempotencyKey field is required.",
            error_type="urn:nidan:missing-idempotency-key",
        )
    if idempotency_key and body.idempotency_key and idempotency_key != body.idempotency_key:
        raise ApiProblemException(
            status=400,
            title="Idempotency-Key mismatch",
            detail="Idempotency-Key header does not match body.idempotencyKey.",
            error_type="urn:nidan:idempotency-mismatch",
        )
    return await service.submit_observation(
        idempotency_key=resolved_key,
        payload=body.model_dump(by_alias=True),
        actor_sub=principal.sub,
        actor_role=principal.role,
        request_id=get_trace_id(request),
    )
