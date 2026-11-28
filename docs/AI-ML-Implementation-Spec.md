# NIDAN — AI/ML Implementation Specification

**Predictive Failure Propagation Engine for Indian Railway Track Circuits**

| | |
|---|---|
| Document | AI/ML Architecture, Model Portfolio and Implementation Specification |
| Version | 1.0 |
| Date | 26 November 2026 |
| Status | Specification — engine not yet implemented. The backend Phase 0/1 contract is frozen; this document defines the scorer that will populate it. |
| Scope | Physics twin, anomaly detection, fault diagnosis, common-cause graph, survival/RUL, conformal calibration, explanation, evaluation and MLOps |
| Companion artefacts | `docs/Research/Debdatta-Complete-Research.md` (§5.3, §11, §16, §19, Appendix C), `docs/Frontend-Complete-Research-Implementation.md`, `backend/Backend-Architecture-Implementation.md`, `backend/app/models/alerts.py`, `backend/app/models/health.py`, `Nidan-Frontend/src/data/fixtures.ts` |

> **Advisory, non-vital boundary.** The AI/ML layer reads telemetry and writes advisory assessments. It holds no write path, credential or API route to Electronic Interlocking, signals, routes, points, axle counters or track-circuit hardware. It does not decide alert levels either — a deterministic policy layer does (§11). No model output is ever actuated.

---

## Contents

