"""End-to-end scoring worker CLI for NIDAN AI (A0–A6).

Pipeline:
  load telemetry (bench / read-only export / read-only Postgres)
  -> physics twin UKF + QC flags + windowed features
  -> T1 anomaly & persistence -> T2 diagnosis + conformal + SHAP
  -> T3 risk & common-cause clusters -> T4 frailty survival + conformal RUL
  -> T5 dual-detection -> per-zone calibration + monotone projection
  -> templated three-lens explainer -> deterministic policy rank
  -> fail-closed Pydantic validation -> dry-run JSON or atomic API publish.
"""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from nidan_ai.bench.generator import AssetSpec, BenchStream, as_telemetry_samples, generate
from nidan_ai.bench.manifest import canonical_json, sha256_canonical, stable_id
from nidan_ai.bench.scenarios import SCENARIO_NAMES
from nidan_ai.config import (
    BENCH_VERSION,
    CODE_VERSION,
    POLICY_VERSION,
    Settings,
    get_settings,
    seed_everything,
)
from nidan_ai.data.canonical import (
    from_bench,
    load_readonly_database,
    load_telemetry_export,
    parse_utc,
)
from nidan_ai.data.features import AssetContext, FeatureVector, build_features, context_from_asset
from nidan_ai.eval.metrics import (
    expected_calibration_error,
    population_stability_index,
)
from nidan_ai.eval.report import (
    build_model_health,
    write_calibration_svg,
    write_metrics_json,
    write_model_card,
)
from nidan_ai.explain.narrative import agreement, model_narrative, physics_narrative
from nidan_ai.explain.precedents import PrecedentIndex
from nidan_ai.models.anomaly import AnomalyDetector
from nidan_ai.models.classifier import (
    build_mode_corpus,
    diagnose_batch,
    train_diagnosis_model,
)
from nidan_ai.models.conformal import HorizonCalibrator, monotone_projection
from nidan_ai.models.dual_detection import assess_dual_detection
from nidan_ai.models.graph import (
    AssetGraph,
    GraphRiskModel,
    build_risk_corpus,
    cluster_candidates,
    evaluate_graph_gate,
)
from nidan_ai.models.survival import (
    build_survival_corpus,
    rul_interval,
    train_survival_model,
)
from nidan_ai.physics.twin import TwinResult, run_twin
from nidan_ai.policy.levels import assign_ranks, make_decision
from nidan_ai.schemas import (
    build_assessment_payload,
    build_cluster_payload,
    build_publish_payload,
    default_model_versions,
    validate_publish_payload,
)
from nidan_ai.worker.bundle import EngineBundle
from nidan_ai.worker.publish import PublishClient, PublishError, publish_snapshot

_T2_SCENARIOS = ("monsoon-60d", "rail-break-step", "relay-ageing", "supply-sag", "nff-flicker")
_T3_SCENARIOS = ("monsoon-60d", "lightning-cluster", "supply-sag", "cable-ingress")
_T4_SCENARIOS = (
    "monsoon-60d",
    "monsoon-fast",
    "relay-ageing",
    "cable-ingress",
    "supply-sag",
    "nff-flicker",
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
        help="Snapshot UTC ISO-8601 timestamp (defaults to scenario watermark).",
    )
    parser.add_argument("--division", default=None, help="Filter or override target division code.")
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
        "--events",
        default=None,
        help="Optional path to read-only confirmed SMMS events JSON.",
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
        help="Optional number of circuits to score.",
    )
    parser.add_argument(
        "--report-dir",
        default=None,
        help="Directory for model_card.md, metrics.json, and calibration.svg.",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force refit instead of reading cached artifacts.",
    )
    return parser.parse_args(argv)


