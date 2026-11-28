"""Precedent retrieval over real confirmed SMMS/event rows.

No synthetic case may be presented as history. Similarity is a scaled Euclidean distance over
a small set of stable features, plus same-mode and same-station bonuses; a confirmed cause is
required and the threshold is 0.6. An empty list is a valid answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

import numpy as np

from nidan_ai.data.canonical import parse_utc
from nidan_ai.data.features import FeatureVector

_SIMILARITY_FEATURES = (
    "margin_ratio",
    "gb_ratio",
    "drop_p95_ms",
    "rain_72h",
    "age_ratio",
)
_SCALES = {
    "margin_ratio": 0.25,
    "gb_ratio": 0.50,
    "drop_p95_ms": 300.0,
    "rain_72h": 40.0,
    "age_ratio": 0.5,
}


@dataclass(slots=True)
class Precedent:
    """One confirmed historical event."""

    smms_id: str
    asset_id: str
    confirmed_mode: str
    similarity: float
    days_ago: int
    outcome: str
    station: str
    feature_vector: dict[str, float] = field(default_factory=dict)


class PrecedentIndex:
    """In-memory index of real event rows, with a cache keyed by assessment hash."""

    def __init__(self, events: list[dict]) -> None:
        self.events = [event for event in events if event.get("confirmedMode") or event.get("mode")]
        self._cache: dict[str, list[Precedent]] = {}

    def retrieve(
        self,
        vector: FeatureVector,
        *,
        as_of: datetime | str,
        top_k: int = 3,
        threshold: float = 0.6,
        cache_key: str | None = None,
    ) -> list[Precedent]:
        if cache_key is not None and cache_key in self._cache:
            return self._cache[cache_key]
        resolved_as_of = parse_utc(as_of)
        candidates: list[Precedent] = []
        for event in self.events:
            mode = str(event.get("confirmedMode") or event.get("mode") or "")
            if not mode:
                continue
            event_time = parse_utc(event["eventTime"])
            days_ago = max(0, int((resolved_as_of - event_time).total_seconds() // 86400))
            if days_ago <= 0:
                continue
            distance = 0.0
            count = 0
            for name in _SIMILARITY_FEATURES:
                other = event.get("featureVector", {}).get(name)
                if other is None:
                    continue
                scale = _SCALES[name]
                distance += ((vector.get(name) - float(other)) / scale) ** 2
                count += 1
            if count == 0:
                continue
            similarity = 1.0 / (1.0 + np.sqrt(distance / count))
            if mode == str(event.get("mode") or ""):
                similarity += 0.05
            if event.get("station") and event.get("station") == vector.asset_id.split("/")[0]:
                similarity += 0.05
            similarity = float(np.clip(similarity, 0.0, 1.0))
            if similarity < threshold:
                continue
            candidates.append(
                Precedent(
                    smms_id=str(event.get("smmsId") or event.get("smms_id") or ""),
                    asset_id=str(event.get("assetId") or event.get("asset_id") or ""),
                    confirmed_mode=mode,
                    similarity=similarity,
                    days_ago=days_ago,
                    outcome=str(event.get("outcome") or "Confirmed"),
                    station=str(event.get("station") or ""),
                    feature_vector=dict(event.get("featureVector", {})),
                )
            )
        candidates.sort(key=lambda item: (-item.similarity, item.smms_id))
        result = candidates[:top_k]
        if cache_key is not None:
            self._cache[cache_key] = result
        return result