1. [Executive Summary](#1-executive-summary)
2. [Position in the System](#2-position-in-the-system)
3. [The Contract With the Backend](#3-the-contract-with-the-backend)
4. [Model Portfolio](#4-model-portfolio)
5. [Data and Feature Specification](#5-data-and-feature-specification)
6. [NIDAN-Bench](#6-nidan-bench)
7. [Physics Twin](#7-physics-twin)
8. [Task Specifications](#8-task-specifications)
9. [Explanation Layer](#9-explanation-layer)
10. [Calibration and Uncertainty](#10-calibration-and-uncertainty)
11. [Policy Handoff](#11-policy-handoff)
12. [Evaluation Protocol](#12-evaluation-protocol)
13. [Promotion Gates and Shadow Mode](#13-promotion-gates-and-shadow-mode)
14. [Runtime and Orchestration](#14-runtime-and-orchestration)
15. [MLOps and Monitoring](#15-mlops-and-monitoring)
16. [Repository Layout and Implementation Plan](#16-repository-layout-and-implementation-plan)
17. [Testing Strategy](#17-testing-strategy)
18. [Risks and Open Questions](#18-risks-and-open-questions)
19. [Appendix A — Metric Definitions](#appendix-a--metric-definitions)
20. [Appendix B — Failure Taxonomy to Feature Map](#appendix-b--failure-taxonomy-to-feature-map)

---

## 1. Executive Summary

The backend already answers *how a NIDAN judgement is stored, served and audited*. It does not yet answer *how that judgement is computed*. Today `risk_assessment` rows, clusters and `/v1/models/health` are served from the seed fixture generated from the front-end contract; the values are demonstration data, not measured model output.

This document specifies the engine that replaces them:

1. **A physics-informed digital twin** of each track circuit, which estimates hidden physical state (effective ballast conductance, series/rail term, relay margin) from ordinary terminal measurements.
2. **A detection stack** that separates weather-explained drift from asset drift, using the twin residual plus statistical and self-supervised detectors.
3. **A diagnosis stack** that names the failure mode from the F1–F12 taxonomy with conformal prediction sets.
4. **A common-cause graph** that converts many simultaneous alarms into one root cause and a cascade window.
5. **A survival model** that turns a snapshot into calibrated days-to-failure with shared frailty for station, supply and climate.
6. **A three-lens explanation** — physics change, signed feature attribution, and similar confirmed SMMS cases — plus a falsifier sentence.
7. **An evaluation and promotion regime** strict enough that an RDSO/DSTE reviewer can accept or reject a model on evidence.

The design principle throughout is **earn the complexity**: a fixed threshold, then a physics residual, then an ensemble, then a graph, then survival. Each layer must beat the one below it on the benchmark, or it is not shipped.

### 1.1 What exists today, and what this document adds

| Element | Status | Where |
|---|---|---|
| Output contract (`Alert`, `Rul`, `Explanation`, `ModelHealth`) | **Implemented** | `backend/app/models/` |
| Database schema, immutability, policy `CHECK`s | **Implemented** | `backend/db/0001_init.sql` |
| Fixture-derived assessments and model-health snapshot | **Implemented (demo values)** | `backend/db/seed.sql`, `Nidan-Frontend/src/data/fixtures.ts` |
| Transmission-line illustration and seeded 60-day experiment | **Documented and reproducible** | Research dossier §5.3, Appendix C |
| Packaged twin, bench, models, explainer, scoring worker | **Specified here** | `ai/` (to be created) |
| Live telemetry ingestion, Kafka, feature store | **Specified** | Backend doc §9; backend Phase 3 |

The AI stream can start immediately: the contract is frozen, so every model can be developed and tested against the same Pydantic schemas the API serves. Nothing here requires the backend's Phase 2 (live Postgres CI, OIDC) to be finished first.

### 1.2 Non-goals

- No control of, or write path to, any vital system.
- No large language model in the decision path. Templated text only (§9.5).
- No claim of field accuracy. Current evidence is simulation and bench only.
- No replacement of the technician, the interlocking, Kavach, RDPMS or SMMS.
- No twelve-class classifier on day one; the first release covers a subset (§8.3).

---

## 2. Position in the System

### 2.1 Where the AI layer sits

```text
L0  Field assets (vital, unchanged)
      │  read-only, isolated, one-way
L1  Edge gateway: feature extraction, compact anomaly model, buffer, clock
      │  MQTT / OPC-UA / CCSP
L2  Adapters: canonical schema, validation, signing
      │
L3  Data platform: Kafka → stream QC → hot TSDB / cold Parquet / feature store / graph store
      │
L4  ┌───────────────────────── AI/ML ENGINE (this document) ─────────────────────────┐
    │ twin → baseline → anomaly → diagnosis → graph → survival → calibration → explain │
    └──────────────────────────────────────────────────────────────────────────────────┘
      │  model_run + risk_assessment + cluster + model_health  (write, append-only)
L5  Policy layer: risk → level, rank, persistence, alert budget (deterministic)
      │
L6  Backend API (/v1/*) → control room, field PWA, CRIS analytics
```

The AI engine **writes**; the policy layer **decides the level**; the backend **serves**. Keeping those three separate is what makes the system auditable: a reviewer can re-run the model, inspect the policy version, and reproduce the exact level a technician saw.

### 2.2 Two integration modes

| Mode | When | How |
|---|---|---|
| **Batch scoring worker** (default) | POC, bench, pilot | Reads a snapshot watermark from the TSDB, scores every circuit, writes one `model_run` and its assessments atomically |
| **Streaming micro-batch** | Scale-out | Flink micro-batches every 1–5 min per division; the same model artefacts, invoked through the same scoring function |

The worker is the only writer. The API never calls a model inline; a slow model must never block a field request.

### 2.3 Why the twin comes first

T1, T2 and T4 all consume the twin's outputs: effective ballast conductance ratio, relay margin ratio, and the standardised residual `z_t`. Without the twin, anomaly detection is generic and the explanation degrades to "the model said so" — precisely the black-box failure the project exists to avoid. The twin is therefore build step 1, not an optional refinement.

---

## 3. The Contract With the Backend

### 3.1 Field-by-field obligations

Every field below is already typed in `backend/app/models/alerts.py`. The engine must satisfy the type, the range and the stated invariant.

| Field | Type / range | Produced by | Invariant |
|---|---|---|---|
| `risk.h24`, `h72`, `h7d` | float 0–1 | T3 + T4 | `h24 ≤ h72 ≤ h7d` |
| `risk.eceZone` | float 0–1 | calibration | Must be measured, not asserted |
| `rul.p10Days`, `medianDays`, `p90Days` | int ≥ 0 | T4 + conformal | `p10 ≤ median ≤ p90` |
| `rul.coverage`, `rul.heldOutN` | 0–1, int > 0 | conformal evaluation | Coverage from the held-out set only |
| `likelyModes` | 1–3 of F1–F12, unique | T2 | Ordered by probability, descending |
| `modeProbability`, `modeSetCoverage` | 0–1 | T2 + conformal | Coverage is the empirical set coverage |
| `dataTrust.score` | 0–1 | data QC | Never suppresses an alert; only discounts rank |
| `dataTrust.flags` | enum list | data QC | From the closed set in §5.4 |
| `explanation.physics` | headline, 2–4 state items, falsifier | twin | Every number computed, never generated |
| `explanation.model.shapTop` | 1–5 signed features | T2/T3 | Values are SHAP contributions, not importances |
| `explanation.model.modeSet` | subset of `likelyModes` | T2 | Must equal the conformal set |
| `explanation.model.agreement` | high / medium / low | explainer | Rule in §9.4 |
| `explanation.precedents` | 0–3 items | retrieval | `similarity` 0–1, confirmed mode only |
| `ranking.calibratedRisk` | 0–1 | policy input | **Equals the horizon that drives the level**: `h24` for critical, `h72` for warning, `h7d` for watch |
| `ranking.consequence` | high / medium / low | policy | Traffic, alternative detection, season, failure cost |
| `ranking.trustDiscount` | 0–1 | data QC | `1 − penalty`, never zero |
| `clusterId`, `clusterRoot` | id / bool | T3 | Membership is derived, never stored on the asset |
| `persistence` | int ≥ 0 | T1 | Consecutive scoring windows the condition held |

**Hard rules.** `likelyModes` must never contain a mode outside F1–F12. `calibratedRisk` must reconcile with the horizon implied by the level. `rul.coverage` and `heldOutN` must come from the current evaluation run, not from a previous model version.

### 3.2 The `model_run` lifecycle

```text
queued → running → succeeded | failed
```

Each run records: `code_version`, `params` (JSONB), `input_watermark`, `dataset_hash`, `started_at`, `finished_at`, `status`. A run is **idempotent** on `(snapshot_id, code_version, params_hash)`: re-running the same snapshot with the same code and parameters must not create a second set of assessments.

### 3.3 Atomic snapshot publication

1. Compute all assessments in memory (or a staging table).
2. Validate every row against the Pydantic models — a contract test, not a convention.
3. Open a transaction: insert `model_run` as `succeeded`, insert all `risk_assessment` rows for the snapshot, update `alert.current_assessment_id`.
4. Publish `alert.upserted` to Redis after commit.
5. On any validation failure, insert `model_run` as `failed` with the reason and publish nothing.

A partially published snapshot is a bug: the control room must never see a half-scored division.

### 3.4 What the engine must **not** write

No table outside `model_run`, `risk_assessment`, `cluster` and the model-health materialisation. No `alert_event` (that is workflow), no `audit_log` (that is the backend), no asset master data, no block plan, no SMMS record. Draft work orders are produced by the backend from the assessment, not by the model.

---

## 4. Model Portfolio

### 4.1 The five tasks

| Task | Question it answers | Model | Primary metrics |
|---|---|---|---|
| **T1 Anomaly** | Is this circuit behaving abnormally for *itself*, given weather and traffic? | Twin residual + CUSUM/EWMA + temporal autoencoder + isolation forest | Lead time; false alarms per station-month; recall at fixed false-alarm budget |
| **T2 Diagnosis** | Which failure mode is this, and how sure are we? | LightGBM + temporal CNN/LSTM + conformal sets | Macro-F1; per-class recall; set size and coverage |
| **T3 Risk** | Which circuits will fail in 24 h / 72 h / 7 d, and which alarms share a cause? | Heterogeneous GNN + temporal encoder | PR-AUC; precision@k; ECE; Brier |
| **T4 Survival** | How many days of margin remain, with what uncertainty? | Bayesian Weibull/Cox with shared frailty | C-index; time-dependent AUC; integrated Brier; interval coverage |
| **T5 Dual detection** | Is a degrading circuit being masked by a parallel axle counter? | Rule + learned discrepancy model | Detection of injected masked decay; false-positive rate |

### 4.2 The ladder — and the rule for climbing it

| Rung | Model | Ships only if… |
|---|---|---|
| 0 | Fixed threshold on relay voltage/current | Baseline; always computed |
| 1 | Physics residual + CUSUM/EWMA | Beats rung 0 on lead time at equal false alarms |
| 2 | + temporal autoencoder + isolation forest | Beats rung 1 on recall at the alert budget |
| 3 | + mode classifier | Macro-F1 above the majority-class baseline by a useful margin |
| 4 | + common-cause graph | Beats the no-graph ablation on PR-AUC and precision@k |
| 5 | + survival and conformal | Beats constant-hazard Weibull on C-index and coverage |

If a rung does not beat the one below, **it is not shipped** and the result is reported. A simpler model that a DSTE can defend is worth more than a graph that wins on a synthetic leaderboard.

### 4.3 Deliberate exclusions

- No end-to-end deep model on raw waveforms: unidentifiable, unexplainable, and impossible to train on the available label volume.
- No LLM for risk, mode or RUL. Text is templated from computed fields (§9.5).
- No per-circuit model without the shared layers: 500 circuits × 12 classes × rare failures is not a learning problem, it is a data problem.
- No train/test shuffle, ever.

---

## 5. Data and Feature Specification

### 5.1 Sources, in preferred order

| Group | Signals | Preferred source | Fallback |
|---|---|---|---|
| Electrical | Feed and relay voltage/current, pick-up/drop-away timing, ripple/noise, bus voltage; phase/frequency for AC/AF | Existing data logger / RDPMS export | Isolated high-impedance taps |
| Occupancy | Occupied/free transitions, train counts, axle-counter counts and resets, route settings | EI log, data logger, axle-counter health output | — |
| Environment | Temperature, humidity, rainfall, enclosure humidity, surge/lightning count | Local sensors + public weather feed | Station records |
| Maintenance | Failures with cause codes, work history, asset age vs codal life, Rolling Block plan | SMMS export | Division registers |
| Topology | Station layout, circuit type and length, cable route, supply group, drain/cess layout | Design drawings, SMMS asset master | Field survey |

### 5.2 Feature groups

| Group | Examples | Window |
|---|---|---|
| Level | Relay current, feed voltage, ballast conductance ratio, relay margin ratio | 1 min, 15 min |
| Trend | 7-day and 30-day slope, slope ratio vs seasonal norm, change-point age | 7 d, 30 d |
| Timing | Pick-up delay, drop-away delay, p95 delay, timing variance | Per movement, 7 d |
| Quality | Gap count, stuck-value runs, interpolation share, clock skew | 24 h |
| Environment | Rain 24/72 h, rain vs 30-day norm, temperature, humidity, surge count | 1 h, 72 h |
| Traffic | Movements/day, loaded/unloaded mix, night quiet ratio | 7 d |
| Maintenance | Days since repair, repair count 12 m, age/codal-life ratio, block history | Event-based |
| Graph | Shared supply/cable/room/weather-cell degree, neighbour risk mean, cluster size | Snapshot |
| Physics | Twin state, innovation, residual `z_t`, parameter uncertainty | 1 min |

### 5.3 Windows and cadence

| Artefact | Cadence | Rationale |
|---|---|---|
| Raw telemetry | 10 s – 1 min | Matches logger sampling in vendor plans |
| Stream QC aggregates | 10 s / 1 min | Gap and stuck detection |
| Feature snapshot | 5 min | Scoring input |
| Anomaly + diagnosis | 5 min | Worklist freshness |
| Graph | 15 min | Cluster formation |
| Survival / RUL | Nightly, plus on trigger | Censoring needs history |
| Retrain | Monthly, shadow | Drift control |

### 5.4 Data trust and its flags

Trust is a property of the *evidence*, not of the asset. The score starts at 1.0 and is penalised for:

| Flag | Trigger | Penalty |
|---|---|---|
| `logger_gap_6h` | Gap ≥ 6 h in the last 24 h | −0.15 per gap, capped |
| `stuck_value_run` | ≥ 30 identical consecutive readings | −0.10 |
| `age_vs_signature_mismatch` | Recorded age inconsistent with observed wear | −0.10 |
| `shunt_pattern_review` | Shunt signature outside expectation | −0.05 |
| `predicted_cascade` | Risk driven mainly by a neighbour, not own evidence | −0.05 |
| `clock_skew` | Timestamp offset above tolerance | −0.10 |

Trust **discounts rank; it never suppresses an alert**. A low-trust circuit with a high raw risk still appears, visibly marked — silence is more dangerous than a flagged uncertainty.

### 5.5 Leakage traps to design against

1. Post-repair data leaking into a pre-failure window.
2. Station-level correlation leaking across a random split.
3. A feature computed with future data (e.g. a 30-day slope centred on the event).
4. Target-derived features: `days_to_failure` must never be an input.
5. Duplicate assets across train and test (same circuit re-exported under two IDs).
6. Seasonal leakage: training on monsoon, testing on monsoon.

Each trap gets an explicit unit test (§17).

---

## 6. NIDAN-Bench

No public Indian track-circuit time-series dataset was found [R40]. The benchmark is therefore a **first-class deliverable**, not a test fixture: it is how models are trained, compared and regressed before any field data exists.

### 6.1 Design

- **Generator:** a transmission-line twin per circuit, driven by synthetic weather, traffic and maintenance calendars.
- **Ground truth:** the hidden state trajectory (`G_b(t)`, `r_eff(t)`, joint state, supply state), the event time, and the cause code.
- **Domain randomisation:** circuit length 0.3–1.5 km; rail loop resistance 0.05–0.20 Ω/km; ballast resistivity 0.5–50 Ω·km; feed 5.5–7.0 V; relay 4–12 Ω; traffic 0–120 movements/day; rain 0–150 mm/72 h; temperature 5–45 °C; surge rate per season.
- **Noise and faults in the data, not just the label:** logger gaps, stuck values, clock skew, quantisation, missing environment channels — so models learn robustness rather than a clean simulation.
- **Determinism:** every scenario takes a seed; identical seed and version produce byte-identical output.

### 6.2 Scenarios

| Scenario | Injects | Primary use |
|---|---|---|
| `monsoon-60d` | F1 ballast decline 8.0 → 1.5 Ω·km over 60 days | T1 lead time; the exhibition demonstration |
| `monsoon-fast` | Exponential F1 onset | T1 robustness to onset shape |
| `lightning-cluster` | F7 surge hitting several circuits on one cable route | T3 clustering |
| `supply-sag` | F6 correlated dips across one supply group | T3, T5 |
| `relay-ageing` | F5 timing drift over 180 days | T2, T4 |
| `points-bridging` | F4 intermittent partial shunt | T2, T5 |
| `cable-ingress` | F8 insulation decline on one branch | T2, T4 |
| `masked-decay` | F1 + healthy axle counter in parallel | T5 |
| `rail-break-step` | F3 step change | T2 (hard, rare) |
| `nff-flicker` | F12 short unexplained flickers | T1 flicker feature |
| `traction-noise` | F10 harmonic rise | T1 robustness |
| `config-drift` | F11 reset pattern after an alteration | T1, advisory only |

### 6.3 Splits

- Time-ordered train / validation / calibration / test.
- Group by station, so no station appears in two splits.
- Leave-one-zone-out as a generalisation check.
- Hold out one full monsoon season.
- A `sim-to-real` split: train on synthetic, fine-tune on a small real slice, test on held-out real.

### 6.4 Versioning

The bench is versioned (`nidan-bench/0.1`) and its manifest hash is recorded in every `model_run`. A metric is meaningless without the bench version that produced it.

---

## 7. Physics Twin

### 7.1 Model

A uniform lossy transmission line: series rail resistance `r` (Ω/km), shunt ballast conductance `g = 1/R_b` (S/km), source at `x = 0`, relay at `x = L`. The ABCD matrix gives relay current for a given ballast resistivity and occupancy state. The reference implementation is dossier Appendix C (`nidan_twin.py`, illustrative parameters, not calibrated to any Indian circuit).

### 7.2 Estimation

- **State:** effective ballast conductance `G_b`, a lumped series term `r_eff` (rail + bonds + joints), and supply state (feed voltage, source resistance) where observable.
- **Filter:** Unscented Kalman Filter over the non-linear measurement function; process noise on `G_b` and `r_eff`, measurement noise from logger specification.
- **Priors:** circuit design data (length, type, feed, relay) and a per-division prior on dry ballast resistivity.
- **Outputs:** `G_b` ratio vs dry baseline, relay margin ratio, innovation, residual `z_t`, and parameter uncertainty.

### 7.3 Identifiability — stated honestly

With only feed-end and relay-end measurements, not every parameter is separately identifiable. The design response is deliberate:

1. Estimate an **effective** conductance, not a physical soil property.
2. Use Bayesian priors from design data to constrain the rest.
3. Add a second tap or use AC/AF phase information where available (patented phase-of-impedance methods support this [R51]).
4. Report parameter uncertainty, and let the explainer say "effective" rather than over-claiming.

### 7.4 What the twin must reproduce

| Check | Expectation |
|---|---|
| Dry circuit | Relay current within 1% of the analytic series solution |
| Ballast sweep | Monotone decline; the documented 96.7% / 53.9% / 28.8% illustration reproduced within tolerance |
| Occupancy | Relay current collapses on shunt; recovery on clear |
| Inverse estimate | Recovers injected `G_b` within 10.4% at the documented checkpoints |
| Determinism | Same inputs and seed → identical output |

The twin is **not** claimed to be calibrated to Indian Railways. It is a mechanism proof and a feature generator until a pilot provides real circuits.

---

## 8. Task Specifications

### 8.1 T1 — Anomaly detection

**Purpose.** Detect abnormal behaviour relative to the circuit's own weather- and traffic-conditioned baseline, with enough persistence to survive alarm fatigue.

**Inputs.** `z_t` residual, twin states, level and trend features, environment, traffic, quality.

**Method.**

1. Context baseline: per-circuit regression of the expected signal on temperature, humidity, rain history and traffic; standardised residual `z_t`.
2. CUSUM (two-sided) and EWMA on `z_t`.
3. Temporal autoencoder (TCN or LSTM) on 24 h windows; reconstruction error as a score.
4. Isolation forest on 30 summary features.
5. Fusion: require persistence (N consecutive windows) **and** cross-signal agreement before a Watch-level candidate; add a flicker-rate feature for F12.

**Outputs.** Anomaly score 0–1, persistence count, contributing signals, and the physics headline that feeds the explanation.

**Metrics.** Lead time before the event; false alarms per station-month; recall at a fixed false-alarm budget. Not AUC alone.

**Exit criterion.** On `monsoon-60d`, detects injected drift with a measurable lead and no more than the agreed false-alarm budget across the bench; the documented 33-day lead is reproduced as a *scenario property*, not quoted as field performance.

### 8.2 T2 — Fault diagnosis

**Purpose.** Name the likely failure mode, with a set that is right at a stated coverage.

**Inputs.** Windowed features (5 min / 1 h / 24 h / 7 d), twin states, environment, maintenance history.

**Method.** LightGBM multiclass plus a temporal CNN/LSTM; class weights for rarity; synthetic pre-training with domain randomisation, then fine-tuning on any available field labels; conformal prediction (APS/RAPS) for the output set.

**Scope.** First release: **F1, F3, F5, F6, F12**. Expand to F2, F4, F7, F8 only when the bench and any field labels support it. F9–F11 are advisory-only until validated.

**Outputs.** Top ≤3 modes, `modeProbability`, conformal `modeSet`, `modeSetCoverage`, and TreeSHAP top features.

**Metrics.** Macro-F1, per-class recall, set size, empirical coverage.

**Exit criterion.** Beats the majority-class and per-circuit-LSTM baselines on macro-F1; coverage within tolerance of nominal on held-out data; set size operationally usable (≤3).

### 8.3 T3 — Short-horizon risk and common-cause graph

**Purpose.** Rank circuits by failure probability in 24 h / 72 h / 7 d, and group alarms that share a cause.

**Graph.**

```text
V: track circuits, point machines, signals, axle-counter sections,
   relay rooms, power supplies, cable segments, weather cells
E: e1 weather-cell (co-location)
   e2 shared-asset (power, cable, room, network)
   e3 interlocking / route dependency
   e4 work-history (same crew, job or time window)
X: twin states, anomaly scores, age, last maintenance, environmental covariates
```

**Method.** Heterogeneous GNN (GraphSAGE/GAT per edge type) with a GRU/TCN temporal encoder; output `p_i(h)` for the three horizons and a cluster posterior `P(common root cause | alarms in window)`. Cluster membership is derived from the posterior plus shared edges, never written onto the asset.

**Baselines that must be beaten.** No-graph per-circuit model; Hawkes self-exciting process; Bayesian network cause attribution.

**Outputs.** Horizon risks, `clusterId`, cluster root candidate, member list, cascade window.

**Metrics.** PR-AUC, precision@k on the daily worklist, ECE, Brier.

**Exit criterion.** Beats the no-graph ablation on PR-AUC and precision@k with a station-level bootstrap confidence interval that excludes zero; if not, ship the per-circuit model and report the negative result.

### 8.4 T4 — Survival and remaining useful life

**Purpose.** Convert a snapshot into calibrated days-to-failure, correctly handling circuits that have not yet failed.

**Model.**

```text
h_i(t | x_i(t), u) = h0(t) · exp(β'x_i(t) + u_station + u_supply + u_climate)
h0: Weibull (interpretable) or neural (BNN-Surv style)
x : twin trends, age vs codal life, anomaly burden, maintenance history, climate
```

**Censoring.** Right-censored (still working) and left-truncated (installed before records began). Maintenance is a **competing event** or a time-varying covariate — otherwise the estimate is biased.

**Outputs.** Survival curve, median RUL, p10/p90, conformal interval, coverage and `heldOutN`.

**Metrics.** C-index, time-dependent AUC, integrated Brier score, interval coverage.

**Exit criterion.** Beats constant-hazard Weibull on C-index; 80% interval coverage lands in 75–85% on held-out data; calibration stable across divisions.

### 8.5 T5 — Dual-detection consistency

**Purpose.** Surface a circuit that is degrading but hidden because a parallel axle counter keeps the route clear.

**Method.** Rule layer (track circuit says clear while axle counter says occupied; drop-away delay abnormal; repeated resets) plus a learned discrepancy classifier over paired streams. Requires both streams; if axle-counter events are unavailable, T5 is **off**, not faked.

**Evidence base.** The CAG finding at Rura (DC track-circuit failure at 02:16:47 on 28.12.2016, not investigated before the 05:30 derailment) and new interlocking designs that place axle counters in parallel with DC circuits.

**Metrics.** Detection rate on injected masked decay; false-positive rate on healthy dual-detection pairs.

**Exit criterion.** Detects the injected `masked-decay` scenario at the agreed rate with a false-positive rate acceptable to the pilot partner.

---

## 9. Explanation Layer

### 9.1 Three lenses, one object

| Lens | Content | Source |
|---|---|---|
| **Physics** | Headline, 2–4 state items (value vs baseline), falsifier | Twin |
| **Model** | 1–5 signed SHAP features, conformal mode set, agreement | T2/T3 |
| **Precedent** | Up to 3 confirmed SMMS cases with similarity and outcome | Retrieval |

The falsifier is mandatory. It states what observation would prove the explanation wrong — e.g. *"If drop-away is under 0.5 s on the next five movements, the pattern is a logger timing artefact, not F9."* A claim that cannot be falsified is not an explanation.

### 9.2 Physics text

Templated, slot-filled from computed values:

```text
"Effective ballast conductance +{delta}% in {days} days;
 relay margin {margin}% of dry; rain {rain} mm in 72 h vs {norm} mm median."
```

No free generation. Every number is a field in the assessment.

### 9.3 SHAP

TreeSHAP for the GBM; Integrated Gradients (or a surrogate) for the temporal model. Report **signed contributions**, not global importances. Cap at five features; the UI renders a force plot. Feature names are human labels, not column names.

### 9.4 Precedents and agreement

- Similarity: scaled Euclidean distance over the top features, plus same-mode and same-station/drain bonuses; require a confirmed cause; threshold 0.6.
- `agreement`:
  - **high** — physics driver and top SHAP feature point the same way, and the mode set is a singleton.
  - **medium** — same direction but a multi-mode set.
  - **low** — physics and model disagree, or the set is wide, or trust is low.
- Low agreement is shown, never hidden. It is a signal to the technician, not a failure of the UI.

### 9.5 Guardrails

1. No LLM in the decision path; optional drafting of the SMMS note is downstream and clearly labelled.
2. Every sentence traces to a computed field.
3. Precedents must be real rows; no synthetic "similar case" may be presented as history.
4. Explanations are versioned with the model that produced them.

---

## 10. Calibration and Uncertainty

- **Split conformal** on a dedicated, time-ordered calibration set, never the test set.
- **Mondrian by level and division**: separate calibration for watch/warning/critical and for each division, so a wet zone is not calibrated against a dry one.
- **RUL intervals** on log-time residuals; report empirical coverage and `heldOutN`.
- **Abstention**: if the conformal set exceeds three modes, or coverage on the last window falls outside tolerance, the assessment is emitted with reduced confidence and a visible flag — not silently widened.
- **Recalibration** per zone on a schedule and on drift trigger; a recalibration is a new model version and a new gate pass.

---

## 11. Policy Handoff

The model outputs calibrated quantities; the policy layer turns them into the level and rank a human sees. This separation is deliberate: thresholds must be tunable in shadow mode without retraining, and auditable without reading model code.

### 11.1 Level rules (design choice, versioned `policy-2026.07`)

| Level | Rule | Action |
|---|---|---|
| Info | Anomaly persistent, low confidence | Logged only |
| Watch | `h7d > 0.20` **or** `p10Days < 30`, with persistence | Appears on the SSE/JE worklist |
| Warning | `h72 > 0.30` **or** margin below the early-warning level | Work order proposed; next block |
| Critical | `h24 > 0.50` with high confidence **or** cluster root cause detected | Immediate notification; special block proposed |

### 11.2 Invariants enforced downstream

- Database `CHECK` constraints (`critical_rule`, `warning_rule`) must agree with the policy version; a model cannot publish a level its own risk contradicts.
- `policyRank` is unique per division and 1-based.
- `calibratedRisk` equals the horizon that drove the level (§3.1).
- Persistence counts consecutive scoring windows, not raw samples.
- An alert budget per section per day limits notifications; it is tuned in shadow mode, not guessed.

### 11.3 Consequence

Consequence combines traffic density, availability of alternative detection (parallel axle counter), proximity to monsoon, and cost of failure. Rank is `calibratedRisk × consequence × trustDiscount` with a documented tie-breaker. The engine supplies the inputs; the policy computes the rank.

---

## 12. Evaluation Protocol

| Element | Rule |
|---|---|
| Splits | Time-ordered; never shuffled across time |
| Leakage | Group by station; exclude post-repair data from pre-failure windows; calibration set separate from test |
| Generalisation | Leave-one-zone-out; hold out a full monsoon season |
| Sim-to-real | Train synthetic → fine-tune small real → test held-out real |
| Censoring | Maintenance as competing event or time-varying covariate |
| Ablations | Remove physics, graph, survival, conformal — one at a time |
| Statistics | Bootstrap confidence intervals at station level |
| Reporting | Model card, calibration plot, reliability bins, failure-case gallery |

### 12.1 Acceptance targets (pilot, to be agreed)

| Metric | Target |
|---|---|
| Median lead time, drift-type Warning | ≥ 72 h |
| Precision@10, daily worklist | ≥ 0.5 |
| False Watch alerts | ≤ 1 per station-month |
| ECE (10 bins) | ≤ 0.05 |
| RUL interval coverage (nominal 80%) | 75–85% |
| Subgroup coverage gap across divisions | ≤ 0.04 |
| Technician acceptance | ≥ 70% |
| SMMS entry time | −50% vs baseline |

### 12.2 Reporting rules

- Every number states its bench version, seed, split and model version.
- A synthetic lead time is labelled a **scenario property**.
- A published accuracy from another system is never restated as ours.
- Negative results are reported with the same care as positive ones.

---

## 13. Promotion Gates and Shadow Mode

A model version moves `shadow → active` only when all gates pass, on data it has not seen, with sign-off recorded in the registry.

| Gate | Rule | Source of truth |
|---|---|---|
| Calibration | ECE ≤ 0.05 over 10 bins | Held-out evaluation |
| Coverage | Conformal coverage 0.88–0.92 | Held-out evaluation |
| Subgroup parity | Coverage gap ≤ 0.04 across divisions | Per-division evaluation |
| Drift | PSI ≤ 0.20 on monitored features | Production window |
| Shadow period | ≥ 28 days in shadow | Registry timestamps |
| Safety | Zero vital-path endpoints or writes | Contract test |
| Contract | All rows validate against the Pydantic models | CI |

Failure of any gate returns the model to shadow with a written reason. Rollback is a registry pointer change, not a redeploy.

---

## 14. Runtime and Orchestration

### 14.1 Scoring worker

```text
1. Claim snapshot (watermark, division)
2. Load features from the feature store
3. Twin → T1 → T2 → T3 → T4 → calibration → explainer
4. Build assessments; validate against backend models
5. Transaction: model_run(succeeded) + risk_assessment rows + alert pointer
6. Publish alert.upserted to Redis
7. Record metrics: latency, row counts, gate values
```

- **Idempotent** on `(snapshot_id, code_version, params_hash)`.
- **Bounded**: a division of 500 circuits must score in under 60 s on CPU at POC scale.
- **Fail-closed**: a validation error aborts the whole snapshot; nothing partial is published.
- **Replayable**: the same snapshot and seed reproduce the same assessments.

### 14.2 Compute

| Component | POC | Scale-out |
|---|---|---|
| Twin + T1 + T2 | CPU, seconds per circuit | Same, horizontally partitioned by division |
| Graph | CPU, small graph per division | GPU optional above ~10k nodes |
| Survival | CPU, nightly | CPU |
| Explainer | CPU, per alert | Cached by assessment hash |

No GPU is required for the POC. That is a feature: it keeps the pilot deployable on railway-approved infrastructure.

### 14.3 Artefacts and registry

Each model version stores: code version, parameters, bench version and hash, training window, evaluation report, model card, calibration plots, and the artefact itself. The registry is the single source of truth for `/v1/models/health`.

---

## 15. MLOps and Monitoring

| Concern | Monitor | Action |
|---|---|---|
| Feature drift | PSI per feature, threshold 0.20 | Investigate; retrain if sustained |
| Calibration drift | Rolling ECE and coverage | Recalibrate per zone |
| Data trust | Flag rate, low-trust asset count | Data-quality ticket; never suppress |
| Label drift | Mode mix, cause-code distribution | Review taxonomy mapping |
| Performance | Lead time, precision@k, false alarms | Shadow comparison |
| Latency | Scoring time per division | Partition or optimise |
| Lineage | `model_run` ↔ dataset hash ↔ artefact | Audit query |

Retraining is monthly and always in shadow. Promotion follows §13. Every production assessment carries the model versions that produced it, so a review can reconstruct the exact judgement months later.

---

## 16. Repository Layout and Implementation Plan

### 16.1 Proposed layout

```text
ai/
├─ pyproject.toml
├─ README.md
├─ nidan_ai/
│  ├─ config.py                 # paths, seeds, thresholds, version pins
│  ├─ schemas.py                # re-exports/validates backend Pydantic models
│  ├─ data/
│  │  ├─ canonical.py           # telemetry + event loaders
│  │  ├─ features.py            # windowing, slopes, flicker, timing
│  │  └─ quality.py             # trust score and flags
│  ├─ bench/
│  │  ├─ generator.py           # domain-randomised stream generator
│  │  ├─ faults.py              # F1–F12 injectors
│  │  ├─ scenarios.py           # monsoon-60d, lightning-cluster, masked-decay…
│  │  └─ manifest.py            # version + hash
│  ├─ physics/
│  │  ├─ line.py                # transmission-line solve
│  │  └─ twin.py                # UKF state estimation
│  ├─ models/
│  │  ├─ anomaly.py             # T1
│  │  ├─ classifier.py          # T2
│  │  ├─ graph.py               # T3
│  │  ├─ survival.py            # T4
│  │  ├─ dual_detection.py      # T5
│  │  └─ conformal.py           # calibration
│  ├─ explain/
│  │  ├─ shap.py
│  │  ├─ precedents.py
│  │  └─ narrative.py           # templated physics text + falsifier
│  ├─ policy/
│  │  └─ levels.py              # risk → level, rank inputs
│  ├─ eval/
│  │  ├─ splits.py
│  │  ├─ metrics.py
│  │  └─ report.py              # model card, calibration plot
│  └─ worker/
│     ├─ run.py                 # scoring worker
│     └─ publish.py             # atomic model_run + assessments
└─ tests/
   ├─ test_contract.py
   ├─ test_twin.py
   ├─ test_bench.py
   ├─ test_leakage.py
   ├─ test_metrics.py
   └─ test_determinism.py
```

### 16.2 Phases

| Phase | Timing | Scope | Exit criterion |
|---|---|---|---|
| **A0 — Skeleton and contract** | Week 1 | Package, schemas, bench manifest, CI, contract tests against backend models | A synthetic assessment validates end to end |
| **A1 — Twin** | Weeks 2–3 | Line solve, UKF, inverse estimate, determinism | Reproduces the documented illustration and the 10.4% recovery check |
| **A2 — Features and T1** | Weeks 3–5 | Feature store contract, context baseline, CUSUM/EWMA, autoencoder, fusion | Detects `monsoon-60d` drift with measurable lead inside the false-alarm budget |
| **A3 — T2** | Weeks 5–7 | Classifier, synthetic pre-training, conformal sets, SHAP | Macro-F1 above baseline; coverage in tolerance; set ≤ 3 |
| **A4 — T3** | Weeks 6–9 | Graph construction, heterogeneous GNN, cluster posterior, ablations | Beats no-graph and Hawkes on PR-AUC and precision@k |
| **A5 — T4 and calibration** | Weeks 8–11 | Frailty survival, censoring, conformal RUL, per-zone calibration | C-index above constant-hazard; coverage 75–85% |
| **A6 — Explainer and worker** | Weeks 10–12 | Three lenses, precedents, templated text, atomic publish, model card | One command produces a valid `model_run` and the UI renders real values |

Phases overlap deliberately: T2 can start once features exist, and the graph can start once per-circuit scores exist. Integration with the backend is a Phase A6 activity, matching backend Phase 3.

### 16.3 Definition of done for the exhibition

```bash
python -m nidan_ai.worker.run --scenario monsoon-60d --seed 42 --publish
```

…produces a `model_run`, a full set of validated `risk_assessment` rows, clusters, and a model-health snapshot that the existing frontend renders without a single UI change. That is the demonstration: not a slide about a model, but the real pipeline writing to the real contract.

---

## 17. Testing Strategy

| Test | What it proves |
|---|---|
| `test_contract` | Every emitted row validates against `backend/app/models/`; `h24 ≤ h72 ≤ h7d`; `p10 ≤ median ≤ p90`; `calibratedRisk` matches the level's horizon |
| `test_twin` | Analytic dry case, monotone ballast sweep, occupancy collapse, inverse recovery, determinism |
| `test_bench` | Seed reproducibility; ground-truth event times; scenario manifests stable |
| `test_leakage` | Split boundaries; no post-repair data in pre-failure windows; no station overlap |
| `test_metrics` | ECE, coverage, C-index, precision@k, PSI against hand-computed fixtures |
| `test_determinism` | Same seed and version → byte-identical assessments |
| `test_safety` | No vital endpoint, no write path, no actuation surface |
| Golden scenarios | `monsoon-60d` produces the expected alert count and lead within tolerance |

Property tests worth having: lower ballast resistivity never lowers risk; adding a confirming signal never lowers confidence; a wider conformal set never increases claimed coverage.

---

## 18. Risks and Open Questions

| # | Risk | Mitigation |
|---|---|---|
| 1 | No field data | Bench + bench-first evaluation; pilot MoU; never claim field accuracy |
| 2 | Parameter identifiability | Effective parameters, priors, second tap where available, stated uncertainty |
| 3 | Label scarcity | Synthetic pre-training, self-supervision, survival with censoring, active learning |
| 4 | Class imbalance | Subset of modes first; class weights; conformal sets instead of forced single labels |
| 5 | Graph overfitting | No-graph ablation is a hard gate; station-level bootstrap CIs |
| 6 | Alarm fatigue | Persistence, cross-signal agreement, alert budget, shadow tuning |
| 7 | Calibration drift by season | Per-zone Mondrian calibration; monsoon holdout; drift trigger |
| 8 | Model/backend version skew | Contract tests in CI; `model_run` records code, params and bench hash |
| 9 | Explainer over-claiming | Templated text only; falsifier mandatory; precedents must be real rows |
| 10 | Scope creep to twelve modes | Phase gates; F1/F3/F5/F6/F12 first |

**Open questions for the domain review.**

1. Which SMMS cause-code list will the pilot zone expose, and how does it map to F1–F12?
2. DC-only or DC + AC in the first release? (Recommendation: DC station circuits first.)
3. Are axle-counter events available for T5, or does T5 stay off in phase 1?
4. Is a second tap permitted, or is the design limited to logger exports?
5. What is the retention policy for raw telemetry, and does it cover a full monsoon?
6. Which division supplies the calibration set, and who signs the model card?

---

## Appendix A — Metric Definitions

| Metric | Definition |
|---|---|
| **Lead time** | Time between the first qualifying alert and the ground-truth failure event |
| **False alarms per station-month** | Watch-or-above alerts with no confirmed cause, normalised by station-months |
| **Precision@k** | Share of the top-k worklist items that fail or are confirmed within the horizon |
| **ECE** | Expected calibration error over 10 equal-frequency bins: Σ (n_b/N)·|observed − predicted| |
| **Coverage** | Share of held-out outcomes inside the conformal interval or set |
| **C-index** | Concordance of predicted risk ordering with observed time-to-event |
| **Integrated Brier** | Time-integrated squared error of predicted survival probabilities |
| **PSI** | Population Stability Index between reference and current feature distributions |

## Appendix B — Failure Taxonomy to Feature Map

| Mode | Signature | Primary features | Primary task |
|---|---|---|---|
| F1 Low ballast resistance | Slow relay-current decline, worse after rain | `G_b` ratio, relay margin, rain 72 h | T1, T2, T4 |
| F2 Insulated joint failure | Leakage to neighbour, polarity anomaly, flicker | Neighbour current, flicker rate | T2 |
| F3 Rail bond / break | Step change, rising impedance | Step detector, `r_eff` jump | T1, T2 |
| F4 Points bridging | Persistent partial shunt at points | Gap resistance, bridging events | T2, T5 |
| F5 Relay ageing | Slower pick/drop, higher variance | Pick-up/drop-away slope, operations count | T2, T4 |
| F6 Supply / feed fault | Voltage sag, ripple, correlated circuits | Feed minimum, dip events, supply group | T2, T3 |
| F7 Lightning / surge | Many sections together, surge spike | Surge count, cluster simultaneity | T3 |
| F8 Cable fault | Intermittent open/short along a route | Insulation slope, route correlation | T2, T3 |
| F9 Shunting failure | Poor shunt signature, slow drop | Drop-away p95, rail surface index | T2 (advisory) |
| F10 Traction interference | Noise floor rise, spurious drops | Harmonic energy, noise floor | T1 |
| F11 Maintenance / config error | Anomaly after alteration, repeated resets | Reset pattern, change-point vs work order | T1 (advisory) |
| F12 No-fault-found | Short unexplained flickers | Flicker rate, intermittency | T1 |

---

**Document status.** Specification for implementation. It defines the engine behind the frozen backend contract; it does not claim that engine exists, that any model is trained, or that any result is field-validated. Every quantitative example cited from the research dossier remains a simulation or design illustration until a pilot replaces it with measured data.
