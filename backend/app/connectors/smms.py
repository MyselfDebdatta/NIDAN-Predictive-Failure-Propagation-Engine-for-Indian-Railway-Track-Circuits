"""Read-only CRIS SMMS sync adapter.

Imports track-circuit master register metadata (into ``asset`` and
``asset_record_source``) and confirmed historical failure precedents (into
``smms_precedent``).  Strictly one-way read/sync: holds no write path to
CRIS SMMS work-order submission or any vital railway signalling system.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.cache import RedisCache
from app.metrics import metrics_registry
from app.models.common import CamelModel, utc_now_iso
from app.services.repository import NidanRepository


def _parse_date(val: Any) -> date | None:
    if val is None or val == "":
        return None
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    return date.fromisoformat(str(val)[:10])


class SmmsAssetRecord(CamelModel):
    """Read-only track-circuit master record exported from CRIS SMMS."""

    id: str = Field(min_length=3, max_length=64)
    division_id: str = Field(min_length=2, max_length=16)
    name: str = Field(min_length=1, max_length=200)
    route: str = Field(min_length=1, max_length=200)
    circuit_type: Literal["DC", "AC"] = "DC"
    length_m: int = Field(gt=0)
    installed_on: date | None = None
    codal_life_years: int | None = Field(default=15, gt=0)
    relay_model: str | None = None
    supply_id: str | None = None
    cable_id: str | None = None
    relay_room_id: str | None = None
    weather_cell_id: str | None = None
    provenance: str = "CRIS SMMS asset register"
    fetched_at: datetime | None = None

    @field_validator("installed_on", mode="before")
    @classmethod
    def _coerce_installed_on(cls, v: Any) -> date | None:
        return _parse_date(v)


class SmmsPrecedentRecord(CamelModel):
    """Confirmed historical SMMS failure precedent (read-only reference)."""

    id: str = Field(min_length=3, max_length=64)
    asset_id: str | None = None
    division_id: str | None = None
    failure_mode: str | None = Field(default=None, pattern=r"^F(?:[1-9]|1[0-2])$")
    confirmed_cause: str = Field(min_length=3, max_length=500)
    occurred_on: date | None = None
    summary: str = ""
    provenance: str = "CRIS SMMS failure register"

    @field_validator("occurred_on", mode="before")
    @classmethod
    def _coerce_occurred_on(cls, v: Any) -> date | None:
        return _parse_date(v)


class SmmsSyncRequest(CamelModel):
    """One-way read-only SMMS sync batch."""

    assets: list[SmmsAssetRecord] = Field(default_factory=list, max_length=2000)
    precedents: list[SmmsPrecedentRecord] = Field(default_factory=list, max_length=2000)

    @model_validator(mode="after")
    def _require_non_empty(self) -> SmmsSyncRequest:
        if not self.assets and not self.precedents:
            raise ValueError("At least one asset or precedent record is required.")
        return self


class SmmsSyncResponse(CamelModel):
    """Confirmation of one-way read-only SMMS register sync."""

    assets_synced: int
    precedents_synced: int
    advisory_only: bool = True
    generated_at: str


class SmmsReadSyncAdapter:
    """Executes one-way SMMS master & precedent synchronization."""

    def __init__(
        self,
        repo: NidanRepository,
        *,
        cache: RedisCache | None = None,
    ) -> None:
        self.repo = repo
        self.cache = cache

    async def sync(self, request: SmmsSyncRequest) -> SmmsSyncResponse:
        now = datetime.now(UTC)
        asset_dicts = [
            {
                **a.model_dump(by_alias=True),
                "fetchedAt": a.fetched_at or now,
            }
            for a in request.assets
        ]
        precedent_dicts = [p.model_dump(by_alias=True) for p in request.precedents]

        counts = await self.repo.sync_smms_snapshot(
            assets=asset_dicts,
            precedents=precedent_dicts,
        )
        metrics_registry.record_smms_sync("asset", counts["assets_synced"])
        metrics_registry.record_smms_sync("precedent", counts["precedents_synced"])

        if self.cache is not None:
            await self.cache.invalidate_prefixes("assets:", "alerts:")

        return SmmsSyncResponse(
            assets_synced=counts["assets_synced"],
            precedents_synced=counts["precedents_synced"],
            advisory_only=True,
            generated_at=utc_now_iso(),
        )
