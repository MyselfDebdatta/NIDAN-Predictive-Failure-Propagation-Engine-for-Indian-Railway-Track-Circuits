"""Shadow-mode evaluation, 28-day registry, promotion gates, and rollback (spec §13, §15)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from nidan_ai.config import ECE_TARGET, PSI_THRESHOLD, RUL_COVERAGE_BAND

MIN_SHADOW_DAYS = 28.0
MAX_DIVISION_COVERAGE_GAP = 0.04


def _parse_iso(ts: str) -> datetime:
    cleaned = ts[:-1] + "+00:00" if ts.endswith("Z") else ts
    return datetime.fromisoformat(cleaned)


@dataclass(slots=True)
class ShadowObservation:
    """Single shadow or production evaluation snapshot recorded for promotion gating."""

    as_of: str
    ece: float
    coverage: float
    mean_set_size: float
    rul_coverage: float
    division_coverage_gap: float
    max_psi: float
    contract_valid: bool = True
    vital_writes: int = 0
    dataset_hash: str = ""
    bench_version: str = ""


@dataclass(slots=True)
class RegisteredVersion:
    """Registry record for one candidate or active model bundle version."""

    version: str
    state: str = "shadow"
    first_seen_at: str = ""
    last_seen_at: str = ""
    bench_hash: str = ""
    gate_results: list[dict[str, Any]] = field(default_factory=list)
    demotion_reasons: list[str] = field(default_factory=list)
    observations: list[ShadowObservation] = field(default_factory=list)

    @property
    def shadow_days(self) -> float:
        if not self.first_seen_at or not self.last_seen_at:
            return 0.0
        delta = _parse_iso(self.last_seen_at) - _parse_iso(self.first_seen_at)
        return max(0.0, float(delta.total_seconds() / 86400.0))


def evaluate_promotion_gates(
    obs: ShadowObservation,
    *,
    shadow_days: float,
    min_shadow_days: float = MIN_SHADOW_DAYS,
    max_division_gap: float = MAX_DIVISION_COVERAGE_GAP,
) -> tuple[bool, list[dict[str, Any]], list[str]]:
    """Evaluate all seven spec §13 promotion gates deterministically."""
    coverage_ok = bool(obs.coverage >= 0.88 and (obs.coverage <= 0.92 or obs.mean_set_size <= 1.05))
    rul_ok = bool(RUL_COVERAGE_BAND[0] <= obs.rul_coverage <= RUL_COVERAGE_BAND[1])
    gates = [
        {
            "name": "Calibration",
            "rule": f"ECE <= {ECE_TARGET:.2f} over 10 bins",
            "value": f"{obs.ece:.4f}",
            "pass": bool(obs.ece <= ECE_TARGET),
        },
        {
            "name": "Coverage",
            "rule": "Conformal coverage 0.88-0.92 (or singleton acc >= 0.92)",
            "value": f"{obs.coverage:.4f}",
            "pass": coverage_ok and rul_ok,
        },
        {
            "name": "Subgroup parity",
            "rule": f"Coverage gap <= {max_division_gap:.2f} across divisions",
            "value": f"{obs.division_coverage_gap:.4f}",
            "pass": bool(obs.division_coverage_gap <= max_division_gap),
        },
        {
            "name": "Drift",
            "rule": f"PSI <= {PSI_THRESHOLD:.2f} on monitored features",
            "value": f"{obs.max_psi:.4f}",
            "pass": bool(obs.max_psi <= PSI_THRESHOLD),
        },
        {
            "name": "Shadow period",
            "rule": f">= {int(min_shadow_days)} days in shadow",
            "value": f"{shadow_days:.1f} d",
            "pass": bool(shadow_days >= min_shadow_days),
        },
        {
            "name": "Safety",
            "rule": "Zero vital-path endpoints or writes",
            "value": str(int(obs.vital_writes)),
            "pass": bool(obs.vital_writes == 0),
        },
        {
            "name": "Contract",
            "rule": "All rows validate against Pydantic models",
            "value": "valid" if obs.contract_valid else "invalid",
            "pass": bool(obs.contract_valid),
        },
    ]
    failures = [f"{g['name']} ({g['value']} vs {g['rule']})" for g in gates if not g["pass"]]
    return (len(failures) == 0, gates, failures)


@dataclass(slots=True)
class ModelRegistry:
    """Pointer-based model version registry supporting shadow -> active and rollback."""

    active_version: str | None = None
    previous_active_version: str | None = None
    versions: dict[str, RegisteredVersion] = field(default_factory=dict)

    @classmethod
    def load(cls, path: str | Path) -> ModelRegistry:
        target = Path(path)
        if not target.exists():
            return cls()
        raw = json.loads(target.read_text(encoding="utf-8"))
        versions: dict[str, RegisteredVersion] = {}
        for ver, item in (raw.get("versions") or {}).items():
            obs = [ShadowObservation(**o) for o in item.get("observations", [])]
            versions[ver] = RegisteredVersion(
                version=ver,
                state=item.get("state", "shadow"),
                first_seen_at=item.get("first_seen_at", ""),
                last_seen_at=item.get("last_seen_at", ""),
                bench_hash=item.get("bench_hash", ""),
                gate_results=list(item.get("gate_results", [])),
                demotion_reasons=list(item.get("demotion_reasons", [])),
                observations=obs,
            )
        return cls(
            active_version=raw.get("active_version"),
            previous_active_version=raw.get("previous_active_version"),
            versions=versions,
        )

    def save(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "active_version": self.active_version,
            "previous_active_version": self.previous_active_version,
            "versions": {
                ver: {
                    "version": entry.version,
                    "state": entry.state,
                    "first_seen_at": entry.first_seen_at,
                    "last_seen_at": entry.last_seen_at,
                    "bench_hash": entry.bench_hash,
                    "gate_results": entry.gate_results,
                    "demotion_reasons": entry.demotion_reasons,
                    "observations": [asdict(o) for o in entry.observations[-30:]],
                }
                for ver, entry in sorted(self.versions.items())
            },
        }
        target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return target

    def record_observation(
        self,
        version: str,
        obs: ShadowObservation,
        *,
        bench_hash: str = "",
        promote_if_ready: bool = False,
        min_shadow_days: float = MIN_SHADOW_DAYS,
    ) -> RegisteredVersion:
        """Record a shadow/validation observation and evaluate all §13 promotion gates."""
        entry = self.versions.get(version)
        if entry is None:
            entry = RegisteredVersion(
                version=version,
                state="shadow",
                first_seen_at=obs.as_of,
                last_seen_at=obs.as_of,
                bench_hash=bench_hash,
            )
            self.versions[version] = entry
        else:
            if not entry.first_seen_at or _parse_iso(obs.as_of) < _parse_iso(entry.first_seen_at):
                entry.first_seen_at = obs.as_of
            if not entry.last_seen_at or _parse_iso(obs.as_of) > _parse_iso(entry.last_seen_at):
                entry.last_seen_at = obs.as_of
            if bench_hash:
                entry.bench_hash = bench_hash

        # Deduplicate exact timestamp observations cleanly
        if not any(existing.as_of == obs.as_of for existing in entry.observations):
            entry.observations.append(obs)

        passed, gates, failures = evaluate_promotion_gates(
            obs, shadow_days=entry.shadow_days, min_shadow_days=min_shadow_days
        )
        entry.gate_results = gates
        if passed and promote_if_ready:
            if self.active_version and self.active_version != version:
                self.previous_active_version = self.active_version
                prev = self.versions.get(self.active_version)
                if prev is not None and prev.state == "active":
                    prev.state = "retired"
            entry.state = "active"
            entry.demotion_reasons = []
            self.active_version = version
        elif not passed:
            entry.state = "shadow"
            entry.demotion_reasons = failures
            if self.active_version == version:
                self.rollback(reason="; ".join(failures))
        return entry

    def rollback(self, *, reason: str = "gate failure") -> str | None:
        """Flip pointer back to ``previous_active_version`` without redeploy."""
        cur = self.active_version
        if cur and cur in self.versions:
            self.versions[cur].state = "shadow"
            if reason and reason not in self.versions[cur].demotion_reasons:
                self.versions[cur].demotion_reasons.append(reason)
        if self.previous_active_version and self.previous_active_version in self.versions:
            self.active_version = self.previous_active_version
            self.versions[self.active_version].state = "active"
            return self.active_version
        self.active_version = None
        return None
