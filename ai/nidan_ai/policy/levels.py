"""Deterministic policy handoff: risk -> level, rank inputs and persistence.

The model outputs calibrated quantities; this module turns them into the level and rank a
human sees. Thresholds are exactly the frozen contract rules (spec §3, §11.1). Hysteresis and
persistence are derived from stored history, never from randomness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nidan_ai.config import (
    CRITICAL_H24,
    WARNING_H72,
    WATCH_H7D,
    WATCH_P10_DAYS,
)

_CONSEQUENCE_WEIGHT = {"high": 1.0, "medium": 0.7, "low": 0.4}


@dataclass(slots=True)
class LevelDecision:
    """One policy decision for an asset."""

    asset_id: str
    level: str
    driving_horizon: str
    calibrated_risk: float
    consequence: str
    consequence_note: str
    exposure: str
    trust_discount: float
    tie_breaker: str
    persistence: int
    policy_rank: int = 0
    h24: float = 0.0
    h72: float = 0.0
    h7d: float = 0.0
    p10_days: int = 0

    def rank_key(self) -> tuple[float, str]:
        score = (
            self.calibrated_risk
            * _CONSEQUENCE_WEIGHT.get(self.consequence, 0.4)
            * max(self.trust_discount, 0.05)
        )
        return (-round(score, 9), self.asset_id)


def decide_level(
    *,
    h24: float,
    h72: float,
    h7d: float,
    cluster_root: bool = False,
) -> tuple[str, str, float]:
    """Return (level, driving horizon, calibrated risk) under the frozen rules."""
    if h24 > CRITICAL_H24 or cluster_root:
        return "critical", "h24", float(h24)
    if h72 > WARNING_H72:
        return "warning", "h72", float(h72)
    return "watch", "h7d", float(h7d)


def consequence_for(
    *,
    traffic_per_day: int,
    route: str,
    level: str,
    parallel_detection: bool = False,
) -> tuple[str, str]:
    """Traffic, alternative detection and failure cost -> consequence."""
    main_line = any(token in route.lower() for token in ("main", "goods", "loop"))
    if traffic_per_day >= 80 and main_line and not parallel_detection:
        return "high", f"{route}, {traffic_per_day} movements/day, no parallel detection"
    if traffic_per_day >= 40 or level in {"critical", "warning"}:
        return "medium", f"{route}, {traffic_per_day} movements/day"
    return "low", f"{route}, {traffic_per_day} movements/day"


def make_decision(
    *,
    asset_id: str,
    h24: float,
    h72: float,
    h7d: float,
    p10_days: int,
    persistence: int,
    trust_score: float,
    traffic_per_day: int,
    route: str,
    cluster_root: bool = False,
    parallel_detection: bool = False,
) -> LevelDecision:
    """Build the full policy decision for one asset."""
    level, horizon, calibrated = decide_level(h24=h24, h72=h72, h7d=h7d, cluster_root=cluster_root)
    consequence, note = consequence_for(
        traffic_per_day=traffic_per_day,
        route=route,
        level=level,
        parallel_detection=parallel_detection,
    )
    trust_discount = float(min(1.0, max(0.05, trust_score)))
    tie_breaker = (
        f"{level}:{horizon}={calibrated:.4f};h7d={h7d:.4f};p10={p10_days}d;"
        f"persistence={persistence}"
    )
    return LevelDecision(
        asset_id=asset_id,
        level=level,
        driving_horizon=horizon,
        calibrated_risk=calibrated,
        consequence=consequence,
        consequence_note=note,
        exposure=f"{route}, {traffic_per_day} movements/day",
        trust_discount=trust_discount,
        tie_breaker=tie_breaker,
        persistence=persistence,
        h24=float(h24),
        h72=float(h72),
        h7d=float(h7d),
        p10_days=int(p10_days),
    )


def assign_ranks(decisions: list[LevelDecision]) -> list[LevelDecision]:
    """Sort by documented rank key and assign unique 1-based policy ranks."""
    ordered = sorted(decisions, key=lambda decision: decision.rank_key())
    for rank, decision in enumerate(ordered, start=1):
        decision.policy_rank = rank
    return ordered


def is_publishable(decision: LevelDecision, *, data_flags: list[str] | None = None) -> bool:
    """Whether an assessment is alert-worthy under the Watch rule.

    Healthy circuits below Watch are logged but not published as alerts; the contract has no
    "info" level, so publishing them as Watch would manufacture alarm fatigue.
    """
    if decision.level in {"warning", "critical"}:
        return True
    if decision.h7d > WATCH_H7D or decision.p10_days < WATCH_P10_DAYS:
        return True
    if decision.persistence >= 2:
        return True
    return bool(data_flags)


@dataclass(slots=True)
class PersistenceTracker:
    """Consecutive-window persistence derived from stored history."""

    threshold: float = WATCH_H7D
    history: dict[str, list[float]] = field(default_factory=dict)

    def update(self, asset_id: str, risk: float) -> int:
        values = self.history.setdefault(asset_id, [])
        values.append(float(risk))
        count = 0
        for value in reversed(values):
            if value >= self.threshold:
                count += 1
            else:
                break
        return count

    def persistence(self, asset_id: str) -> int:
        count = 0
        for value in reversed(self.history.get(asset_id, [])):
            if value >= self.threshold:
                count += 1
            else:
                break
        return count