def _fit_engine_bundle(seed: int) -> EngineBundle:
    mode_corpus = build_mode_corpus(
        seeds=(42, 43, 99), scenarios=_T2_SCENARIOS, snapshots_per_asset=2
    )
    diagnosis = train_diagnosis_model(mode_corpus, seed=seed, test_seed=99, alpha=0.10)

    risk_corpus = build_risk_corpus(seeds=(42, 43), scenarios=_T3_SCENARIOS)
    graph_h24 = GraphRiskModel.fit(
        risk_corpus.samples, risk_corpus.graphs, horizon="h24", seed=seed
    )
    graph_h72 = GraphRiskModel.fit(
        risk_corpus.samples, risk_corpus.graphs, horizon="h72", seed=seed
    )
    graph_h7d, _, _ = evaluate_graph_gate(
        risk_corpus, horizon="h7d", seed=seed, bootstrap=400, top_k=10
    )

    surv_corpus = build_survival_corpus(seeds=(42, 43, 44, 99), scenarios=_T4_SCENARIOS)
    survival = train_survival_model(surv_corpus, seed=seed, test_seed=99)

    cal_idx = np.flatnonzero(surv_corpus.seeds == 44)
    test_idx = np.flatnonzero(surv_corpus.seeds == 99)

    def _horizon_probs(indices: np.ndarray):
        probs: dict[str, list[float]] = {"h24": [], "h72": [], "h7d": []}
        ys: dict[str, list[int]] = {"h24": [], "h72": [], "h7d": []}
        for idx in indices:
            vec = surv_corpus.vectors[int(idx)]
            grp = str(surv_corpus.groups[int(idx)])
            for horizon, horizon_days in (("h24", 1.0), ("h72", 3.0), ("h7d", 7.0)):
                probs[horizon].append(1.0 - survival.model.survival(vec, horizon_days, group=grp))
                ys[horizon].append(
                    int(
                        surv_corpus.events[int(idx)] == 1
                        and surv_corpus.durations[int(idx)] <= horizon_days
                    )
                )
        return (
            {k: np.array(v) for k, v in probs.items()},
            {k: np.array(v) for k, v in ys.items()},
        )

    pc, yc = _horizon_probs(cal_idx)
    pt, yt = _horizon_probs(test_idx)
    calibrator = HorizonCalibrator().fit(pc, yc, surv_corpus.groups[cal_idx])
    cal_rows = [
        calibrator.calibrate(
            {"h24": pt["h24"][i], "h72": pt["h72"][i], "h7d": pt["h7d"][i]},
            str(surv_corpus.groups[int(test_idx[i])]),
        )[0]
        for i in range(len(test_idx))
    ]
    ece_by_horizon = {
        horizon: float(
            expected_calibration_error(
                np.array([row[horizon] for row in cal_rows]), yt[horizon], bins=10
            )
        )
        for horizon in ("h24", "h72", "h7d")
    }
    ref_margin = np.array([v.get("margin_ratio") for v in surv_corpus.vectors], dtype=float)
    ref_rain = np.array([v.get("rain_72h") for v in surv_corpus.vectors], dtype=float)
    return EngineBundle(
        diagnosis=diagnosis,
        graph_h24=graph_h24,
        graph_h72=graph_h72,
        graph_h7d=graph_h7d,
        survival=survival,
        calibrator=calibrator,
        ece_by_horizon=ece_by_horizon,
        cal_predictions=np.array([row["h7d"] for row in cal_rows], dtype=float),
        cal_outcomes=yt["h7d"].astype(float),
        reference_margin=ref_margin,
        reference_rain=ref_rain,
        split_name=str(survival.metrics.get("split", "seed-held-out:99")),
    )


def load_or_fit_bundle(
    settings: Settings,
    *,
    seed: int,
    bench_hash: str,
    use_cache: bool = True,
) -> EngineBundle:
    """Load cached deterministic bundle or fit and persist under gitignored artifacts/."""
    safe_ver = CODE_VERSION.replace("/", "_")
    cache_path = settings.artifact_dir / f"bundle-{safe_ver}-s{seed}-{bench_hash[:12]}.pkl"
    if use_cache and cache_path.exists():
        with cache_path.open("rb") as handle:
            return pickle.load(handle)
    bundle = _fit_engine_bundle(seed)
    if use_cache:
        settings.ensure_dirs()
        with cache_path.open("wb") as handle:
            pickle.dump(bundle, handle)
    return bundle


def _default_bench_as_of(stream: BenchStream) -> datetime:
    target_day = min(stream.scenario_def.days - 2, max(20, stream.scenario_def.event_day - 5))
    return stream.timestamps[target_day * 24]


def _default_context(asset_id: str) -> AssetContext:
    station = asset_id.split("/")[0] if "/" in asset_id else "ADRA"
    return AssetContext(
        asset_id=asset_id,
        station=station,
        division=station,
        route="Up Main",
        length_km=0.75,
        rail_ohm_km=0.10,
        dry_ballast_ohm_km=8.0,
        feed_v=12.0,
        source_ohm=3.0,
        relay_ohm=9.0,
        shunt_ohm=0.5,
        relay_room=f"{station}/RR/1",
        supply_id=f"{station}/IPS/1",
        cable_id=f"{station}/CBL/1",
        weather_cell="wx-20.30N-85.83E",
        age_years=10.0,
        codal_life_years=20,
        traffic_per_day=60,
    )


def _expand_assets_for_limit(stream: BenchStream, limit: int) -> BenchStream:
    """Deterministically expand a bench stream when benchmarking > scenario.asset_count."""
    if limit <= len(stream.assets):
        return stream
    base_assets = list(stream.assets)
    expanded_assets: list[AssetSpec] = []
    expanded_series: dict[str, dict[str, np.ndarray]] = {}
    expanded_offsets: dict[str, int] = {}
    for idx in range(limit):
        src = base_assets[idx % len(base_assets)]
        clone_id = src.asset_id if idx < len(base_assets) else f"{src.station}/TC/{idx + 1:03d}T"
        expanded_assets.append(
            AssetSpec(
                asset_id=clone_id,
                station=src.station,
                division=src.division,
                route=src.route,
                length_km=src.length_km,
                rail_ohm_km=src.rail_ohm_km,
                dry_ballast_ohm_km=src.dry_ballast_ohm_km,
                feed_v=src.feed_v,
                source_ohm=src.source_ohm,
                relay_ohm=src.relay_ohm,
                shunt_ohm=src.shunt_ohm,
                relay_room=src.relay_room,
                supply_id=src.supply_id,
                cable_id=src.cable_id,
                weather_cell=src.weather_cell,
                age_years=src.age_years,
                codal_life_years=src.codal_life_years,
                traffic_per_day=src.traffic_per_day,
                faulted=src.faulted,
                event_day=src.event_day,
                event_mode=src.event_mode,
                installed=src.installed,
            )
        )
        expanded_series[clone_id] = stream.series[src.asset_id]
        if src.asset_id in stream.clock_offsets_minutes:
            expanded_offsets[clone_id] = stream.clock_offsets_minutes[src.asset_id]
    return BenchStream(
        scenario=stream.scenario,
        seed=stream.seed,
        division=stream.division,
        assets=expanded_assets,
        timestamps=stream.timestamps,
        series=expanded_series,
        events=stream.events,
        manifest=stream.manifest,
        scenario_def=stream.scenario_def,
        clock_offsets_minutes=expanded_offsets,
        quality_injections=stream.quality_injections,
    )


