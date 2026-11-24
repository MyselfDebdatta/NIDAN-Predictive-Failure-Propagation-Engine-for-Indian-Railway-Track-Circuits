"""Rolling Block windows and scheduled job models."""

from __future__ import annotations

from typing import Literal

from app.models.common import CamelModel, ModelVersions

BlockFit = Literal["fits", "extends", "special", "none"]
BlockKind = Literal["published", "draft"]


class BlockWindow(CamelModel):
    """Published or draft Rolling Block maintenance window."""

    id: str
    date: str
    start: str
    end: str
    duration_min: int
    kind: BlockKind


class AlertBlockInfo(CamelModel):
    """Block assignment paired with an alert assessment."""

    window: BlockWindow
    fit: BlockFit
    minutes: int


class BlockJob(CamelModel):
    """Maintenance job mapped to assets and a Rolling Block window."""

    id: str
    title: str
    assets: list[str]
    block_id: str | None = None
    duration_min: int
    fit: BlockFit
    crew: str


class BlocksResponse(CamelModel):
    """Response for GET /v1/blocks."""

    windows: list[BlockWindow]
    jobs: list[BlockJob]
    model_versions: ModelVersions
    generated_at: str
