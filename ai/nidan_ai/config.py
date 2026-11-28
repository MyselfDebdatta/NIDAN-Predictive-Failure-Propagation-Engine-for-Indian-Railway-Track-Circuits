"""Configuration, version pins, seeds and policy thresholds for the NIDAN AI engine.

Everything that affects a published number is pinned here so a `model_run` can be replayed.
No wall-clock value is ever read into a payload; `computedAt` derives from the snapshot.
"""

from __future__ import annotations

import os
import random
from functools import lru_cache
from pathlib import Path

import numpy as np
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Version pins. Bump deliberately; each appears in every model_versions record.
CODE_VERSION = "nidan-ai/0.1.0"
TWIN_VERSION = "0.3.1"
CLASSIFIER_VERSION = "0.2.0"
GNN_VERSION = "0.2.0"
SURVIVAL_VERSION = "0.2.4"
CONFORMAL_VERSION = "0.1.3"
BENCH_VERSION = "nidan-bench/0.1"
POLICY_VERSION = "policy-2026.07"

# Policy thresholds (spec §11.1). The contract re-checks critical/warning server-side.
CRITICAL_H24 = 0.5
WARNING_H72 = 0.3
WATCH_H7D = 0.20
WATCH_P10_DAYS = 30

# Conformal and calibration targets (spec §10, §13).
CONFORMAL_TARGET = 0.90
CONFORMAL_TOLERANCE = (0.88, 0.92)
RUL_NOMINAL = 0.80
RUL_COVERAGE_BAND = (0.75, 0.85)
ECE_TARGET = 0.05
PSI_THRESHOLD = 0.20

# Deterministic float precision used before hashing canonical JSON.
HASH_PRECISION = 6

# Signal keys used by the canonical telemetry contract and the bench.
SIGNAL_KEYS = (
    "relay_i",
    "feed_v",
    "rain_mm",
    "temp_c",
    "humidity_pct",
    "neighbour_i",
    "harmonic_mv",
    "occupancy",
    "drop_ms",
    "pickup_ms",
    "cable_ir",
    "axle_occupied",
)

FAILURE_MODES = ("F1", "F2", "F3", "F4", "F5", "F6", "F7", "F8", "F9", "F10", "F11", "F12")

# First-release diagnosis scope (spec §8.2). Other modes remain advisory-only.
RELEASE_MODES = ("F1", "F3", "F5", "F6", "F12")

TRUST_FLAGS = frozenset(
    {
        "logger_gap_6h",
        "stuck_value_run",
        "age_vs_signature_mismatch",
        "shunt_pattern_review",
        "predicted_cascade",
        "clock_skew",
    }
)

# The only outbound write routes the engine is allowed to call.
ALLOWED_INGEST_PATHS = ("/v1/ingest/telemetry", "/v1/ingest/model-run")


class Settings(BaseSettings):
    """Environment-driven settings. Prefix every variable with ``NIDAN_AI_``."""

    model_config = SettingsConfigDict(
        env_prefix="NIDAN_AI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    seed: int = 42
    bench_version: str = BENCH_VERSION
    policy_version: str = POLICY_VERSION
    code_version: str = CODE_VERSION

    api_base_url: str = "http://127.0.0.1:8000"
    auth_mode: str = "dev"
    auth_token: str | None = None
    request_timeout_seconds: float = 30.0
    max_retries: int = 3
    retry_backoff_seconds: float = 0.5

    artifact_dir: Path = Field(default=Path("artifacts"))
    report_dir: Path = Field(default=Path("reports"))

    critical_h24: float = CRITICAL_H24
    warning_h72: float = WARNING_H72
    watch_h7d: float = WATCH_H7D
    watch_p10_days: int = WATCH_P10_DAYS

    max_assets: int = 500
    telemetry_batch_size: int = 5000

    def ensure_dirs(self) -> None:
        """Create gitignored output directories if they do not exist."""
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()


def seed_everything(seed: int | None = None) -> int:
    """Pin Python, NumPy and (when present) torch RNGs for a reproducible run."""
    value = get_settings().seed if seed is None else int(seed)
    random.seed(value)
    np.random.seed(value)
    os.environ.setdefault("PYTHONHASHSEED", str(value))
    try:  # optional dependency; only used by the A4 graph extra
        import torch

        torch.manual_seed(value)
        torch.use_deterministic_algorithms(True, warn_only=True)
        torch.set_num_threads(1)
    except Exception:  # pragma: no cover - torch absent is the default path
        pass
    return value
