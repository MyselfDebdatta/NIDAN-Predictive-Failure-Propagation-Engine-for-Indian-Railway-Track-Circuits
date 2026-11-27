"""Current operator role, division scope, and advisory capability metadata."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.auth import NidanPrincipal, get_current_principal
from app.models.common import ModelVersions, utc_now_iso
from app.models.summary import MeResponse

router = APIRouter(prefix="/v1", tags=["auth"])

_ROLE_CAPABILITIES: dict[str, list[str]] = {
    "maintainer": ["read:field_tasks", "submit:observations"],
    "operator": [
        "read:all",
        "acknowledge:alerts",
        "defer:alerts",
        "merge:clusters",
        "draft:work_orders",
    ],
    "dste": [
        "read:all",
        "acknowledge:alerts",
        "defer:alerts",
        "merge:clusters",
        "draft:work_orders",
        "review:blocks",
        "review:models",
    ],
    "service": ["append:telemetry", "publish:snapshots"],
    "admin": ["read:all", "inspect:audit_log", "promote:models"],
}


@router.get("/me", response_model=MeResponse, response_model_by_alias=True)
async def get_me(
    response: Response,
    principal: Annotated[NidanPrincipal, Depends(get_current_principal)],
) -> MeResponse:
    """Return authenticated operator identity, division scope, and advisory capabilities."""
    response.headers["Cache-Control"] = "private, max-age=600"
    return MeResponse(
        user_id=principal.sub,
        display_name=principal.display_name,
        role=principal.role,
        divisions=principal.division_ids,
        advisory_only=True,
        vital_command_capable=False,
        capabilities=_ROLE_CAPABILITIES.get(principal.role, []),
        model_versions=ModelVersions(),
        generated_at=utc_now_iso(),
    )