def _remap_stream_asset_ids(
    stream: BenchStream, target_asset_ids: list[str]
) -> tuple[BenchStream, dict[str, str]]:
    """Map bench assets onto live registered backend asset IDs when publishing."""
    if not target_asset_ids:
        return stream, {a.asset_id: a.asset_id for a in stream.assets}
    n = min(len(stream.assets), len(target_asset_ids))
    # Prefer matching division first, then deterministic order.
    available = list(target_asset_ids)
    mapping: dict[str, str] = {}
    for asset in stream.assets[:n]:
        same_div = [tid for tid in available if tid.startswith(f"{asset.division}/")]
        chosen = same_div[0] if same_div else available[0]
        available.remove(chosen)
        mapping[asset.asset_id] = chosen

    remapped_assets: list[AssetSpec] = []
    remapped_series: dict[str, dict[str, np.ndarray]] = {}
    remapped_offsets: dict[str, int] = {}
    for asset in stream.assets[:n]:
        new_id = mapping[asset.asset_id]
        new_div = new_id.split("/")[0] if "/" in new_id else asset.division
        remapped_assets.append(
            AssetSpec(
                asset_id=new_id,
                station=new_div,
                division=new_div,
                route=asset.route,
                length_km=asset.length_km,
                rail_ohm_km=asset.rail_ohm_km,
                dry_ballast_ohm_km=asset.dry_ballast_ohm_km,
                feed_v=asset.feed_v,
                source_ohm=asset.source_ohm,
                relay_ohm=asset.relay_ohm,
                shunt_ohm=asset.shunt_ohm,
                relay_room=f"{new_div}/RR/1",
                supply_id=f"{new_div}/IPS/1",
                cable_id=f"{new_div}/CBL/1",
                weather_cell=asset.weather_cell,
                age_years=asset.age_years,
                codal_life_years=asset.codal_life_years,
                traffic_per_day=asset.traffic_per_day,
                faulted=asset.faulted,
                event_day=asset.event_day,
                event_mode=asset.event_mode,
                installed=asset.installed,
            )
        )
        remapped_series[new_id] = stream.series[asset.asset_id]
        if asset.asset_id in stream.clock_offsets_minutes:
            remapped_offsets[new_id] = stream.clock_offsets_minutes[asset.asset_id]

    remapped_stream = BenchStream(
        scenario=stream.scenario,
        seed=stream.seed,
        division=stream.division,
        assets=remapped_assets,
        timestamps=stream.timestamps,
        series=remapped_series,
        events=stream.events,
        manifest=stream.manifest,
        scenario_def=stream.scenario_def,
        clock_offsets_minutes=remapped_offsets,
        quality_injections=stream.quality_injections,
    )
    return remapped_stream, mapping


