"""Atomic HTTP publisher for telemetry batches and model-run snapshots.

Strictly advisory and non-vital: only calls ``POST /v1/ingest/telemetry`` and
``POST /v1/ingest/model-run`` for writes, plus read-only ``GET /v1/alerts`` and
``GET /v1/blocks`` when discovering existing registered assets/windows.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from nidan_ai.config import ALLOWED_INGEST_PATHS, Settings, get_settings
from nidan_ai.schemas import validate_publish_payload

_LOGGER = logging.getLogger("nidan_ai.publish")
_RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


class PublishError(RuntimeError):
    """Raised when telemetry or model-run publication fails closed."""


@dataclass(slots=True)
class PublishSummary:
    """Result of publishing telemetry batches and one atomic model-run."""

    telemetry_accepted: int
    telemetry_deduplicated: int
    batches_sent: int
    model_run_id: str
    snapshot_id: str
    assessments_written: int
    alerts_updated: int
    events_published: list[str]
    idempotent_replay: bool


class PublishClient:
    """Bounded-backoff ``httpx`` client restricted to the two allowed ingest routes."""

    def __init__(
        self,
        settings: Settings | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.settings.auth_token:
            headers["Authorization"] = f"Bearer {self.settings.auth_token}"
        self._client = httpx.Client(
            base_url=self.settings.api_base_url.rstrip("/"),
            headers=headers,
            timeout=self.settings.request_timeout_seconds,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> PublishClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request_with_backoff(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        if method.upper() not in {"GET", "POST"}:
            raise PublishError(f"Disallowed HTTP method: {method}")
        if method.upper() == "POST" and path not in ALLOWED_INGEST_PATHS:
            raise PublishError(
                f"Refusing outbound write to non-ingest path {path!r}; "
                f"allowed={ALLOWED_INGEST_PATHS}"
            )
        attempts = max(1, self.settings.max_retries + 1)
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                response = self._client.request(method, path, json=json_body)
            except httpx.TransportError as exc:
                last_exc = exc
                if attempt + 1 >= attempts:
                    break
                time.sleep(self.settings.retry_backoff_seconds * (2**attempt))
                continue

            if response.status_code in _RETRYABLE_STATUS and attempt + 1 < attempts:
                time.sleep(self.settings.retry_backoff_seconds * (2**attempt))
                continue

            if response.status_code >= 400:
                detail = response.text[:500]
                raise PublishError(
                    f"{method} {path} failed with HTTP {response.status_code}: {detail}"
                )
            return response

        raise PublishError(f"{method} {path} failed after {attempts} attempts: {last_exc}")

    def fetch_alerts(self) -> list[dict[str, Any]]:
        """Read-only fetch of existing alerts/registered assets on the target API."""
        response = self._request_with_backoff("GET", "/v1/alerts")
        data = response.json()
        return list(data) if isinstance(data, list) else []

    def fetch_blocks(self) -> dict[str, Any]:
        """Read-only fetch of published Rolling Block windows."""
        response = self._request_with_backoff("GET", "/v1/blocks")
        data = response.json()
        return dict(data) if isinstance(data, dict) else {}

    def publish_telemetry(
        self,
        samples: list[dict[str, Any]],
        *,
        batch_size: int | None = None,
    ) -> tuple[int, int, int]:
        """Chunk telemetry samples (<= 5000/request) and POST to /v1/ingest/telemetry."""
        if not samples:
            return 0, 0, 0
        limit = min(5000, batch_size or self.settings.telemetry_batch_size)
        accepted = 0
        deduplicated = 0
        batches = 0
        for start in range(0, len(samples), limit):
            chunk = samples[start : start + limit]
            response = self._request_with_backoff(
                "POST",
                "/v1/ingest/telemetry",
                json_body={"samples": chunk, "sourceProtocol": "canonical"},
            )
            body = response.json()
            accepted += int(body.get("accepted", 0))
            deduplicated += int(body.get("deduplicated", 0))
            batches += 1
        return accepted, deduplicated, batches

    def publish_model_run(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Validate locally (fail closed) and POST atomically to /v1/ingest/model-run."""
        validated = validate_publish_payload(payload)
        wire = validated.model_dump(by_alias=True, mode="json")
        response = self._request_with_backoff("POST", "/v1/ingest/model-run", json_body=wire)
        result = dict(response.json())
        if result.get("idempotentReplay"):
            _LOGGER.info(
                "Idempotent replay acknowledged for snapshot=%s model_run=%s",
                result.get("snapshotId"),
                result.get("modelRunId"),
            )
        return result


def publish_snapshot(
    *,
    payload: dict[str, Any],
    samples: list[dict[str, Any]] | None = None,
    settings: Settings | None = None,
    transport: httpx.BaseTransport | None = None,
) -> PublishSummary:
    """Validate payload, push telemetry batches if given, and publish model-run atomically."""
    validate_publish_payload(payload)
    with PublishClient(settings=settings, transport=transport) as client:
        accepted, deduplicated, batches = client.publish_telemetry(samples or [])
        result = client.publish_model_run(payload)
        return PublishSummary(
            telemetry_accepted=accepted,
            telemetry_deduplicated=deduplicated,
            batches_sent=batches,
            model_run_id=str(result.get("modelRunId", "")),
            snapshot_id=str(result.get("snapshotId", "")),
            assessments_written=int(result.get("assessmentsWritten", 0)),
            alerts_updated=int(result.get("alertsUpdated", 0)),
            events_published=list(result.get("eventsPublished", [])),
            idempotent_replay=bool(result.get("idempotentReplay", False)),
        )
