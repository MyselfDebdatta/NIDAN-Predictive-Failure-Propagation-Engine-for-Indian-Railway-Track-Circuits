# NIDAN — Exhibition Registration Form Answers

**Prepared:** 24 November 2026 · **Version:** 1.0
**Basis:** `docs/Research/Debdatta-Complete-Research.md` (v1.1, 22 Nov 2026), `Frontend-Complete-Research-Implementation.md`, `design/brand/Logo-and-Brand-Guidelines.md`, and the shipped POC/simulator in this repository.

> **How to use this document.** Every answer starts with a **copy-ready short answer** that fits a typical Google Form text box. Below it is the full, research-backed detail you can use if the field allows long answers, or for the follow-up discussion with the industry experts.
>
> **Citation convention:** `[R1]`…`[R77]` are verified source tags that resolve to full links in **§24 of the research dossier**. Statements marked **[Assumption]**, **[Estimate]** or **[Design choice]** are our own engineering judgements, not measured field results. **No field accuracy is claimed** — the current POC is simulation- and lab-bench-based.

---

## Quick-fill summary

| # | Question | Short answer |
|---|---|---|
| 1 | Project Title | **NIDAN (निदान) — Predictive Failure Propagation Engine for Indian Railway Track Circuits** |
| 2 | Project Category | Railways → Signalling & Safety-Critical Systems → Predictive Maintenance / AI-ML analytics (advisory, non-vital) |
| 3 | Brief Description | A vendor-neutral advisory layer that reads existing track-circuit data with a physics twin, finds shared root causes, predicts remaining life with uncertainty, and explains every alert — so maintainers fix faults days before trains stop. |
| 4 | Detailed Description | See §4 — problem, corrected landscape, six-layer architecture, method, novelty, evidence and safety stance. |
| 5 | Tech Stack | POC: Python/NumPy/SciPy physics simulator + seeded synthetic benchmark + static HTML/CSS/JS screens. Production: React 19 + TypeScript + Vite, Kafka/Flink, PyTorch Geometric, Bayesian survival, SHAP. **Future optimisation:** isolated sensors, Hall/Rogowski clamps, ARM edge gateway, MQTT/OPC-UA and CCSP-compliant interface. |
| 6 | Unique & Innovative | First combination of physics twin + four-edge common-cause graph + dual-detection masking monitor + Bayesian RUL with conformal uncertainty + three-part explanation + SMMS auto-fill, built for Indian RDPMS/SMMS reality. |
| 7 | Target Users | S&T maintainers (SSE/JE/ESM), Station Masters/controllers, divisions/zones, RDSO/CRIS/Railway Board, RDPMS OEMs, project agencies, metros/DFCCIL; passengers and freight are beneficiaries. |
| 8 | Real-world Impact | Fewer false-occupied failures and delays, risk-ranked work inside Rolling Block windows, ~50% less SMMS entry time, fewer unnecessary track walks; highest value in monsoon/lightning-prone zones. |
| 9 | Future Plan | 16-week MVP (simulator → data platform → intelligence → bench) → 5–10 month shadow pilot → 10–18 month CRIS/RDSO integration → 18–36 month multi-zone scale-out. |
| 10 | Additional Notes | Needs a zone/OEM data MoU, RDSO review and Rail Tech 50:50 co-funding; strictly advisory and non-vital; all current results are simulated/bench, not field-validated. |

---

# 1) Project Title

**NIDAN (निदान) — Predictive Failure Propagation Engine for Indian Railway Track Circuits**

- **Tagline:** *Find the cause before the failure. Predict. Explain. Prevent.*
- **Hindi / Sanskrit:** *निदान* means diagnosis and the determination of the root cause; *निदानम्* in Sanskrit means cause, origin and diagnosis. The name mirrors the Railway Board's own programme name, RDPMS — Remote Diagnostic and Predictive Maintenance System [R1].
- **Bilingual lock-up:** NIDAN | निदान — Predictive Failure Propagation Engine for Indian Railway Track Circuits.

---

# 2) Project Category

**Primary category:** Railways → Signalling & Safety-Critical Systems → Predictive Maintenance / AI-ML Analytics.

**Select the closest matching option in the form:**

| If the form offers… | Choose… |
|---|---|
| A domain / sector category | **Railways / Transportation & Logistics** |
| A technology category | **Artificial Intelligence & Machine Learning for Infrastructure Reliability** |
| An application category | **Predictive Maintenance / IoT & Asset Health Monitoring** |
| A safety / critical-systems category | **Safety-Critical Systems — advisory, non-vital analytics** |

**Important positioning note:** NIDAN is **not** a signalling control product. It is a read-only intelligence layer that *observes* the vital chain and never modifies it. If the form asks for "hardware" vs "software" classification, choose **software / decision-support**, with hardware sensing listed as a future optimisation (see answer 5).

---

# 3) Brief Project Description

