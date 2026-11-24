"""Field tablet task and offline-first observation models."""

from __future__ import annotations

from typing import Literal

from app.models.alerts import AlertLevel
from app.models.common import CamelModel, ModelVersions


class FieldMeasurements(CamelModel):
    """Measured or confirmed field telemetry values (string-encoded per form spec)."""

    relay_current: str
    ballast_conductance: str
    cable_insulation: str
    feed_voltage: str


class FieldTask(CamelModel):
    """Bilingual field inspection task delivered to the tablet PWA."""

    id: str
    asset_id: str
    title: str
    title_hi: str
    route: str
    length_m: int
    block_id: str
    date: str
    start: str
    end: str
    level: AlertLevel
    hypothesis: str
    hypothesis_hi: str
    falsifier: str
    falsifier_hi: str
    last_readings: FieldMeasurements


class FieldSyncStatus(CamelModel):
    """Summary of field outbox synchronization status."""

    last_sync: str
    queued_offline: int


class FieldTasksResponse(CamelModel):
    """Response for GET /v1/field/tasks."""

    tasks: list[FieldTask]
    sync: FieldSyncStatus
    model_versions: ModelVersions
    generated_at: str


class FieldObservationRequest(CamelModel):
    """Idempotent field observation intake payload from Nidan-Frontend."""

    idempotency_key: str
    task_id: str
    finding: Literal["confirmed", "not-found", "something-else"]
    measurements: FieldMeasurements
    note: str = ""
    created_at: str


class FieldObservationReceipt(CamelModel):
    """Receipt returned on intake or idempotent replay."""

    queued: bool = True
    receipt: str
    replayed: bool = False
    model_versions: ModelVersions
    generated_at: str
