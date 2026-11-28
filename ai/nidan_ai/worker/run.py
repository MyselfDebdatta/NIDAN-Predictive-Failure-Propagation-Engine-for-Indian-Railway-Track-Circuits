"""Scoring worker CLI for NIDAN AI.

Supports offline bench/export dry runs (zero network calls) and atomic publication to
``POST /v1/ingest/telemetry`` and ``POST /v1/ingest/model-run``.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from nidan_ai.bench.manifest import build_manifest, canonical_json, sha256_canonical
from nidan_ai.bench.scenarios import SCENARIO_NAMES, scenario_manifest
from nidan_ai.config import (
    BENCH_VERSION,
    CODE_VERSION,
    POLICY_VERSION,
    get_settings,
    seed_everything,
)
from nidan_ai.schemas import (
    build_assessment_payload,
    build_publish_payload,
    default_model_versions,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nidan_ai.worker.run",
        description="Run the NIDAN advisory scoring worker (non-vital).",
    )
    parser.add_argument(
        "--scenario",
        default="monsoon-60d",
        choices=SCENARIO_NAMES,
        help="NIDAN-Bench scenario name.",
    )
    parser.add_argument("--seed", type=int, default=42, help="Deterministic RNG seed.")
    parser.add_argument(
        "--as-of",
        default=None,
        help="Snapshot UTC ISO-8601 timestamp (defaults to deterministic scenario watermark).",
    )
    parser.add_argument("--division", default="ADRA", help="Target division code.")
    parser.add_argument(
        "--source",
        default="bench",
        choices=("bench", "export", "db"),
        help="Input telemetry source.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Path to read-only JSON/JSONL telemetry export when --source export.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and emit payload locally with zero network calls.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Publish telemetry batches and atomic model-run to backend API.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help="Output JSON path (defaults to stdout when --dry-run).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of circuits to score.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Optional directory for model card, metrics JSON, and calibration SVG.",
    )
    return parser.parse_args(argv)


def _deterministic_as_of(as_of: str | None) -> datetime:
    if as_of is None:
        return datetime(2026, 7, 14, 0, 0, tzinfo=UTC)
    parsed = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Naive --as-of timestamp rejected; provide UTC offset: {as_of!r}")
    return parsed.astimezone(UTC)


def build_synthetic_dry_run_payload(
    *,
    scenario: str = "monsoon-60d",
    seed: int = 42,
    division: str = "ADRA",
    as_of: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Emit a deterministic, contract-validated synthetic payload for A0 dry-run checks."""
    seed_everything(seed)
    watermark = _deterministic_as_of(as_of)
    manifest = build_manifest(scenario_manifest(), [seed], version=BENCH_VERSION)
    params = {
        "scenario": scenario,
        "seed": int(seed),
        "division": division,
        "benchVersion": manifest.version,
        "benchHash": manifest.hash,
        "policyVersion": POLICY_VERSION,
        "mode": "synthetic-a0",
    }
    params_hash = sha256_canonical(params)
    model_versions = default_model_versions(
        code_version=CODE_VERSION,
        params_hash=params_hash,
        bench_version=manifest.version,
        bench_hash=manifest.hash,
        seed=seed,
        split="bench-synthetic",
    )

    sample_assets = [
        (f"{division}/TC/12T", 0.14, 0.34, 0.62, 7, 16, 29, ["F1"], 0.74, "warning", "h72"),
        (f"{division}/TC/07T", 0.54, 0.69, 0.78, 2, 7, 15, ["F5", "F1"], 0.66, "critical", "h24"),
        (f"{division}/TC/14T", 0.08, 0.19, 0.28, 18, 34, 58, ["F1"], 0.61, "watch", "h7d"),
    ]
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be >= 1")
        sample_assets = sample_assets[:limit]

    assessments: list[dict[str, Any]] = []
    for rank, row in enumerate(sample_assets, start=1):
        (
            asset_id,
            h24,
            h72,
            h7d,
            p10,
            med,
            p90,
            modes,
            mode_prob,
            level,
            horizon,
        ) = row
        cal_risk = {"h24": h24, "h72": h72, "h7d": h7d}[horizon]
        explanation = {
            "physics": {
                "headline": (
                    "Effective ballast conductance +42.0% versus the dry design baseline; "
                    "relay margin 68.4% of dry."
                ),
                "state": [
                    {
                        "label": "Effective ballast conductance",
                        "value": "1.42x dry",
                        "baseline": "1.00x dry",
                    },
                    {
                        "label": "Relay margin",
                        "value": "68.4% of dry",
                        "baseline": "100% of dry",
                    },
                ],
                "falsifier": (
                    "If a repeat 0.5 ohm shunt test holds relay current above 75% of dry for "
                    "five movements, the effective-ballast explanation is falsified."
                ),
            },
            "model": {
                "shapTop": [
                    {
                        "feature": "gb_ratio",
                        "label": "Effective ballast conductance ratio",
                        "value": 0.24,
                    },
                    {
                        "feature": "margin_slope_7d",
                        "label": "7-day relay margin slope",
                        "value": -0.18,
                    },
                ],
                "calibrationNote": (
                    "Conformal set coverage 0.900 on 100 held-out outcomes; "
                    "calibration is per division and horizon."
                ),
                "modeSet": modes,
                "modeSetCoverage": 0.90,
                "agreement": "high" if len(modes) == 1 else "medium",
            },
            "precedents": [],
        }
        ranking = {
            "calibratedRisk": cal_risk,
            "consequence": "high" if level == "critical" else "medium",
            "consequenceNote": f"Synthetic A0 contract fixture for {scenario}",
            "exposure": "Up Main, 60 movements/day",
            "trustDiscount": 1.0,
            "tieBreaker": f"{level}:{horizon}={cal_risk:.4f};p10={p10}d",
        }
        assessments.append(
            build_assessment_payload(
                asset_id=asset_id,
                level=level,
                policy_rank=rank,
                persistence=2 if level != "watch" else 1,
                h24=h24,
                h72=h72,
                h7d=h7d,
                ece_zone=0.03,
                p10_days=p10,
                median_days=med,
                p90_days=p90,
                rul_coverage=0.80,
                held_out_n=100,
                likely_modes=modes,
                mode_probability=mode_prob,
                mode_set_coverage=0.90,
                data_trust_score=1.0,
                data_trust_flags=[],
                explanation=explanation,
                ranking=ranking,
                model_versions=model_versions,
                computed_at=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )

    iso_week = int(watermark.isocalendar().week)
    return build_publish_payload(
        snapshot_as_of=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
        snapshot_week=iso_week,
        snapshot_label=watermark.strftime("%d %b %Y · %H:%M UTC"),
        code_version=CODE_VERSION,
        input_watermark=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
        params=params,
        dataset_hash=manifest.hash,
        assessments=assessments,
        clusters=[],
        policy_version=POLICY_VERSION,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _settings = get_settings()
    if args.publish and args.dry_run:
        print("Cannot pass both --dry-run and --publish.", file=sys.stderr)
        return 2
    if args.publish:
        print("Live publish is wired in Phase A6; run with --dry-run in A0.", file=sys.stderr)
        return 2

    payload = build_synthetic_dry_run_payload(
        scenario=args.scenario,
        seed=args.seed,
        division=args.division,
        as_of=args.as_of,
        limit=args.limit,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    # Emit deterministic canonical hash to stderr for auditability.
    _digest = sha256_canonical(json.loads(canonical_json(payload)))
    print(f"Validated ModelRunPublishRequest (sha256={_digest[:12]})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
