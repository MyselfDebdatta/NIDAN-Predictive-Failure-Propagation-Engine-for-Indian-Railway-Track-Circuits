"""Lightweight in-process Prometheus-format metrics collector for NIDAN."""

from __future__ import annotations

import threading
from collections import defaultdict


class MetricsRegistry:
    """Thread-safe counters and latency summaries rendered in Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._http_requests: dict[tuple[str, str, int], int] = defaultdict(int)
        self._http_duration_sum: dict[tuple[str, str], float] = defaultdict(float)
        self._http_duration_count: dict[tuple[str, str], int] = defaultdict(int)
        self._observations: dict[str, int] = defaultdict(int)
        self._telemetry_samples: dict[str, int] = defaultdict(int)
        self._model_runs: dict[str, int] = defaultdict(int)

    def record_http(self, method: str, path: str, status: int, duration_s: float) -> None:
        with self._lock:
            self._http_requests[(method, path, status)] += 1
            self._http_duration_sum[(method, path)] += duration_s
            self._http_duration_count[(method, path)] += 1

    def record_observation(self, outcome: str) -> None:
        """Record field observation outcome: created | replayed | conflict."""
        with self._lock:
            self._observations[outcome] += 1

    def record_telemetry(self, quality_label: str, count: int = 1) -> None:
        """Record ingested telemetry sample counts by quality: measured|interpolated|suspect."""
        with self._lock:
            self._telemetry_samples[quality_label] += count

    def record_model_run(self, status: str) -> None:
        """Record model_run outcome: succeeded | replayed | failed."""
        with self._lock:
            self._model_runs[status] += 1

    def render_prometheus(
        self,
        *,
        ws_connections: int,
        db_pool_size: int,
        db_pool_idle: int,
    ) -> str:
        """Render all metrics in Prometheus 0.0.4 exposition format."""
        lines: list[str] = [
            "# HELP nidan_http_requests_total Total HTTP requests handled by NIDAN API.",
            "# TYPE nidan_http_requests_total counter",
        ]
        with self._lock:
            for (method, path, status), count in sorted(self._http_requests.items()):
                lbl = f'method="{method}",path="{path}",status="{status}"'
                lines.append(f"nidan_http_requests_total{{{lbl}}} {count}")

            lines.extend(
                [
                    "# HELP nidan_http_request_duration_seconds_sum Total HTTP latency (s).",
                    "# TYPE nidan_http_request_duration_seconds_sum counter",
                ]
            )
            for (method, path), total in sorted(self._http_duration_sum.items()):
                lbl = f'method="{method}",path="{path}"'
                lines.append(f"nidan_http_request_duration_seconds_sum{{{lbl}}} {total:.6f}")

            lines.extend(
                [
                    "# HELP nidan_http_request_duration_seconds_count Timed HTTP requests.",
                    "# TYPE nidan_http_request_duration_seconds_count counter",
                ]
            )
            for (method, path), count in sorted(self._http_duration_count.items()):
                lbl = f'method="{method}",path="{path}"'
                lines.append(f"nidan_http_request_duration_seconds_count{{{lbl}}} {count}")

            lines.extend(
                [
                    "# HELP nidan_field_observations_total Field observation intake outcomes.",
                    "# TYPE nidan_field_observations_total counter",
                ]
            )
            for outcome in ("created", "replayed", "conflict"):
                val = self._observations[outcome]
                lines.append(f'nidan_field_observations_total{{outcome="{outcome}"}} {val}')

            lines.extend(
                [
                    "# HELP nidan_telemetry_samples_total Telemetry samples ingested by QC class.",
                    "# TYPE nidan_telemetry_samples_total counter",
                ]
            )
            for q_label in ("measured", "interpolated", "suspect"):
                val = self._telemetry_samples[q_label]
                lines.append(f'nidan_telemetry_samples_total{{quality="{q_label}"}} {val}')

            lines.extend(
                [
                    "# HELP nidan_model_runs_total Atomic model-run publish outcomes.",
                    "# TYPE nidan_model_runs_total counter",
                ]
            )
            for status in ("succeeded", "replayed", "failed"):
                val = self._model_runs[status]
                lines.append(f'nidan_model_runs_total{{status="{status}"}} {val}')

        lines.extend(
            [
                "# HELP nidan_websocket_connections_active Active /v1/stream WebSocket clients.",
                "# TYPE nidan_websocket_connections_active gauge",
                f"nidan_websocket_connections_active {ws_connections}",
                "# HELP nidan_db_pool_size Current asyncpg connection pool size.",
                "# TYPE nidan_db_pool_size gauge",
                f"nidan_db_pool_size {db_pool_size}",
                "# HELP nidan_db_pool_idle Idle connections in asyncpg pool.",
                "# TYPE nidan_db_pool_idle gauge",
                f"nidan_db_pool_idle {db_pool_idle}",
                "",
            ]
        )
        return "\n".join(lines)


metrics_registry = MetricsRegistry()
