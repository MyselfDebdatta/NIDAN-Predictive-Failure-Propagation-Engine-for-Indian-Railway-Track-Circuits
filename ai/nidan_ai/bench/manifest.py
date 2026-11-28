"""NIDAN-Bench manifest: canonical JSON and SHA-256 over generator + scenarios + seeds.

A metric without its bench version and hash is not reproducible, so the hash travels in
every ``model_run`` payload as ``datasetHash``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

import numpy as np

from nidan_ai.config import BENCH_VERSION, HASH_PRECISION


def _canonical_value(value: Any, precision: int) -> Any:
    if isinstance(value, dict):
        return {str(key): _canonical_value(value[key], precision) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [_canonical_value(item, precision) for item in value]
    if isinstance(value, np.ndarray):
        return _canonical_value(value.tolist(), precision)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        rounded = round(float(value), precision)
        if rounded == 0.0:
            return 0.0
        return rounded
    if isinstance(value, np.bool_):
        return bool(value)
    if value is None or isinstance(value, (str, int, bool)):
        return value
    raise TypeError(f"Cannot canonicalise value of type {type(value)!r}")


def canonical_json(value: Any, precision: int = HASH_PRECISION) -> str:
    """Deterministic JSON: sorted keys, fixed float precision, no NaN, compact separators."""
    return json.dumps(
        _canonical_value(value, precision),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_canonical(value: Any, precision: int = HASH_PRECISION) -> str:
    """SHA-256 of the canonical JSON representation."""
    return hashlib.sha256(canonical_json(value, precision).encode("utf-8")).hexdigest()


def stable_id(*parts: Any, length: int = 16) -> str:
    """Deterministic short id derived from stable inputs (never from time or randomness)."""
    digest = sha256_canonical(list(parts))
    return digest[:length]


@dataclass(frozen=True, slots=True)
class BenchManifest:
    """Versioned, hashed description of a bench run."""

    version: str
    generator: str
    scenarios: dict[str, Any]
    seeds: tuple[int, ...]
    hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generator": self.generator,
            "scenarios": self.scenarios,
            "seeds": list(self.seeds),
            "hash": self.hash,
        }


def build_manifest(
    scenarios: dict[str, Any],
    seeds: list[int] | tuple[int, ...],
    *,
    version: str = BENCH_VERSION,
    generator: str = "nidan_ai.bench.generator/1",
) -> BenchManifest:
    """Build a manifest and its stable hash from scenario definitions and seeds."""
    ordered_seeds = tuple(sorted(int(seed) for seed in seeds))
    body = {
        "version": version,
        "generator": generator,
        "scenarios": scenarios,
        "seeds": list(ordered_seeds),
    }
    return BenchManifest(
        version=version,
        generator=generator,
        scenarios=scenarios,
        seeds=ordered_seeds,
        hash=sha256_canonical(body),
    )
