"""Model card, metrics JSON, calibration plot and model-health snapshot builders."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from nidan_ai.bench.manifest import canonical_json, stable_id
from nidan_ai.config import (
    CLASSIFIER_VERSION,
    CONFORMAL_VERSION,
    GNN_VERSION,
    SURVIVAL_VERSION,
    TWIN_VERSION,
)


def write_metrics_json(path: str | Path, metrics: dict[str, Any]) -> Path:
    """Write a deterministic metrics JSON artefact (gitignored directory)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(canonical_json(metrics) + "\n", encoding="utf-8")
    return target


def write_model_card(
    path: str | Path,
    *,
    scenario: str,
    seed: int,
    split: str,
    bench_version: str,
    bench_hash: str,
    metrics: dict[str, Any],
    negative_results: list[str] | None = None,
    notes: list[str] | None = None,
) -> Path:
    """Write the model card markdown, labelled bench-only."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NIDAN AI model card",
        "",
        "> Bench-only evidence. These are simulation results, not field accuracy. Every number",
        "> below carries its bench version, seed, split and model version.",
        "",
        f"- Scenario: `{scenario}`",
        f"- Seed: `{seed}`",
        f"- Split: `{split}`",
        f"- Bench version: `{bench_version}`",
        f"- Bench hash: `{bench_hash}`",
        f"- Twin: `{TWIN_VERSION}`, classifier: `{CLASSIFIER_VERSION}`, "
        f"graph: `{GNN_VERSION}`, survival: `{SURVIVAL_VERSION}`, "
        f"conformal: `{CONFORMAL_VERSION}`",
        "",
        "## Measured metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
    ]
    for key in sorted(metrics):
        lines.append(f"| `{key}` | {metrics[key]} |")
    lines += [
        "",
        "## Safety statement",
        "",
        "NIDAN is advisory and non-vital. The engine has no write path, credential or API route",
        "to interlocking, signals, routes, points, axle counters or track-circuit hardware. The",
        "only outbound writes are `POST /v1/ingest/telemetry` and `POST /v1/ingest/model-run`.",
        "",
        "## Negative results",
        "",
    ]
    if negative_results:
        lines.extend(f"- {item}" for item in negative_results)
    else:
        lines.append("- None recorded for this run.")
    if notes:
        lines += ["", "## Notes", ""]
        lines.extend(f"- {item}" for item in notes)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def write_calibration_svg(
    path: str | Path,
    *,
    predictions: np.ndarray,
    outcomes: np.ndarray,
    bins: int = 10,
) -> Path:
    """Write a small deterministic reliability diagram as SVG (no plotting dependency)."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    predictions = np.asarray(predictions, dtype=float)
    outcomes = np.asarray(outcomes, dtype=float)
    order = np.argsort(predictions, kind="stable")
    predictions = predictions[order]
    outcomes = outcomes[order]
    chunks = np.array_split(np.arange(predictions.size), min(bins, max(1, predictions.size)))
    points = []
    for chunk in chunks:
        if chunk.size:
            points.append((float(np.mean(predictions[chunk])), float(np.mean(outcomes[chunk]))))
    width = height = 320
    padding = 40

    def scale(value: float) -> float:
        return padding + (1.0 - value) * (height - 2 * padding)

    def xscale(value: float) -> float:
        return padding + value * (width - 2 * padding)

    polyline = " ".join(f"{xscale(x):.1f},{scale(y):.1f}" for x, y in points)
    bars = "".join(
        f'<circle cx="{xscale(x):.1f}" cy="{scale(y):.1f}" r="3" fill="#1f6feb"/>'
        for x, y in points
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">'
        f'<rect width="{width}" height="{height}" fill="#ffffff"/>'
        f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" '
        f'y2="{height - padding}" stroke="#888"/>'
        f'<line x1="{padding}" y1="{padding}" x2="{padding}" '
        f'y2="{height - padding}" stroke="#888"/>'
        f'<line x1="{padding}" y1="{height - padding}" x2="{width - padding}" y2="{padding}" '
        f'stroke="#cccccc" stroke-dasharray="4 4"/>'
        f'<polyline points="{polyline}" fill="none" stroke="#1f6feb" stroke-width="2"/>'
        f"{bars}"
        f'<text x="{width / 2}" y="{height - 8}" font-size="11" '
        f'text-anchor="middle">Predicted</text>'
        f'<text x="12" y="{height / 2}" font-size="11" text-anchor="middle" '
        f'transform="rotate(-90 12 {height / 2})">Observed</text>'
        f"</svg>"
    )
    target.write_text(svg + "\n", encoding="utf-8")
    return target


def build_model_health(
    *,
    as_of: str,
    window: str,
    ece: float,
    coverage: float,
    held_out_n: int,
    reliability: list[dict[str, Any]],
    by_level: list[dict[str, Any]],
    by_mode: list[dict[str, Any]],
    drift: list[dict[str, Any]],
    data_trust: dict[str, Any],
    gates: list[dict[str, Any]],
    code_version: str,
    bench_version: str,
    bench_hash: str,
    seed: int,
    split: str,
    graph_active: bool = False,
) -> dict[str, Any]:
    """Build a payload matching the backend ``ModelHealth`` model."""
    signature = stable_id(
        "model-health",
        as_of,
        code_version,
        bench_hash,
        seed,
        split,
        round(float(ece), 6),
        round(float(coverage), 6),
        32,
    )
    models = [
        {
            "name": "Physics twin",
            "version": TWIN_VERSION,
            "trained": as_of,
            "window": window,
            "owner": "S&T R&D",
            "state": "Active",
        },
        {
            "name": "Propagation graph",
            "version": GNN_VERSION,
            "trained": as_of,
            "window": window,
            "owner": "ML platform",
            "state": "Active" if graph_active else "Shadow",
        },
        {
            "name": "Survival / RUL",
            "version": SURVIVAL_VERSION,
            "trained": as_of,
            "window": window,
            "owner": "ML platform",
            "state": "Active",
        },
        {
            "name": "Mode classifier",
            "version": CLASSIFIER_VERSION,
            "trained": as_of,
            "window": window,
            "owner": "ML platform",
            "state": "Active",
        },
        {
            "name": "Conformal calibrator",
            "version": CONFORMAL_VERSION,
            "trained": as_of,
            "window": window,
            "owner": "ML platform",
            "state": "Active",
        },
    ]
    return {
        "asOf": as_of,
        "window": window,
        "ece": float(ece),
        "eceBins": 10,
        "coverage": float(coverage),
        "heldOutN": int(held_out_n),
        "activeModels": int(sum(1 for m in models if m["state"] == "Active")),
        "driftAmber": int(sum(1 for item in drift if item["state"] != "nominal")),
        "models": models,
        "reliability": reliability,
        "byLevel": by_level,
        "byMode": by_mode,
        "drift": drift,
        "dataTrust": data_trust,
        "gates": gates,
        "signature": f"nidan-ai {code_version} bench {bench_version} hash {bench_hash[:12]}",
        "modelVersions": {
            "twin": TWIN_VERSION,
            "gnn": GNN_VERSION,
            "survival": SURVIVAL_VERSION,
            "classifier": CLASSIFIER_VERSION,
            "conformal": CONFORMAL_VERSION,
            "codeVersion": code_version,
            "benchVersion": bench_version,
            "benchHash": bench_hash,
            "seed": seed,
            "split": split,
            "signature": signature,
        },
        "generatedAt": as_of,
    }


def write_json(path: str | Path, payload: dict[str, Any]) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def timestamp_label(value: datetime) -> str:
    return value.strftime("%d %b %Y %H:%M UTC")