> **Copy-ready:** Indian Railways detects track-circuit failures mostly after a relay drops and a train stops, while the slow degradation behind them stays invisible. NIDAN is a vendor-neutral, advisory-only intelligence layer that watches each circuit's electrical "pulse", estimates hidden physical parameters with a transmission-line digital twin, groups alarms that share a root cause, predicts remaining useful life with calibrated uncertainty, and hands the maintainer a ranked, already-explained work item that fits a Rolling Block window. The current prototype is a reproducible software simulation plus a static UI; no vital signalling is touched.

**Supporting points (use if space allows):**

- **Scale of the problem:** 6,665 stations have complete track circuiting and 6,660 have electrical/electronic interlocking [R5]; 99.2% of broad-gauge route-km is electrified, making traction interference a daily concern [R15b].
- **The gap is officially recorded:** Railway Board minutes of 31 January 2025 note ~100+ RDPMS stations with different OEM business rules, small datasets for AI/ML, and a unified dashboard still to be built [R1]. RDSO has since published the standard **RDSO/SPN/257/2025 v2.0**, effective 31.12.2025 [R69].
- **Our answer:** the analytics layer that sits on those feeds — physics + graph + survival + explainability — not another OEM monitor and not a control system.
- **Current status:** physics simulator, seeded 60-day drift experiment, seven-screen UI prototype and a documented pilot plan. **No field accuracy is claimed yet.**

---

# 4) Detailed Project Description

## 4.1 The problem, precisely

A track circuit feeds a small current into the two rails; a relay at the far end stays energised while the section is clear. Train axles shunt the rails, the relay drops, and the section is read as occupied. The circuit is **fail-safe** — a failure also looks like "occupied" — so it protects safety but costs availability [R52].

What goes wrong is slow and hidden:

- **P1 — Silent degradation.** Wet, fouled or muddy ballast lowers resistance, relay current declines over days or weeks, and nobody sees the shrinking margin until the relay drops. Indian practice requires at least **2 ohm-km in yards and 4 ohm-km in block sections** [R50]; Railway Board's 2024 monsoon circular requires **50 mm ballast clearance below the rail foot** and 100% insulated liners in track-circuited areas [R14].
- **P2 — Reactive maintenance.** Official statements describe signalling maintenance as manual and find-and-fix; CAG found that even where 100% of required maintenance blocks were granted, failures continued [R10][R25].
- **P3 — Fragmented data.** RDPMS data are OEM-specific; SMMS holds assets and failures digitally but depends on manual entry — Western Railway alone has 3,01,650 assets and ~30,000 daily entries, with staff reporting the process as cumbersome and error-prone [R1][R24].
- **P4 — Rule-based alerts.** Fixed OEM thresholds do not adapt to local ballast, climate, traffic or asset age [R1].
- **P5 — Correlated failures treated as isolated.** Lightning, shared supplies, cable routes and maintenance actions hit many sections together; each is logged as a separate fault [R2].
- **P6 — Dual detection can mask decay.** Where a track circuit and an axle counter co-exist, the signal can clear if *either* shows clear. CAG documented a DC track-circuit failure at **02:16:47 on 28.12.2016** at Rura that was not investigated, followed by the Sealdah–Ajmer Express derailment at 05:30 with over 50 injured; CAG concluded that acting on the track-circuit indication could have prevented it [R12]. New interlocking designs plan axle counters in parallel with DC track circuits, so the masking risk is structural [R3].
- **P8 — Black-box fear.** A score without a cause will not survive scrutiny by SSEs, CRS or auditors.
- **P9 — Climate stress.** Monsoon, flooding and lightning drive recurring seasonal precautions [R14][R2].
- **P10 — Maintenance-induced hazards.** The CRS inquiry into Balasore found wrong signalling after a circuit alteration and earlier unreported abnormal behaviour [R17].
- **P12 — No open benchmark.** No public Indian track-circuit time-series dataset was found [R40].

## 4.2 What already exists — the corrected picture

We deliberately do **not** claim "nothing exists". That claim is outdated and would not survive expert scrutiny.

| Existing element | What it does | Why it is not complete |
|---|---|---|
| Manual inspection + logger review | Mandatory, trusted, periodic — fortnightly to half-yearly [R73][R74] | Cannot see slow drift between visits |
| SMMS (CRIS) | Digital asset and failure register [R24] | Manual entry, wrong records defeat alerts; not an analytics engine [R2] |
| RDPMS at ~100+ stations | Real-time monitoring, OEM rules, reported prevented failures [R1][R23] | Rules differ by OEM, data model not yet common, datasets too small for AI/ML [R1] |
| Kavach / interlocking / ABS | Prevent collisions and human error | Consume healthy inputs; do not predict decay [R19] |
| ITMS / WILD / OMRS / MVIS | Track geometry, wheel/bearing, visual inspection [R4] | Do not monitor signalling track-circuit electronics |
| Global platforms (Siemens Railigent X, Alstom HealthHub, Thales TIRIS, Wabtec RCM) | Mature, proven abroad [R45][R46][R47][R71][R72] | Vendor-tied, commercial, not built around Indian multi-OEM RDPMS/SMMS/CCSP reality |
| Per-circuit deep learning papers | 99.31% anomaly accuracy on one circuit technology [R26]; 99.7% in a generative-model LSTM study [R28]; 99.36% on Chinese-type jointless circuits [R29] | Classification on specific circuits; no network view, no RUL, proprietary or non-Indian data |
| Delay-prediction GNNs | Model train-delay propagation, including an Indian-network model [R35]–[R38] | Wrong target variable — delay, not asset health |

