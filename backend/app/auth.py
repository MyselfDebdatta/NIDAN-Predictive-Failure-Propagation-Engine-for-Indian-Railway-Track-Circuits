"""OIDC JWT verification and division-scoped RBAC for NIDAN.

Phase 2 introduces RS256/ES256 JWT enforcement via JWKS discovery.
In development / test mode (AUTH_MODE=dev) a static seeded operator identity
is returned without token verification, preserving the existing fixture-backed
contract tests.

Environment variables:
    AUTH_MODE          "dev" (default) | "oidc"
    OIDC_ISSUER        Keycloak realm URL, e.g. http://keycloak:8080/realms/nidan
    OIDC_AUDIENCE      JWT aud claim, e.g. nidan-api
    OIDC_JWKS_URL      Override JWKS URL (inferred from OIDC_ISSUER if absent)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Literal

import httpx
from fastapi import Depends, Request, WebSocket
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from pydantic import BaseModel, Field
from starlette.requests import HTTPConnection

from app.config import Settings, get_settings
from app.middleware import ApiProblemException

logger = logging.getLogger("nidan.auth")

UserRoleType = Literal["operator", "maintainer", "dste", "service", "admin"]

_ROLE_PRECEDENCE: tuple[UserRoleType, ...] = (
    "admin",
    "dste",
    "operator",
    "maintainer",
    "service",
)

_DEV_OPERATOR: dict[str, Any] = {
    "sub": "dev-operator-01",
    "displayName": "Demo Operator (Dev Mode)",
    "role": "operator",
    "divisionIds": ["ADRA", "BKSC", "KGP", "TATA"],
    "advisoryOnly": True,
    "vitalCommandCapable": False,
}

_DEV_SERVICE: dict[str, Any] = {
    "sub": "dev-service-01",
    "displayName": "Demo Model Runner (Dev Mode)",
    "role": "service",
    "divisionIds": ["*"],
    "advisoryOnly": True,
    "vitalCommandCapable": False,
}

# Module-level JWKS cache keyed by JWKS URL
_jwks_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_JWKS_TTL_SECONDS = 300.0


def clear_jwks_cache() -> None:
    """Clear the cached JWKS keysets (useful in tests)."""
    _jwks_cache.clear()


def _resolve_settings(conn: HTTPConnection) -> Settings:
    cfg = getattr(conn.app.state, "settings", None)
    if isinstance(cfg, Settings):
        return cfg
    return get_settings()


def _jwks_url(settings: Settings) -> str:
    if settings.oidc_jwks_url:
        return settings.oidc_jwks_url
    issuer = settings.oidc_issuer.rstrip("/")
    return f"{issuer}/.well-known/jwks.json"


async def _get_jwks(conn: HTTPConnection, settings: Settings) -> dict[str, Any]:
    override = getattr(conn.app.state, "jwks_override", None)
    if isinstance(override, dict):
        return override

    url = _jwks_url(settings)
    now = time.monotonic()
    cached = _jwks_cache.get(url)
    if cached is not None and (now - cached[0]) <= _JWKS_TTL_SECONDS:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            jwks = resp.json()
        _jwks_cache[url] = (now, jwks)
        return jwks
    except Exception as exc:
        logger.error("Failed to fetch JWKS from %s: %s", url, exc)
        if cached is not None:
            return cached[1]
        raise ApiProblemException(
            status=503,
            title="Authentication service unavailable",
            detail="Unable to retrieve OIDC signing keys.",
            error_type="urn:nidan:auth-unavailable",
            retryable=True,
        ) from exc


class NidanPrincipal(BaseModel):
    """Verified operator or service identity extracted from a JWT or the dev stub."""

    sub: str
    display_name: str = Field(alias="displayName")
    role: UserRoleType
    division_ids: list[str] = Field(alias="divisionIds")
    advisory_only: bool = Field(True, alias="advisoryOnly")
    vital_command_capable: bool = Field(False, alias="vitalCommandCapable")

    model_config = {"populate_by_name": True}

    @property
    def has_global_scope(self) -> bool:
        """Return True if principal can inspect all divisions."""
        return self.role in ("admin", "service") or "*" in self.division_ids

    def can_access_division(self, division_id: str | None) -> bool:
        """Return True if principal is authorized for the given division."""
        if not division_id or self.has_global_scope:
            return True
        return division_id in self.division_ids

    def assert_role(self, *allowed: UserRoleType) -> None:
        """Raise 403 if the principal's role is not in allowed."""
        if self.role not in allowed:
            raise ApiProblemException(
                status=403,
                title="Insufficient role",
                detail=f"Role '{self.role}' is not permitted for this operation.",
                error_type="urn:nidan:forbidden",
            )

    def assert_division(self, division_id: str | None) -> None:
        """Raise 403 if the principal cannot access the given division."""
        if not self.can_access_division(division_id):
            raise ApiProblemException(
                status=403,
                title="Division access denied",
                detail=f"Access to division '{division_id}' is not in your scope.",
                error_type="urn:nidan:forbidden-division",
            )