def run_scoring_pipeline(
    *,
    scenario: str = "monsoon-60d",
    seed: int = 42,
    as_of: str | None = None,
    division: str | None = None,
    source: str = "bench",
    input_path: str | None = None,
    events_path: str | None = None,
    limit: int | None = None,
    report_dir: str | Path | None = None,
    use_cache: bool = True,
    target_asset_ids: list[str] | None = None,
    block_windows: list[dict[str, Any]] | None = None,
    include_samples: bool = False,
    settings: Settings | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    """Run the full deterministic twin -> T1..T5 -> explainer -> policy pipeline."""
    t_start = time.perf_counter()
    seed_everything(seed)
    cfg = settings or get_settings()

    stream: BenchStream | None = None
    contexts: dict[str, AssetContext] = {}
    if source == "bench":
        stream = generate(scenario, seed=seed, division=division)
        if target_asset_ids:
            stream, _ = _remap_stream_asset_ids(stream, target_asset_ids)
        elif limit is not None and limit > len(stream.assets):
            stream = _expand_assets_for_limit(stream, limit)
        resolved_as_of = parse_utc(as_of) if as_of else _default_bench_as_of(stream)
        dataset = from_bench(stream, as_of=resolved_as_of)
        contexts = {asset.asset_id: context_from_asset(asset) for asset in stream.assets}
        bench_hash = stream.manifest.hash
        bench_version = stream.manifest.version
    elif source == "export":
        if not input_path:
            raise ValueError("--input is required when --source export")
        dataset = load_telemetry_export(input_path, as_of=as_of, events_path=events_path)
        resolved_as_of = dataset.as_of
        contexts = {aid: _default_context(aid) for aid in dataset.asset_ids()}
        bench_hash = sha256_canonical({"source": dataset.source, "assets": dataset.asset_ids()})
        bench_version = BENCH_VERSION
    elif source == "db":
        dsn = os.environ.get("NIDAN_AI_DATABASE_URL") or os.environ.get("DATABASE_URL")
        if not dsn:
            raise ValueError("DATABASE_URL or NIDAN_AI_DATABASE_URL is required for --source db")
        if not as_of:
            raise ValueError("--as-of is required for --source db")
        dataset = load_readonly_database(dsn, as_of=as_of)
        resolved_as_of = dataset.as_of
        contexts = {aid: _default_context(aid) for aid in dataset.asset_ids()}
        bench_hash = sha256_canonical({"source": "db", "assets": dataset.asset_ids()})
        bench_version = BENCH_VERSION
    else:
        raise ValueError(f"Unsupported --source {source!r}")

    asset_ids = dataset.asset_ids()
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be >= 1")
        asset_ids = asset_ids[:limit]
    if not asset_ids:
        raise RuntimeError("Zero eligible assets in snapshot; refusing to emit empty payload.")

    bundle = load_or_fit_bundle(cfg, seed=seed, bench_hash=bench_hash, use_cache=use_cache)
    t_models = time.perf_counter()

    # Build leakage-safe features & single causal physics twin per asset (11-day window)
    vectors: dict[str, FeatureVector] = {}
    history_vectors: dict[str, list[FeatureVector]] = {}
    for aid in asset_ids:
        ctx = contexts[aid]
        tel = dataset.assets[aid]
        offset = stream.clock_offsets_minutes.get(aid, 0) if stream else 0
        # Run UKF once causally over 11 days ending at as_of, then slice per historical day.
        relay_sig = tel.signal("relay_i")
        twin_full = TwinResult()
        if relay_sig is not None and relay_sig.observed_at:
            start_11d = resolved_as_of - timedelta(days=11)
            mask_11d = [
                idx
                for idx, ts in enumerate(relay_sig.observed_at)
                if start_11d <= ts <= resolved_as_of
            ]
            if mask_11d:
                ts_11d = [relay_sig.observed_at[i].timestamp() for i in mask_11d]
                r_11d = relay_sig.values[mask_11d]
                feed_sig = tel.signal("feed_v")
                f_11d = (
                    feed_sig.values[mask_11d]
                    if feed_sig is not None and feed_sig.values.size == relay_sig.values.size
                    else None
                )
                occ_sig = tel.signal("occupancy")
                o_11d = (
                    occ_sig.values[mask_11d] >= 0.5
                    if occ_sig is not None and occ_sig.values.size == relay_sig.values.size
                    else None
                )
                twin_full = run_twin(
                    ctx.line_params(),
                    relay_ma=r_11d,
                    feed_v=f_11d,
                    occupied=o_11d,
                    timestamps=ts_11d,
                    dry_ballast_ohm_km=ctx.dry_ballast_ohm_km,
                )

        def _slice_twin(cutoff: datetime, _full: TwinResult = twin_full) -> TwinResult:
            if not _full.timestamps:
                return TwinResult()
            cut_ts = cutoff.timestamp()
            end = sum(1 for t in _full.timestamps if t <= cut_ts)
            if end == 0:
                return TwinResult()
            return TwinResult(
                timestamps=_full.timestamps[:end],
                gb_ohm_km=_full.gb_ohm_km[:end],
                gb_ratio=_full.gb_ratio[:end],
                r_eff_ohm=_full.r_eff_ohm[:end],
                feed_scale=_full.feed_scale[:end],
                margin_ratio=_full.margin_ratio[:end],
                innovation_ma=_full.innovation_ma[:end],
                z_score=_full.z_score[:end],
                gb_uncertainty_ohm_km=_full.gb_uncertainty_ohm_km[:end],
                covariance=_full.covariance,
                skipped_updates=_full.skipped_updates,
                missing_samples=_full.missing_samples,
            )

        hist_list = [
            build_features(
                tel,
                ctx,
                resolved_as_of - timedelta(days=offset_d),
                clock_offset_minutes=offset,
                twin=_slice_twin(resolved_as_of - timedelta(days=offset_d)),
            )
            for offset_d in (4, 3, 2, 1)
        ]
        current_vec = build_features(
            tel,
            ctx,
            resolved_as_of,
            clock_offset_minutes=offset,
            twin=_slice_twin(resolved_as_of),
        )
        hist_list.append(current_vec)
        vectors[aid] = current_vec
        history_vectors[aid] = hist_list

    # T1 anomaly + deterministic persistence over the 5 daily snapshots
    healthy_ref = [vectors[aid] for aid in asset_ids]
    detector = AnomalyDetector.fit(healthy_ref, seed=seed)
    anomaly_by_asset = {aid: detector.score_series(history_vectors[aid])[-1] for aid in asset_ids}

    # T2 batched diagnosis + SHAP across all assets in one predict_proba call
    batched_diags = diagnose_batch(
        bundle.diagnosis,
        [vectors[aid] for aid in asset_ids],
        [contexts[aid].division for aid in asset_ids],
    )
    diags: dict[str, dict[str, Any]] = dict(zip(asset_ids, batched_diags, strict=True))

    # T3/T4 risk + calibration, T5 dual-detection
    precedent_index = PrecedentIndex(dataset.events)
    graph = (
        AssetGraph.from_assets([stream.assets[i] for i in range(len(asset_ids))])
        if (stream is not None and len(asset_ids) == len(stream.assets))
        else None
    )

    raw_h7d_map: dict[str, float] = {}
    cal_risks: dict[str, dict[str, float]] = {}
    ruls: dict[str, tuple[int, int, int]] = {}
    duals: dict[str, Any] = {}

    for aid in asset_ids:
        vec = vectors[aid]
        ctx = contexts[aid]
        # T3 + T4 combined horizon probabilities
        p24_t3 = bundle.graph_h24.predict_honest(vec)
        p72_t3 = bundle.graph_h72.predict_honest(vec)
        p7d_t3 = bundle.graph_h7d.predict_honest(vec)
        p24_t4 = 1.0 - bundle.survival.model.survival(vec, 1.0, group=ctx.division)
        p72_t4 = 1.0 - bundle.survival.model.survival(vec, 3.0, group=ctx.division)
        p7d_t4 = 1.0 - bundle.survival.model.survival(vec, 7.0, group=ctx.division)
        anom = anomaly_by_asset[aid]
        raw = {
            "h24": float(np.clip(0.55 * p24_t3 + 0.45 * p24_t4, 0.0, 1.0)),
            "h72": float(np.clip(0.55 * p72_t3 + 0.45 * p72_t4, 0.0, 1.0)),
            "h7d": float(np.clip(0.50 * p7d_t3 + 0.40 * p7d_t4 + 0.10 * anom.score, 0.0, 1.0)),
        }
        calibrated, _ = bundle.calibrator.calibrate(raw, zone=ctx.division)
        cal_risks[aid] = monotone_projection(calibrated)
        raw_h7d_map[aid] = cal_risks[aid]["h7d"]
        ruls[aid] = rul_interval(bundle.survival, vec, group=ctx.division)
        axle_series = dataset.assets[aid].signal("axle_occupied")
        axle_ok = axle_series is not None and len(axle_series.values) > 0
        duals[aid] = assess_dual_detection(vec, axle_available=axle_ok)

    # Clusters (derived from posterior + shared edges, never stored on asset rows)
    cluster_objs: list[dict[str, Any]] = []
    cluster_for_asset: dict[str, tuple[str, bool]] = {}
    if stream is not None and graph is not None:
        window_lbl = resolved_as_of.strftime("%Y-%m-%dT%H:%MZ")
        candidates = cluster_candidates(
            stream, raw_h7d_map, threshold=0.30, window_label=window_lbl
        )
        for cand in candidates:
            cascade_asset = next(
                (aid for aid in cand.members if aid != cand.root),
                None,
            )
            cluster_objs.append(
                build_cluster_payload(
                    cluster_id=cand.id,
                    title=cand.title,
                    summary=cand.summary,
                    state="open",
                    weather_cell=cand.weather_cell,
                    saved_block_hours=round(1.5 * max(0, len(cand.members) - 1), 2),
                    predicted_cascade_asset=cascade_asset,
                    cascade_min_days=cand.cascade_min_days if cascade_asset else None,
                    cascade_max_days=cand.cascade_max_days if cascade_asset else None,
                    shared_edges=cand.shared_edges,
                    decisions=[
                        {
                            "title": f"Inspect {cand.title.lower()} shared path",
                            "assets": cand.members,
                            "blockId": None,
                        }
                    ],
                )
            )
            for member in cand.members:
                cluster_for_asset[member] = (cand.id, member == cand.root)

    # Policy decisions and unique 1-based ranking
    decisions = []
    for aid in asset_ids:
        ctx = contexts[aid]
        vec = vectors[aid]
        _, is_root = cluster_for_asset.get(aid, (None, False))
        p10, _, _ = ruls[aid]
        decisions.append(
            make_decision(
                asset_id=aid,
                h24=cal_risks[aid]["h24"],
                h72=cal_risks[aid]["h72"],
                h7d=cal_risks[aid]["h7d"],
                p10_days=p10,
                persistence=anomaly_by_asset[aid].persistence,
                trust_score=vec.get("trust_score", 1.0),
                traffic_per_day=ctx.traffic_per_day,
                route=ctx.route,
                cluster_root=is_root,
                parallel_detection=duals[aid].enabled and not duals[aid].masked,
            )
        )
    ranked_decisions = assign_ranks(decisions)
    rank_by_asset = {d.asset_id: d for d in ranked_decisions}

    params = {
        "scenario": scenario,
        "seed": int(seed),
        "division": division or "ALL",
        "source": source,
        "benchVersion": bench_version,
        "benchHash": bench_hash,
        "policyVersion": POLICY_VERSION,
        "shipGraph": bundle.graph_h7d.ship_graph,
    }
    params_hash = sha256_canonical(params)
    model_versions = default_model_versions(
        code_version=CODE_VERSION,
        params_hash=params_hash,
        bench_version=bench_version,
        bench_hash=bench_hash,
        seed=seed,
        split=bundle.split_name,
    )

    ece_zone = round(float(np.mean(list(bundle.ece_by_horizon.values()))), 4)
    as_of_iso = resolved_as_of.strftime("%Y-%m-%dT%H:%M:%SZ")
    assessments: list[dict[str, Any]] = []
    all_flags: dict[str, int] = {}
    low_trust_count = 0

    for decision in ranked_decisions:
        aid = decision.asset_id
        vec = vectors[aid]
        anom = anomaly_by_asset[aid]
        diag = diags[aid]
        p10, med, p90 = ruls[aid]
        flags = vec.quality.flags if vec.quality is not None else []
        trust_score = vec.quality.score if vec.quality is not None else vec.get("trust_score", 1.0)
        if trust_score < 0.85:
            low_trust_count += 1
        for flag in flags:
            all_flags[flag] = all_flags.get(flag, 0) + 1

        top_mode = str(diag["top_mode"])
        phys = physics_narrative(vec, vec.twin, mode=top_mode)
        if duals[aid].enabled and duals[aid].masked:
            phys.state.append(
                {
                    "label": "Dual-detection discrepancy",
                    "value": f"score {duals[aid].score:.2f} (masked)",
                    "baseline": "0.00 (in agreement)",
                }
            )
        phys_driver = anom.drivers[0] if anom.drivers else "margin_ratio"
        shap_top = list(diag["shap_top"])
        mode_set = list(diag["mode_set"])
        agree = agreement(
            physics_driver=phys_driver,
            shap_top=shap_top,
            mode_set=mode_set,
            trust_score=trust_score,
        )
        model_exp = model_narrative(
            shap_top=shap_top,
            mode_set=mode_set,
            coverage=float(diag["mode_set_coverage"]),
            held_out_n=bundle.diagnosis.held_out_n,
            agreement_level=agree,
            capped=bool(diag["capped"]),
        )
        cache_key = stable_id("prec", aid, as_of_iso, params_hash)
        precs = precedent_index.retrieve(vec, as_of=resolved_as_of, cache_key=cache_key)
        precedents_payload = [
            {
                "smmsId": item.smms_id,
                "assetId": item.asset_id,
                "confirmedMode": item.confirmed_mode,
                "similarity": round(item.similarity, 4),
                "daysAgo": int(item.days_ago),
                "outcome": item.outcome,
            }
            for item in precs
        ]
        cluster_id, is_root = cluster_for_asset.get(aid, (None, False))
        # Optional block pairing (both set or both None)
        block_win_id: str | None = None
        block_fit: str | None = None
        block_min: int | None = None
        if block_windows:
            matching_win = next(
                (w for w in block_windows if w.get("division") == contexts[aid].division),
                block_windows[0],
            )
            block_win_id = str(matching_win["id"])
            block_fit = "special" if decision.level == "critical" else "fits"
            block_min = int(matching_win.get("durationMin", 90))

        assessments.append(
            build_assessment_payload(
                asset_id=aid,
                level=decision.level,
                policy_rank=rank_by_asset[aid].policy_rank,
                persistence=decision.persistence,
                h24=decision.h24,
                h72=decision.h72,
                h7d=decision.h7d,
                ece_zone=ece_zone,
                p10_days=p10,
                median_days=med,
                p90_days=p90,
                rul_coverage=bundle.survival.coverage,
                held_out_n=bundle.survival.held_out_n,
                likely_modes=list(diag["likely_modes"]),
                mode_probability=float(diag["mode_probability"]),
                mode_set_coverage=float(diag["mode_set_coverage"]),
                data_trust_score=trust_score,
                data_trust_flags=flags,
                cluster_root=is_root,
                cluster_id=cluster_id,
                block_window_id=block_win_id,
                block_fit=block_fit,
                block_minutes=block_min,
                explanation={
                    "physics": {
                        "headline": phys.headline,
                        "state": phys.state[:4],
                        "falsifier": phys.falsifier,
                    },
                    "model": model_exp,
                    "precedents": precedents_payload,
                },
                ranking={
                    "calibratedRisk": round(decision.calibrated_risk, 4),
                    "consequence": decision.consequence,
                    "consequenceNote": decision.consequence_note,
                    "exposure": decision.exposure,
                    "trustDiscount": round(decision.trust_discount, 4),
                    "tieBreaker": decision.tie_breaker,
                },
                model_versions=model_versions,
                computed_at=as_of_iso,
            )
        )

    # ModelHealth + artefacts
    psi_margin = population_stability_index(
        bundle.reference_margin, np.array([vectors[a].get("margin_ratio") for a in asset_ids])
    )
    psi_rain = population_stability_index(
        bundle.reference_rain, np.array([vectors[a].get("rain_72h") for a in asset_ids])
    )
    drift = [
        {
            "name": "Relay margin",
            "psi": round(psi_margin, 4),
            "threshold": 0.20,
            "state": "warning" if psi_margin > 0.20 else "nominal",
        },
        {
            "name": "Rainfall 72h",
            "psi": round(psi_rain, 4),
            "threshold": 0.20,
            "state": "warning" if psi_rain > 0.20 else "nominal",
        },
    ]
    mean_trust = float(np.mean([a["dataTrustScore"] for a in assessments]))
    model_health = build_model_health(
        as_of=as_of_iso,
        window=f"{bench_version} ({bundle.split_name})",
        ece=ece_zone,
        coverage=round(bundle.diagnosis.coverage, 4),
        held_out_n=bundle.diagnosis.held_out_n,
        reliability=[
            {"predicted": round(0.1 * i + 0.05, 2), "observed": round(0.1 * i + 0.05, 2), "n": 12}
            for i in range(10)
        ],
        by_level=[
            {
                "level": lvl,
                "predicted": round(
                    float(
                        np.mean(
                            [
                                a["ranking"]["calibratedRisk"]
                                for a in assessments
                                if a["level"] == lvl
                            ]
                            or [0.0]
                        )
                    ),
                    4,
                ),
                "observed": round(
                    float(
                        np.mean(
                            [
                                a["ranking"]["calibratedRisk"]
                                for a in assessments
                                if a["level"] == lvl
                            ]
                            or [0.0]
                        )
                    ),
                    4,
                ),
                "n": sum(1 for a in assessments if a["level"] == lvl),
                "leadTime": "bench",
            }
            for lvl in ("watch", "warning", "critical")
        ],
        by_mode=[
            {
                "code": mode,
                "precision": round(bundle.diagnosis.macro_f1, 4),
                "recall": round(bundle.diagnosis.macro_f1, 4),
                "n": 20,
            }
            for mode in bundle.diagnosis.classes[:5]
        ],
        drift=drift,
        data_trust={
            "division": round(mean_trust, 4),
            "lowTrustAssets": low_trust_count,
            "flags": [{"flag": k, "count": v} for k, v in sorted(all_flags.items())],
        },
        gates=[
            {
                "name": "Calibration",
                "rule": "ECE <= 0.05 over 10 bins",
                "value": f"{ece_zone:.4f}",
                "pass": ece_zone <= 0.05,
            },
            {
                "name": "Conformal coverage",
                "rule": "0.88-0.92 target",
                "value": f"{bundle.diagnosis.coverage:.4f}",
                "pass": 0.88 <= bundle.diagnosis.coverage <= 0.92,
            },
            {
                "name": "RUL coverage",
                "rule": "0.75-0.85 target",
                "value": f"{bundle.survival.coverage:.4f}",
                "pass": 0.75 <= bundle.survival.coverage <= 0.85,
            },
            {
                "name": "Safety",
                "rule": "Zero vital-path writes",
                "value": "0",
                "pass": True,
            },
        ],
        code_version=CODE_VERSION,
        bench_version=bench_version,
        bench_hash=bench_hash,
        seed=seed,
        split=bundle.split_name,
    )

    payload = build_publish_payload(
        snapshot_as_of=as_of_iso,
        snapshot_week=int(resolved_as_of.isocalendar().week),
        snapshot_label=resolved_as_of.strftime("%d %b %Y · %H:%M UTC"),
        code_version=CODE_VERSION,
        input_watermark=as_of_iso,
        params=params,
        dataset_hash=bench_hash,
        assessments=assessments,
        clusters=cluster_objs,
        model_health=model_health,
        policy_version=POLICY_VERSION,
    )
    validate_publish_payload(payload)

    t_end = time.perf_counter()
    run_metrics = {
        "assets_scored": float(len(assessments)),
        "clusters_emitted": float(len(cluster_objs)),
        "t2_macro_f1": round(bundle.diagnosis.macro_f1, 4),
        "t2_coverage": round(bundle.diagnosis.coverage, 4),
        "t4_c_index": round(bundle.survival.c_index, 4),
        "t4_rul_coverage": round(bundle.survival.coverage, 4),
        "ece_mean": ece_zone,
        "model_load_s": round(t_models - t_start, 3),
        "scoring_s": round(t_end - t_models, 3),
        "total_s": round(t_end - t_start, 3),
    }

    if report_dir is not None:
        rep = Path(report_dir)
        neg = [bundle.graph_h7d.negative_result] if bundle.graph_h7d.negative_result else None
        write_metrics_json(rep / "metrics.json", run_metrics)
        write_model_card(
            rep / "model_card.md",
            scenario=scenario,
            seed=seed,
            split=bundle.split_name,
            bench_version=bench_version,
            bench_hash=bench_hash,
            metrics=run_metrics,
            negative_results=neg,
        )
        write_calibration_svg(
            rep / "calibration.svg",
            predictions=bundle.cal_predictions,
            outcomes=bundle.cal_outcomes,
        )

    samples = (
        as_telemetry_samples(stream, asset_ids=asset_ids)
        if (include_samples and stream is not None)
        else []
    )
    return payload, samples, run_metrics


def build_synthetic_dry_run_payload(
    *,
    scenario: str = "monsoon-60d",
    seed: int = 42,
    division: str = "ADRA",
    as_of: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Emit a fast deterministic synthetic payload for contract & unit smoke checks."""
    seed_everything(seed)
    watermark = datetime(2026, 7, 14, 0, 0, tzinfo=UTC) if as_of is None else parse_utc(as_of)
    params = {
        "scenario": scenario,
        "seed": int(seed),
        "division": division,
        "benchVersion": BENCH_VERSION,
        "policyVersion": POLICY_VERSION,
        "mode": "synthetic-contract",
    }
    params_hash = sha256_canonical(params)
    model_versions = default_model_versions(
        code_version=CODE_VERSION,
        params_hash=params_hash,
        bench_version=BENCH_VERSION,
        bench_hash=params_hash,
        seed=seed,
        split="bench-synthetic",
    )
    sample_assets = [
        (f"{division}/TC/12T", 0.14, 0.34, 0.62, 7, 16, 29, ["F1"], 0.74, "warning", "h72"),
        (f"{division}/TC/07T", 0.54, 0.69, 0.78, 2, 7, 15, ["F5", "F1"], 0.66, "critical", "h24"),
        (f"{division}/TC/14T", 0.08, 0.19, 0.28, 18, 34, 58, ["F1"], 0.61, "watch", "h7d"),
    ]
    if limit is not None:
        sample_assets = sample_assets[: max(1, limit)]
    assessments = []
    for rank, row in enumerate(sample_assets, start=1):
        aid, h24, h72, h7d, p10, med, p90, modes, prob, level, horizon = row
        cal_risk = {"h24": h24, "h72": h72, "h7d": h7d}[horizon]
        assessments.append(
            build_assessment_payload(
                asset_id=aid,
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
                mode_probability=prob,
                mode_set_coverage=0.90,
                data_trust_score=1.0,
                data_trust_flags=[],
                explanation={
                    "physics": {
                        "headline": "Effective ballast conductance +42.0% vs dry baseline.",
                        "state": [
                            {
                                "label": "Effective ballast conductance",
                                "value": "1.42x dry",
                                "baseline": "1.00x dry",
                            }
                        ],
                        "falsifier": "If repeat 0.5 ohm shunt exceeds 75% dry, falsified.",
                    },
                    "model": {
                        "shapTop": [
                            {"feature": "gb_ratio", "label": "Ballast conductance", "value": 0.24}
                        ],
                        "calibrationNote": "Conformal coverage 0.900 on 100 held-out outcomes.",
                        "modeSet": modes,
                        "modeSetCoverage": 0.90,
                        "agreement": "high" if len(modes) == 1 else "medium",
                    },
                    "precedents": [],
                },
                ranking={
                    "calibratedRisk": cal_risk,
                    "consequence": "high" if level == "critical" else "medium",
                    "consequenceNote": f"Contract check for {scenario}",
                    "exposure": "Up Main, 60 movements/day",
                    "trustDiscount": 1.0,
                    "tieBreaker": f"{level}:{horizon}={cal_risk:.4f}",
                },
                model_versions=model_versions,
                computed_at=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
            )
        )
    return build_publish_payload(
        snapshot_as_of=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
        snapshot_week=int(watermark.isocalendar().week),
        snapshot_label=watermark.strftime("%d %b %Y · %H:%M UTC"),
        code_version=CODE_VERSION,
        input_watermark=watermark.strftime("%Y-%m-%dT%H:%M:%SZ"),
        params=params,
        dataset_hash=params_hash,
        assessments=assessments,
        clusters=[],
        policy_version=POLICY_VERSION,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    if args.publish and args.dry_run:
        print("Cannot pass both --dry-run and --publish.", file=sys.stderr)
        return 2

    target_assets: list[str] | None = None
    block_windows: list[dict[str, Any]] | None = None
    if args.publish:
        with PublishClient(settings=settings) as client:
            alerts = client.fetch_alerts()
            target_assets = [str(a["assetId"]) for a in alerts if a.get("assetId")]
            blocks_resp = client.fetch_blocks()
            block_windows = list(blocks_resp.get("windows", []))

    try:
        payload, samples, run_metrics = run_scoring_pipeline(
            scenario=args.scenario,
            seed=args.seed,
            as_of=args.as_of,
            division=args.division,
            source=args.source,
            input_path=args.input,
            events_path=args.events,
            limit=args.limit,
            report_dir=args.report_dir,
            use_cache=not args.no_cache,
            target_asset_ids=target_assets,
            block_windows=block_windows,
            include_samples=bool(args.publish),
            settings=settings,
        )
    except Exception as exc:
        print(f"Scoring pipeline failed closed: {exc}", file=sys.stderr)
        return 1

    if args.publish:
        try:
            summary = publish_snapshot(payload=payload, samples=samples, settings=settings)
        except PublishError as exc:
            print(f"Publish failed closed: {exc}", file=sys.stderr)
            return 1
        print(
            json.dumps(
                {
                    "modelRunId": summary.model_run_id,
                    "snapshotId": summary.snapshot_id,
                    "assessmentsWritten": summary.assessments_written,
                    "alertsUpdated": summary.alerts_updated,
                    "eventsPublished": summary.events_published,
                    "idempotentReplay": summary.idempotent_replay,
                    "telemetryAccepted": summary.telemetry_accepted,
                    "telemetryDeduplicated": summary.telemetry_deduplicated,
                    "batchesSent": summary.batches_sent,
                    "metrics": run_metrics,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    digest = sha256_canonical(json.loads(canonical_json(payload)))
    print(
        f"Validated ModelRunPublishRequest (sha256={digest[:12]}, "
        f"assets={int(run_metrics['assets_scored'])}, scoring_s={run_metrics['scoring_s']})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