**one-sentence summary:** *each piece exists somewhere; nobody has combined physics, live sensing, graph risk, survival prognosis, calibrated uncertainty, explainability and Indian operational integration into one vendor-neutral, advisory-only layer* [§7 of the dossier].

## 4.3 The solution — six layers

| Layer | What it does |
|---|---|
| **L1 — Non-intrusive observation** | Read-only, galvanically isolated, high-impedance taps and existing logger/RDPMS feeds. One-way flow L0 → L1; the vital chain is never modified. |
| **L2 — Connectivity & adapters** | MQTT/OPC-UA/Modbus/CSV adapters, canonical event schema, CCSP-compatible interface, signed messages, store-and-forward. |
| **L3 — Data platform** | Kafka topics per zone, Schema Registry, stream QC and feature extraction, hot time-series store, cold Parquet store, feature and graph stores. |
| **L4 — Intelligence** | Per-circuit physics twin (transmission line + Unscented Kalman Filter) → context-aware baseline → anomaly ensemble → fault classifier → **heterogeneous common-cause graph** → **Bayesian survival RUL** → conformal calibration → three-part explainer → dual-detection consistency monitor. |
| **L5 — Decision & human-in-the-loop** | Rank by risk × consequence; fit work into Rolling Block windows (planned up to 52 weeks ahead [R68]); pre-fill SMMS entries; technician confirms or overrides with one tap; feedback becomes a label. |
| **L6 — Interfaces** | Offline-first field PWA, control-room dashboard, zonal/CRIS analytics, APIs for the unified RDPMS platform. |

## 4.4 How it works — end to end

1. **Watch** feed/relay voltage and current, pick-up/drop timings, ripple, supply quality, temperature, humidity, rainfall and surge counts.
2. **Understand physically:** the twin treats the circuit as a lossy transmission line with series rail resistance `r` and ballast conductance `g`, and online-estimates an *effective* ballast conductance plus rail/joint/supply states from ordinary measurements [R43][R44][R51].
3. **Detect drift** relative to that circuit's own baseline, conditioned on weather and traffic — a monsoon-wet circuit is not flagged merely for being wet.
4. **Connect the dots** using a heterogeneous graph with four edge types: weather-cell, shared-asset, interlocking/route, and work-history. Failures do **not** electrically propagate for kilometres; they cluster because of common causes and shared infrastructure — our model represents that correctly [§3.5].
5. **Predict** time-to-failure with a Bayesian Weibull/Cox survival model with shared frailty for station, supply and climate zone, plus distribution-free conformal intervals [R32][R33][R34][R26].
6. **Explain** with three parts: (a) physics change — *"effective ballast conductance rose 38% in 12 days; margin fell from 82% to 66% of dry baseline"*; (b) SHAP feature attribution; (c) the three most similar past SMMS cases with confirmed causes and fixes.
7. **Dispatch** a ranked, block-aware worklist with pre-filled paperwork; the human approves.
8. **Learn** from one-tap technician feedback and from maintenance treated as interventions during Rolling Block work.

## 4.5 Evidence generated so far — and its honest limits

- **Transmission-line illustration [Assumption/Design choice]:** with a 0.75 km DC circuit, relay current stays at 96.7% of dry value at 50 ohm-km ballast but falls to 53.9% at 2 ohm-km and 28.8% at 0.7 ohm-km. The circuit looks "healthy" across most of that range while the margin vanishes; a binary threshold sees nothing until the end, a trend estimator sees the slope.
- **Reproducible synthetic experiment (dossier §5.3, Appendix C):** a seeded 60-day run where ballast falls from 8.0 to 1.5 ohm-km raised a trend/Watch alarm on **day 26**; the relay dropped on **day 59** — a **33-day lead in this scenario**. An exponential fast-onset variant gave a 40-day lead. The twin's inverse ballast estimate stayed within **10.4%** of truth at the checkpoints.
- **Critical caveat:** *this is a proof of mechanism, not a field result.* Lead time is a property of the scenario and thresholds, not a predicted operational number. We never quote 33 or 40 days as an expected field lead time, and we never quote published 99% accuracies as our own.