def _extract_role(payload: dict[str, Any]) -> UserRoleType:
    realm_roles: list[str] = payload.get("realm_access", {}).get("roles", []) or []
    direct_roles: list[str] = payload.get("roles", []) or []
    candidate_set = set(realm_roles) | set(direct_roles)
    for role in _ROLE_PRECEDENCE:
        if role in candidate_set:
            return role
    return "operator"


def _select_signing_key(token: str, jwks: dict[str, Any]) -> dict[str, Any]:
    keys = jwks.get("keys")
    if not isinstance(keys, list) or not keys:
        return jwks
    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
    except JWTError:
        kid = None
    if kid:
        for key in keys:
            if key.get("kid") == kid:
                return key
    return jwks


async def _verify_jwt(conn: HTTPConnection, token: str, settings: Settings) -> NidanPrincipal:
    """Verify a Bearer JWT against JWKS and return a NidanPrincipal."""
    jwks = await _get_jwks(conn, settings)
    signing_key = _select_signing_key(token, jwks)
    try:
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256", "ES256"],
            audience=settings.oidc_audience or None,
            issuer=settings.oidc_issuer or None,
            options={
                "verify_aud": bool(settings.oidc_audience),
                "verify_iss": bool(settings.oidc_issuer),
                "require": ["exp", "iat", "sub"],
            },
        )
    except ExpiredSignatureError as exc:
        raise ApiProblemException(
            status=401,
            title="Token expired",
            detail="Bearer token has expired.",
            error_type="urn:nidan:token-expired",
        ) from exc
    except JWTError as exc:
        raise ApiProblemException(
            status=401,
            title="Invalid token",
            detail=f"Invalid Bearer token: {exc}",
            error_type="urn:nidan:invalid-token",
        ) from exc

    role = _extract_role(payload)
    raw_divisions = payload.get("division_ids") or payload.get("groups") or []
    division_ids = [str(d).lstrip("/") for d in raw_divisions]

    return NidanPrincipal(
        **{
            "sub": str(payload["sub"]),
            "displayName": str(
                payload.get("name") or payload.get("preferred_username") or payload["sub"]
            ),
            "role": role,
            "divisionIds": division_ids,
            "advisoryOnly": True,
            "vitalCommandCapable": False,
        }
    )


_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> NidanPrincipal:
    """Return the authenticated principal (dev stub in dev mode, JWT in oidc mode)."""
    settings = _resolve_settings(request)
    if settings.auth_mode == "dev":
        return NidanPrincipal(**_DEV_OPERATOR)

    if credentials is None or not credentials.credentials:
        raise ApiProblemException(
            status=401,
            title="Authentication required",
            detail="Bearer token required.",
            error_type="urn:nidan:unauthorized",
        )

    return await _verify_jwt(request, credentials.credentials, settings)


async def require_operator_or_above(
    principal: NidanPrincipal = Depends(get_current_principal),  # noqa: B008
) -> NidanPrincipal:
    """Require operator, dste, or admin role."""
    principal.assert_role("operator", "dste", "admin")
    return principal


async def require_maintainer_or_above(
    principal: NidanPrincipal = Depends(get_current_principal),  # noqa: B008
) -> NidanPrincipal:
    """Require maintainer, operator, dste, or admin role."""
    principal.assert_role("maintainer", "operator", "dste", "admin")
    return principal


async def require_service_role(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),  # noqa: B008
) -> NidanPrincipal:
    """Require service or admin role (with explicit dev-mode passthrough)."""
    settings = _resolve_settings(request)
    if settings.auth_mode == "dev":
        return NidanPrincipal(**_DEV_SERVICE)

    if credentials is None or not credentials.credentials:
        raise ApiProblemException(
            status=401,
            title="Authentication required",
            detail="Bearer token required.",
            error_type="urn:nidan:unauthorized",
        )

    principal = await _verify_jwt(request, credentials.credentials, settings)
    principal.assert_role("service", "admin")
    return principal


async def verify_websocket_principal(websocket: WebSocket) -> NidanPrincipal:
    """Authenticate a WebSocket handshake via Bearer header or ?token= query param."""
    settings = _resolve_settings(websocket)
    if settings.auth_mode == "dev":
        return NidanPrincipal(**_DEV_OPERATOR)

    auth_header = websocket.headers.get("authorization", "")
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = websocket.query_params.get("token", "").strip()

    if not token:
        raise ApiProblemException(
            status=401,
            title="Authentication required",
            detail="WebSocket stream requires a Bearer token.",
            error_type="urn:nidan:unauthorized",
        )

    return await _verify_jwt(websocket, token, settings)
