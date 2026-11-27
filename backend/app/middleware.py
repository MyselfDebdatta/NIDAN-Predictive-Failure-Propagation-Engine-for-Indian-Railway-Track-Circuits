"""Middleware, RFC 9457 error handling, and advisory-boundary enforcement."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.metrics import metrics_registry
from app.models.common import ProblemDetails

logger = logging.getLogger("nidan.middleware")

# Banned path segments that would imply vital signalling control (permanently out of scope).
VITAL_CONTROL_PATTERNS = (
    "/interlocking/",
    "/signals/",
    "/routes/",
    "/points/",
    "/track-circuits/",
)

# Per-process fallback rate-limit buckets keyed by (client_ip, minute_bucket)
_local_rate_buckets: dict[tuple[str, int], int] = {}


async def _check_rate_limit(request: Request, limit_per_min: int) -> int | None:
    """Return Retry-After seconds if caller exceeded rate limit, else None."""
    if limit_per_min <= 0 or request.url.path in ("/healthz", "/metrics"):
        return None
    client_ip = request.client.host if request.client else "unknown"
    now_s = int(time.time())
    minute_bucket = now_s // 60
    retry_after = max(1, 60 - (now_s % 60))

    db = getattr(request.app.state, "db", None)
    redis_client = getattr(db, "redis", None) if db is not None else None
    if redis_client is not None:
        key = f"nidan:ratelimit:{client_ip}:{minute_bucket}"
        try:
            count = await redis_client.incr(key)
            if count == 1:
                await redis_client.expire(key, 65)
            return retry_after if int(count) > limit_per_min else None
        except Exception as exc:  # pragma: no cover
            logger.debug("Redis rate-limit fallback (%s)", exc)

    # Bounded in-memory fallback when Redis is absent
    if len(_local_rate_buckets) > 4096:
        _local_rate_buckets.clear()
    bucket_key = (client_ip, minute_bucket)
    current = _local_rate_buckets.get(bucket_key, 0) + 1
    _local_rate_buckets[bucket_key] = current
    return retry_after if current > limit_per_min else None


class ApiProblemException(Exception):
    """Domain error serialized as RFC 9457 Problem Details."""

    def __init__(
        self,
        *,
        status: int,
        title: str,
        detail: str,
        error_type: str = "urn:nidan:error",
        retryable: bool = False,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.status = status
        self.title = title
        self.detail = detail
        self.error_type = error_type
        self.retryable = retryable
        self.extra = extra or {}


def get_trace_id(request: Request) -> str:
    """Return the request's trace ID from middleware state or headers."""
    trace_id = getattr(request.state, "trace_id", None)
    if isinstance(trace_id, str) and trace_id:
        return trace_id
    return request.headers.get("traceparent") or uuid.uuid4().hex[:20]


def problem_json_response(
    request: Request,
    *,
    status: int,
    title: str,
    detail: str,
    error_type: str = "urn:nidan:error",
    retryable: bool = False,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Build an RFC 9457 JSONResponse without leaking internal details."""
    trace_id = get_trace_id(request)
    payload = ProblemDetails(
        type=error_type,
        title=title,
        status=status,
        detail=detail,
        trace_id=trace_id,
        retryable=retryable,
    ).model_dump(by_alias=True)
    if extra:
        payload.update(extra)
    return JSONResponse(
        status_code=status,
        content=payload,
        media_type="application/problem+json",
        headers={"X-Trace-Id": trace_id},
    )


def register_middleware_and_handlers(app: FastAPI) -> None:
    """Attach security headers, trace IDs, advisory check, and RFC 9457 handlers."""

    @app.middleware("http")
    async def request_context_and_security_headers(request: Request, call_next):
        trace_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:20]
        request.state.trace_id = trace_id

        # Belt-and-suspenders guard: reject any path attempting a vital command surface.
        path_lower = request.url.path.lower()
        if any(seg in path_lower for seg in VITAL_CONTROL_PATTERNS) and path_lower.endswith(
            "/command"
        ):
            return problem_json_response(
                request,
                status=403,
                title="Advisory boundary enforced",
                detail=(
                    "NIDAN is strictly advisory and non-vital. No interlocking, signal, "
                    "route, points, or track-circuit command path exists."
                ),
                error_type="urn:nidan:advisory-only",
                retryable=False,
            )

        settings = getattr(request.app.state, "settings", None)
        limit_per_min = getattr(settings, "rate_limit_per_min", 0)
        retry_after = await _check_rate_limit(request, limit_per_min)
        if retry_after is not None:
            resp = problem_json_response(
                request,
                status=429,
                title="Rate limit exceeded",
                detail=f"Exceeded {limit_per_min} requests/minute. Retry after {retry_after}s.",
                error_type="urn:nidan:rate-limited",
                retryable=True,
            )
            resp.headers["Retry-After"] = str(retry_after)
            return resp

        start = time.perf_counter()
        response = await call_next(request)
        duration_s = time.perf_counter() - start
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path)
        metrics_registry.record_http(
            request.method,
            route_path,
            response.status_code,
            duration_s,
        )
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["X-NIDAN-Mode"] = "advisory-non-vital"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; frame-ancestors 'none'; object-src 'none'"
        )
        return response

    @app.exception_handler(ApiProblemException)
    async def api_problem_handler(request: Request, exc: ApiProblemException) -> JSONResponse:
        return problem_json_response(
            request,
            status=exc.status,
            title=exc.title,
            detail=exc.detail,
            error_type=exc.error_type,
            retryable=exc.retryable,
            extra=exc.extra,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first_msg = errors[0].get("msg", "Validation failed") if errors else "Validation failed"
        return problem_json_response(
            request,
            status=422,
            title="Validation failed",
            detail=str(first_msg),
            error_type="urn:nidan:validation-error",
            retryable=False,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return problem_json_response(
            request,
            status=exc.status_code,
            title="Request failed",
            detail=str(exc.detail),
            error_type="urn:nidan:http-error",
            retryable=exc.status_code >= 500,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error trace_id=%s: %s", get_trace_id(request), exc)
        return problem_json_response(
            request,
            status=500,
            title="Internal server error",
            detail="An unexpected internal error occurred. Quote traceId when reporting.",
            error_type="urn:nidan:internal-error",
            retryable=True,
        )