## 4.6 Safety, standards and ethics

- **Strictly advisory and non-vital.** No output changes any signal aspect, route or interlocking state. No SIL-rated function is claimed.
- Sensors are read-only, isolated and fail-open; data flows one way from the field.
- Alignment targets: RDSO/SPN/257/2025 v2.0 (RDPMS) [R69], CCSP for edge/IoT [R1], CRIS-hosted data sovereignty, and good practice from EN 50126/50128/50129 [R41].
- **Assets, not people:** alerts are about equipment health. The system must never be used to rank or discipline staff — essential for workforce acceptance given existing entry workload [R24].
- Every recommendation can be overridden with a reason; model cards, calibration plots and audit logs are available to reviewers.

---

# 5) Tech Stack Used

> **Copy-ready:** The current proof-of-concept is deliberately software-simulation-first: a reproducible Python transmission-line simulator and seeded synthetic fault generator, a static HTML/CSS/JS prototype of the seven product screens, and a fully specified production architecture. IoT, sensors and edge hardware are planned as the **next optimisation** after the POC — read-only isolated voltage/current taps, environmental and surge sensors, an ARM edge gateway, MQTT/OPC-UA adapters and a CCSP-compliant interface — so that the vital signalling chain is never touched during the prototype stage.

## 5.1 Current POC — what actually exists and is demonstrated

| Layer | Current implementation | Purpose |
|---|---|---|
| Physics / digital twin | **Python, NumPy, SciPy** — lossy transmission-line solve of a DC track circuit | Recover hidden ballast conductance from observable relay current; generate fault data |
| Seeded experiment | Reproducible synthetic monsoon-drift script, 60 days, fault injectors F1–F7/F12 (dossier §5.3 & Appendix C) | Prove early detection mechanism with a fixed random seed; generate labels |
| Measurements / baselines | CUSUM/EWMA trend detection, 7-day slope + level rule | Compare physics-aware detection with a plain threshold |
| Benchmark plan | **NIDAN-Bench** — domain-randomised synthetic streams with ground-truth hidden states and topology | Bootstrap models where no public Indian dataset exists [R40] |
| UI prototype | **Static HTML + CSS + JavaScript**, self-hosted fonts, offline, no build step — seven screens in `design/mockups/pages/` | Show the product argument: overview, circuit detail, alert queue, field tablet, model health, design system |
| Brand assets | Outlined SVG + PNG kit, bilingual NIDAN/निदान lockup | Consistent, professional presentation |
| Documentation | `docs/Research/Debdatta-Complete-Research.md` v1.1 and `Frontend-Complete-Research-Implementation.md` | Every claim carries a source tag and a verified link |

## 5.2 Production platform — specified, not yet built

| Layer | Planned stack | Why |
|---|---|---|
| UI runtime | **React 19 + TypeScript 5.7**, **Vite 6**, Tailwind CSS v4, Radix/shadcn, TanStack Query/Table, Zustand, i18next | Largest hiring pool for CRIS/OEM teams; static bundle fits an air-gapped deployment; offline-first PWA via Workbox + IndexedDB [§14 of the front-end spec] |
| Visualisation | MapLibre GL JS + deck.gl, hand-authored SVG with d3-scale, Plotly/ECharts for confidence bands | Thousands of nodes; explainable charts instead of opaque chart widgets |
| Edge runtime | Linux + k3s/Docker, ONNX Runtime or TFLite with INT8 quantisation | Same model artefact as cloud; works through backhaul loss |
| Messaging | **MQTT** (TLS, per-device certificates), **OPC-UA / Modbus / CSV** adapters, **CCSP/oneM2M** interface | Vendor-neutral ingestion; Railway Board directs CCSP compliance for new RDPMS edge devices [R1][R20][R56] |
| Streaming | **Apache Kafka** + Schema Registry (Avro/Protobuf), **Flink** or Kafka Streams | Replayable, partitioned, ~20k msg/s sizing is well within capacity (dossier §13.4) |
| Storage | TimescaleDB/ClickHouse (hot), Parquet on MinIO (cold), PostgreSQL + PostGIS, Feast feature store, Redis | SQL analytics, cheap retention, spatial topology, consistent train/serve features |
| Physics & twin | Python NumPy/SciPy solver, **Unscented Kalman Filter**, OSRD / SUMO-rail / OpenTrack for traffic context | Transparent, unit-testable; "digital twin" = live graph + per-circuit state, not a 3D CAD model |
| AI/ML | **PyTorch**, **PyTorch Geometric + Temporal**, TCN/LSTM autoencoders, **lifelines / PyMC / NumPyro** for Bayesian survival, LightGBM, **SHAP**, MAPIE/split-conformal | Graph risk, censored RUL, uncertainty and explanations, with ablations against no-graph and Hawkes baselines |
| Backend | Python FastAPI + gRPC, Temporal/Airflow, Keycloak OIDC, Vault | Typed APIs for CRIS/SMMS integration; role-based access by zone |
| DevOps / security | Docker/Kubernetes, GitHub Actions, Prometheus/Grafana/OpenTelemetry, mTLS, signed payloads, segmentation, no write path | Auditability, drift monitoring, critical-infrastructure security |

