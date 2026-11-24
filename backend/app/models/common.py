"""Shared Pydantic base models, model lineage, and RFC 9457 error payload."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    """Base model serializing all fields in camelCase to match frontend contracts."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ModelVersions(CamelModel):
    """Pinned model versions accompanying every advisory score."""

    twin: str = "0.3.1"
    gnn: str = "0.2.0"
    survival: str = "0.2.4"
    classifier: str = "0.2.0"


class ProblemDetails(CamelModel):
    """RFC 9457 problem details payload returned for all API errors."""

    type: str
    title: str
    status: int
    detail: str
    trace_id: str
    retryable: bool = False


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO 8601 Z format."""
    return datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