## 5.3 Future optimisation — IoT / hardware / sensors (explicitly after the POC)

These are **planned**, not claimed as delivered. They make the field system stronger without changing the vital chain.

| Component | Planned technology | Why it is the right future optimisation |
|---|---|---|
| Sensing front-end | **Galvanically isolated, high-impedance voltage taps; Hall-effect / Rogowski non-intrusive current clamps; isolation amplifiers; simultaneous-sampling ADC** | Read-only and fail-open — a sensor failure cannot load or disturb the vital circuit; aligns with Indian Railways' own "non-intrusive sensors" direction [R25] |
| Environment sensing | Temperature/humidity probes, rainfall gauge or public weather feed, lightning/surge counter | Separates weather-explained drift from asset faults — monsoon and lightning are documented drivers [R2][R14] |
| Edge gateway | Industrial ARM-based gateway/SBC, wide temperature range, watchdog, secure element, GPS-disciplined NTP/PTP | Local feature extraction, buffering and detection when backhaul is lost; timestamp accuracy is required for cross-station correlation |
| Backhaul | 4G/5G, optical fibre where available, store-and-forward | Matches Indian rollout conditions; OFC is being laid for Kavach [R19] |
| Lab hardware-in-the-loop | Resistor-ladder "ballast box", real relay, programmable DC source, fault-injection switches | Gives experts a *physical* demonstration and labelled data before any field deployment — the credible bridge from simulation to pilot |
| Compliance | CCSP-compatible gateway, RDSO calibration procedure and pre-commissioning checklist alignment [R1][R69] | Required for any real RDPMS-edge deployment in Indian Railways |

**Why this ordering is deliberate:** presenting the POC as simulation-first is honest, fast to reproduce and safe; adding isolated hardware later shows a credible, standards-aligned path to the field without overstating what has been validated.

---

# 6) What Makes Your Project Unique and Innovative

> **Copy-ready:** NIDAN's novelty is the *combination*, not one algorithm. It is the first vendor-neutral layer that joins a physics-informed digital twin of each track circuit, a four-edge common-cause graph, a dual-detection masking monitor, Bayesian time-to-failure with conformal uncertainty, three-part explanations, and automatic SMMS paperwork — designed from the start for India's multi-OEM RDPMS, imperfect SMMS data, monsoon exposure and Rolling Block maintenance windows.

| ID | Innovation | What is new and why it matters |
|---|---|---|
| **N1** | Physics-informed twin with online parameter estimation | Transmission-line model + filtering estimates hidden ballast conductance/rail and joint health from ordinary signals; ML models only the residual. Interpretable and data-efficient where labels are scarce [R43][R44]. |
| **N2** | Heterogeneous common-cause graph | Four edge types — weather-cell, shared-asset, interlocking/route, work-history — model *correlated and cascading risk* correctly, instead of the physically wrong "failure spreads for kilometres" story [R2][R35]–[R39]. |
| **N3** | Masked-failure monitor for dual detection | Cross-checks track circuit vs axle counter vs interlocking events to surface a degrading-but-hidden circuit — directly addresses the CAG finding at Rura [R12] and new parallel-detection designs [R3]. |
| **N4** | Bayesian survival + conformal prediction | Days-to-failure with shared frailty for station/supply/climate and distribution-free coverage guarantees; handles censoring properly [R32][R33][R34][R26]. |
| **N5** | Data-trust layer + SMMS auto-fill | Scores asset-record trust and pre-fills failure/maintenance entries, tackling documented wrong data and staff workload [R2][R24]. |
| **N6** | Vendor-neutral canonical model + adapters | One schema with adapters for OEM RDPMS, data loggers, EI logs and CSV — exactly what Railway Board asked CRIS/RDSO to enable [R1]. |
| **N7** | Three-part explanation | Physics change + SHAP attribution + similar past cases; an auditor can follow the reasoning [§11.2 Step J]. |
| **N8** | Maintenance as intervention | Rolling Block work becomes a natural experiment, generating labels and measuring intervention effect [R68]. |
| **N9** | Sim-to-real pipeline + open benchmark | Domain-randomised synthetic faults pre-train models; NIDAN-Bench addresses the absence of an open Indian dataset [R40]. |
| **N10** | Configuration-drift and reset-pattern alerts | Flags repeated resets and unexplained behaviour after alterations — an advisory step toward Balasore-type latent hazards without touching vital logic [R17]. |

**Positioning against closest prior work:** rule-based RDPMS has live data but no physics, graph, RUL or uncertainty; per-circuit deep learning has high accuracy on specific circuits but no network or prognosis; delay GNNs model the wrong target; survival studies are not connected to live streams or explainable dispatch. The capability matrix is in dossier §10.2.

---

# 7) Target Audience / Users

> **Copy-ready:** Primary users are Indian Railways S&T maintainers — SSE/JE/ESM — and Station Masters/controllers who need an early, explained reason to act. Institutional users are divisions and zonal railways, RDSO, CRIS and Railway Board; delivery partners are RDPMS OEMs and project agencies such as RVNL/IRCON/RailTel. Metros and DFCCIL are adjacent adopters. Passengers and freight users are the ultimate beneficiaries.

| User group | Current pain | What NIDAN gives them |
|---|---|---|
| **S&T maintainers (SSE / JE / ESM)** | Reactive firefighting, manual and error-prone SMMS entry, backlogs [R24] | Ranked worklist, reason for each alert, pre-filled entry, fewer unnecessary track walks |
| **Station Masters / controllers** | Unexplained "occupied" faults and fallback procedures | Advance warning and a clearer cause; documented evidence trail [R12] |
| **Divisions / zonal railways** | Failures despite granted maintenance blocks; wide MTBF/MTTR variation [R10][R13] | Risk-based block planning, cross-division benchmarking |
| **Railway Board / RDSO / CRIS** | Fragmented RDPMS; need common data, unified dashboard and sensor calibration [R1] | Reference analytics layer, canonical data model, open benchmark, integration path |
| **RDPMS OEMs and startups** | Need bigger datasets and better models [R1] | Analytics module they can embed; vendor-neutral adapters; shared standard |
| **Project agencies (RVNL, IRCON, RailTel)** | Deliver signalling/RDPMS works [R22] | Add-on predictive analytics for delivered projects |
| **Metros / DFCCIL / state rail** | Centralised signalling monitoring exists but without physics-based prognosis [R75][R76] | Technology transfer; Delhi Metro already runs remote health monitoring on the Magenta Line |
| **Safety regulators (CRS)** | Investigations find latent maintenance lapses [R17] | Drift, reset and alteration evidence trails |
| **Passengers / freight users** | Delays; punctuality index fell from 94.17 (2020) to 73.62 (2023) [R15a] | Fewer unexplained stops; better-planned maintenance [R77] |

**Explicit non-users:** the system is **assets-not-people** — it must never be used to rank, score or discipline staff.

---

# 8) Real-World Application or Impact

> **Copy-ready:** NIDAN applies to the 6,665 Indian stations with complete track circuiting, especially station yards and point zones where ballast moisture, insulated joints, relay ageing, supply faults and lightning dominate failures. It turns a failure-driven routine into a predicted, explained and block-scheduled one: earlier detection, common-cause clusters instead of repeated isolated investigations, and near-zero extra paperwork through SMMS pre-fill. The greatest benefit is in monsoon-, flood- and lightning-exposed divisions. All impact numbers are expressed as a defensible formula and pilot acceptance targets — not as claimed field results.

## 8.1 Where it applies

- **Station yards and point zones** — track circuiting is complete at 6,665 stations, while block sections increasingly use axle counters; new EI designs specify both in parallel [R5][R3].
- **DC, AC and audio-frequency jointless circuits**, with type-specific twins; axle-counter health events can be ingested later [R54].
- **Monsoon/cyclone/lightning-prone zones** — Railway Board issues annual ballast-clearance, liner and IPS-backup precautions every year [R14][R2].
- **Adjacent operators** — metros and freight corridors using relay or DC/AC/AF circuits; Delhi Metro already demonstrates centralised signalling health monitoring [R75][R76].

## 8.2 How it changes work — before vs after

| Dimension | Before | With NIDAN |
|---|---|---|
| Detection | After relay drop / train stop; periodic inspection | Drift flagged days ahead for fault types that drift *(target, to be proven in pilot)* |
| Data | OEM silos, manual SMMS entries | Canonical stream, adapters, data-trust scores |
| Intelligence | Fixed OEM thresholds | Physics residual + ML + graph + survival |
| Correlation | Each failure investigated separately | Common-cause clusters shown with evidence |
| Prognosis | Binary alarms | Time-to-failure with uncertainty band |
| Dual detection | Masked decay possible | Cross-modal monitor surfaces the hidden circuit |
| Paperwork | Manual SMMS typing | Pre-filled entry, one-tap confirmation |
| Maintenance planning | Calendar-based | Risk-ranked, fitted to Rolling Block windows [R68] |
| Climate | Annual circulars for everyone | Location-conditioned, season-aware baselines |

## 8.3 Defensible impact formula [Assumption-based, to be replaced by pilot data]

```
Annual failures avoided   = N_circuits_monitored × f_TC_failure_rate × P(pre-empted)
Delay-minutes saved       = Failures avoided × mean_delay_per_failure × trains_affected
Maintenance hours saved   = False-alarm walks avoided + faster MTTR − extra investigation
Paperwork time saved      = Records pre-filled × (manual time − confirm time)
```

**Scale context, not a claim:** CAG recorded ~2,961 signal failures per year in one zone over five years [R10][R11]; nationally, 13 consequential events were attributed to signalling failure over five years [R18]. The pyramid is steep — many precursor failures, rare accidents — which is exactly why prediction at the base matters.

**Proposed pilot acceptance targets [Design choices, to be agreed with partners:** median lead ≥72 h for drift-type Warning alerts; Precision@10 ≥0.5 on the daily worklist; ≤1 false Watch alert per station-month; calibration error ≤0.05; 80% RUL interval coverage 75–85%; ≥70% technician acceptance; 50% reduction in SMMS entry time (dossier §16.4).

## 8.4 Social and safety dimension

- Fewer unnecessary on-track visits reduce exposure; the ministry reports a 66% fall in track-maintenance staff deaths since 2013-14, and further exposure reduction is aligned with that effort [R5] **[our inference]**.
- Configuration-drift and reset alerts make latent hazards visible earlier; Balasore showed why this matters [R17].
- No claim of replacing the technician, the interlocking or Kavach — NIDAN supports them with better information.

---

# 9) Future Development Plan

> **Copy-ready:** A staged, evidence-gated plan: (0) align claims and secure a data contact; (1) physics twin and synthetic benchmark; (2) Kafka-based data platform and dashboard MVP; (3) graph, survival, calibration and explanation stack; (4) lab bench with hardware-in-the-loop; (5) showcase release at week 16; (6) 5–10 month shadow-mode pilot at 2–3 stations with no operational effect; (7) 10–18 month CRIS/RDSO integration and Rail Tech co-funded trial; (8) 18–36 month multi-zone scale-out to axle counters, points and power.

| Phase | Timing | Goal | Exit criterion |
|---|---|---|---|
| **0 — Alignment & verification** | Weeks 0–2 | Confirm claims with 2–3 SSEs and one RDSO/CRIS contact; prepare one-pager and data request | Domain assumptions confirmed; named data contact |
| **1 — Twin & benchmark** | Weeks 2–6 | Transmission-line simulator, fault injectors F1–F7/F12, trend baselines, unit tests | Injected drift detected with measurable lead on synthetic data |
| **2 — Data platform MVP** | Weeks 4–10 | MQTT → Kafka → TSDB, stream QC, 30–50 circuit replay dashboard | Live replay demonstration |
| **3 — Intelligence stack** | Weeks 8–16 | GNN risk with ablations, Bayesian survival with frailty, conformal layer, SHAP + physics explanations, SMMS pre-fill | Beats baselines on the synthetic benchmark; calibration targets met |
| **4 — Lab bench / HIL** | Weeks 6–16 | Ballast emulator, relay, isolated sensors, gateway, fault injection | Bench data reproduces twin behaviour |
| **5 — Showcase MVP** | Week 16 | 7-minute expert walkthrough, technical note, open NIDAN-Bench v0.1 | Expert Q&A rehearsed |
| **6 — Shadow-mode pilot** | Months 5–10 | 2–3 stations in one division; read-only feeds; weekly SSE review; no alerts affecting operations | Pre-registered pilot metrics assessed [§16.4] |
| **7 — Integration & standards** | Months 10–18 | RDPMS OEM adapters, CCSP-compatible interface, SMMS connector, RDSO review, Rail Tech co-funded trial [R4][R57] | Data model accepted; trial agreement signed |
| **8 — Scale-out** | Months 18–36 | Multi-zone deployment; extend to axle counters, points, power supplies | Uptime, adoption and KPI dashboards |

**Funding and adoption route:** submit via the **Rail Tech Policy** portal (adopted 26.02.2026), which provides **50:50 cost-sharing for prototype development and trials** and grants for extended trials/scale-up [R4][R57]; propose NIDAN as the analytics module for the planned **CRIS unified RDPMS dashboard** [R1]; request RDSO review of the canonical data model and calibration approach [R69]; partner with CCSP-registered RDPMS vendors [R20].

**Key risks and mitigations:** data access → early MoU + bench; rare failures/label scarcity → synthetic pre-training, self-supervision, active learning; alarm fatigue → persistence rules, alert budget, conformal abstention, shadow tuning; sensor permissions → existing logger feeds first, OEM partnership; certification friction → non-vital design, trial route [§19].

---

# 10) Additional Requirements and Notes

## 10.1 What we need to move from POC to pilot

| Requirement | Detail |
|---|---|
| **Data access (MoU/NDA)** | 12+ months of track-circuit electrical logs including a monsoon; occupancy/EI and axle-counter events; 3+ years of SMMS failure records with cause codes; station layouts, circuit types/lengths, cable and power maps; weather/lightning records; sensor calibration records [§15.3] |
| **Domain review** | 2–3 SSE/Sig officers and one RDSO/CRIS contact to confirm assumptions and the canonical data model |
| **Trial route** | Rail Tech Policy 50:50 co-funding for prototype and trial [R4][R57] |
| **Bench support** | Space and instrumentation for the resistor-ladder ballast emulator and relay hardware-in-the-loop rig |
| **Partners** | One willing zone/division and one CCSP-registered RDPMS OEM for adapter development |

## 10.2 Notes for the experts — what we are and are not claiming

- **We are simulation- and bench-stage.** Synthetic lead times are properties of the scenario, not field results. Published 99% accuracies belong to other systems on other circuits and are not our claims.
- **We are advisory and non-vital.** No write path to interlocking, signals, routes or track circuits; sensors, when added, are isolated and read-only; this is the central safety argument.
- **We are not competing with RDPMS or OEMs.** Railway Board has already defined the gap — fragmented rules, no common data model, small datasets, no unified analytics [R1] — and we supply that missing layer.
- **We do not overstate the market.** A bottom-up India-only estimate is **₹127–313 Cr capex + ₹20–53 Cr/yr opex**, about **₹227–580 Cr over five years** [Estimate, dossier §22.5]. We do not quote the unsupported ₹2,000 Cr headline.
- **We are assets-not-people.** No staff ranking or discipline; every recommendation is human-overridable.
- **We use only verified sources.** The unverified paper titles in the original problem sheet were removed; the corrected claims audit is dossier §2.3.
- **Governance:** data stays on Indian Railways-approved infrastructure, role-based access, minimal personal data, audit logs, and any public benchmark contains only synthetic or fully anonymised data [§15.6].

## 10.3 Suggested 7-minute demonstration flow

1. **(1 min)** The monsoon story — show the seeded 60-day drift chart from §5.3.
2. **(1 min)** Why now — Railway Board's own RDPMS minutes list the exact gaps [R1].
3. **(2 min)** Physics: lower ballast resistance on the emulator / simulator; watch the twin estimate conductance rise and an alert fire ahead of drop-away.
4. **(1 min)** Graph + explanation: three circuits sharing a drain cluster into one root cause; show physics + SHAP + precedent.
5. **(1 min)** Worklist: Rolling Block-aware plan and pre-filled SMMS entry with one-tap confirmation.
6. **(1 min)** The ask: one zone's data for a shadow pilot, RDSO review, Rail Tech co-funding.

## 10.4 Key references (full list with links in dossier §24)

| Tag | Source |
|---|---|
| [R1] | [Railway Board minutes, 31.01.2025 meeting on RDPMS implementation](https://ecr.indianrailways.gov.in/cris//uploads/files/1744352589344-RB%20Minutes%20of%20Meeting%20held%20on%2031.01.25%20regarding%20RDPMS%20implementation..pdf) |
| [R5] | [ Rajya Sabha reply reported by ANI: 6,660 EI stations, 6,665 fully track-circuited stations](https://www.newkerala.com/news/a/indian-railways-safety-measures-yield-results-58-drop-312.htm) |
| [R12] | [CAG Report No. 45 of 2018 — dual detection and the Rura case](https://cag.gov.in/webroot/uploads/download_audit_report/2017/Report_No.45_of_2018_%E2%80%93_Compliance_Audit_on_Maintenance_of_track_on_heavy_traffic_sections_over_India.pdf) |
| [R14] | [Railway Board Summer & Monsoon Precautions for signalling, 11.03.2024](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2024/Summer%20%26%20Monsoon%20110324.pdf) |
| [R17] | [CRS inquiry into the Balasore accident — multi-level signalling lapses](https://theprint.in/india/odisha-train-accident-inquiry-finds-multi-level-lapses-says-reporting-past-red-flags-could-have-averted-tragedy/1653092) |
| [R24] | [SMMS at Western Railway: 3,01,650 assets, ~30,000 daily entries](https://www.devdiscourse.com/article/business/3546255-streamlining-signals-western-railways-digital-leap) |
| [R40] | [Systematic review of open railway AI datasets](https://dx.doi.org/10.3390/infrastructures6100136) |
| [R69] | [RDSO/SPN/257/2025 v2.0 — RDPMS specification listing](https://rdso.indianrailways.gov.in/) |
| [R68] | [Rolling Block Programme — 52-week planning, IR Open Lines General Rules rule 15.02(c)](https://gazettetracker.com/g/CG-DL-E-30112023-250327) |
| [R4]/[R57] | [Rail Tech Policy and PIB release on AI/ML devices](https://pib.gov.in/PressReleasePage.aspx?PRID=2238772) |

---

**Document status:** ready for form submission. All claims trace to the project's research dossier v1.1; assumptions, estimates and design choices are labelled as such, and no simulated result is presented as field-validated performance.
