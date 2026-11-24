# NIDAN | निदान — Predictive Failure Propagation Engine for Indian Railway Track Circuits
## Complete Research Dossier: Problem, Landscape, Gaps, Solution, Architecture, Plan

**Tagline:** *Find the cause before the failure. Predict. Explain. Prevent.*

**Prepared for:** Debdatta and team (industry-expert showcase)
**Document status:** Research draft v1.1, 22 November 2026. v1.1 renames the project to **NIDAN**, re-verifies every figure that v1.0 flagged as open, and replaces the non-reproducible drift run with a seeded script (§5.3, Appendix C). The change log is §24.4.
**Scope:** Problem Statement 01 (Railways · Signalling · Safety-Critical Systems)
**Evidence policy:** every factual claim carries a reference tag like `[R12]` that resolves to a link in Section 24, and Section 24.1 explains the status codes (**O** = opened and read, **L** = located and title-matched, **T** = tentative). Anything that is *our own assumption, estimate, or engineering judgement* is explicitly labelled **[Assumption]**, **[Estimate]** or **[Design choice]**. Claims that could not be verified were either removed in v1.1 or moved to the short open list in §24.4.2.

---

## How to use this document (and one important warning)

This dossier is written so you can defend every slide in front of Indian Railways S&T officers, RDSO engineers, CRIS people and OEM engineers. Those audiences will check your claims. During research I found that **several statements in the original problem sheet are either outdated, overstated, or not verifiable** (Section 2.3). If you present them as written, an expert can puncture your credibility in one question. The good news: the *real* picture is stronger for you. The Railway Board itself wrote down, in 2025, the exact gaps your project fills (Section 6.1). So the dossier **re-frames** the pitch from "nothing exists" (false and risky) to "a national RDPMS programme exists, but it is fragmented, rule-based and data-starved, and we provide the missing analytics, physics, graph and explainability layer" (true, documented, and much more credible).

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Understanding the Problem Statement Deeply](#2-understanding-the-problem-statement-deeply)
3. [Domain Primer: How Track Circuits Work and Fail](#3-domain-primer-how-track-circuits-work-and-fail)
4. [The Identified Problems](#4-the-identified-problems)
5. [Real-World Evidence](#5-real-world-evidence)
6. [What Already Exists (India and World)](#6-what-already-exists-india-and-world)
7. [Why Existing Solutions Are Not Complete](#7-why-existing-solutions-are-not-complete)
8. [Gap Analysis: What Must Be Filled](#8-gap-analysis-what-must-be-filled)
9. [Our Proposed Solution: Concept and Positioning](#9-our-proposed-solution-concept-and-positioning)
10. [Novelty and Innovations](#10-novelty-and-innovations)
11. [Methodology (Technical and Logical Detail)](#11-methodology-technical-and-logical-detail)
12. [Before vs After](#12-before-vs-after)
13. [Proposed System Architecture](#13-proposed-system-architecture)
14. [Technology Stack: Domain-wise, With Justification](#14-technology-stack-domain-wise-with-justification)
15. [Datasets and Data Strategy](#15-datasets-and-data-strategy)
16. [Model Design, Evaluation and Validation](#16-model-design-evaluation-and-validation)
17. [Safety, Standards, Cybersecurity and Compliance](#17-safety-standards-cybersecurity-and-compliance)
18. [Feasibility and Viability](#18-feasibility-and-viability)
19. [Challenges and Mitigations](#19-challenges-and-mitigations)
20. [Impact and Benefits (Who Gains, Where)](#20-impact-and-benefits-who-gains-where)
21. [Implementation Plan](#21-implementation-plan)
22. [Assumptions, Cost Estimation and Market Sizing](#22-assumptions-cost-estimation-and-market-sizing)
23. [Expert Q&A Preparation and Showcase Strategy](#23-expert-qa-preparation-and-showcase-strategy)
24. [References (with Links)](#24-references-with-links)
25. [Appendices](#25-appendices)

---

# 1. Executive Summary

**The problem in one paragraph.** Indian Railways relies on *track circuits* (and axle counters) to know whether a section of track is occupied. A track circuit is a safety-critical electrical circuit that uses the two rails as wires; when it fails it defaults to "occupied", which is *safe* but stops trains. Track-circuit health depends on slow, messy physical factors (ballast moisture and dirt, insulated joints, bonds, relay age, power supply quality, lightning surges, stray traction currents, workmanship). Today these are mostly detected **after** they cause a failure, or by periodic manual inspection. Failures cluster in time and space (monsoon, lightning, shared power or cable faults), so they are *correlated*, but the data that could reveal the correlation sits in separate silos.

**What exists (corrected picture).** Indian Railways already runs a national drive for **RDPMS** (Remote Diagnostic and Predictive/Preventive Maintenance System) for signalling. As of a Railway Board meeting on 31 January 2025, about 100+ individual stations had RDPMS working, each using *different business rules defined by different OEMs*, and zones said they needed bigger datasets before AI/ML could be exploited [R1]. Railway Board has asked RDSO for standard business rules, standardised data structures, CCSP-compliant edge devices, and asked CRIS for a unified application and dashboard [R1]. A **Signal Maintenance Management System (SMMS)** run by CRIS is the digital asset and failure register, but Railway Board itself had to warn zones about wrong data entry (for example a more-than-16-year-old track relay recorded with wrong data) [R2][R24].

**What is missing (our opportunity).** (1) A *vendor-neutral analytics layer* on top of heterogeneous RDPMS/data-logger feeds; (2) *physics-informed* models (a track circuit is a transmission line, so we can estimate hidden parameters such as ballast conductance instead of only thresholding raw voltage); (3) a *network-aware* layer that models correlated and cascading risk across circuits, shared power, cables and interlocking; (4) *time-to-failure* (survival) estimates with calibrated uncertainty instead of binary alarms; (5) *explainable, human-in-the-loop* work-order generation that reduces (not adds to) the maintainer's paperwork burden; (6) a safe, *non-vital*, standards-aware deployment path through RDSO/CRIS and the new Rail Tech Policy.

**Our solution — NIDAN (निदान, "diagnosis").** A *Predictive Failure Propagation Engine* with six layers: non-intrusive sensing and edge AI; secure streaming ingestion; a physics-informed digital twin per track circuit; a heterogeneous-graph model for correlated and cascading failure risk; Bayesian survival models for remaining useful life; and an explainable dispatch queue (SHAP + physics explanations) that feeds SMMS and a unified dashboard.

**Why it can win.** The novelty is not any single algorithm. It is the *combination* that no published system or public Indian programme currently provides: physics + graph + survival + conformal uncertainty + explainability + Indian operating realities (dual detection masking, SMMS data-quality, OEM fragmentation, monsoon/lightning exposure, Rolling Block maintenance windows).

**Honest scope note.** A 4-month MVP is realistic on a *simulated plus lab-bench* basis. Claims of field accuracy need real data from Indian Railways (Section 15, Section 21). Do not claim field validation until you have it.

---

# 2. Understanding the Problem Statement Deeply

## 2.1 The original statement, decoded

The problem sheet says (paraphrased, in our words):

| Element | What the sheet claims | What it really means technically |
|---|---|---|
| Title | Predictive Failure Propagation Engine for Track Circuits | Predict *which* track circuits will fail, *when*, and *how failures relate/cascade*, before trains are delayed |
| "Why nobody notices" | Failures are logged as isolated events; no system correlates multi-km cascading electrical failures from soil moisture, stray current, ballast degradation, axle load anomalies | Failure *records* are per-asset; cross-asset *correlation* (weather cells, shared power, cable routes, interlocking dependencies) is not analysed |
| Current workflow | Engineers walk tracks with handheld probes monthly; paper logbooks; no temporal correlation across 7,000+ stations | Periodic manual inspection to fixed schedules (fortnightly technician checks, monthly inspector checks, quarterly shunt tests, half-yearly joint S&T–P.Way inspection) [R73][R74]; entries now digital in SMMS [R24]; weak time-series continuity across 7,461 stations [R77] |
| Proposed system | Edge sensors → Kafka → GNN → Bayesian survival → human-in-loop dispatch with SHAP → digital twin | Sensing → streaming → graph model → RUL → explainable action → live twin |
| Users | Indian Railways, RDSO, RVNL | Operator, standards body, project agency |

## 2.2 The *actual* problems underneath (plain English)

1. **Slow hidden degradation.** Ballast gets wet, dirty and fouled. The circuit's safety margin shrinks quietly until one rainy afternoon the relay drops and trains stop. Nobody sees the shrinking margin in time.
2. **Failures that look random but are not.** Many failures happen together because of *shared causes* (a lightning strike, a flooded drain, a power-supply fault, a cut cable, a bad maintenance change), not because one failure "infects" its neighbour.
3. **Data exists but is fragmented.** Data loggers, RDPMS vendors, SMMS, and EI logs speak different formats and are owned by different systems [R1][R20].
4. **Alarms without explanation.** Maintainers will not trust a black-box score. They need to know *which signal changed and why it matters*.
5. **Safety certification fear.** Anything touching signalling must not degrade the vital chain. The system must be strictly advisory and non-intrusive.

## 2.3 Claims audit: what to correct before you present

This table is the most important one for your credibility. "Status" is my verdict from the research.

| # | Claim in the problem sheet | Status | Evidence and what to say instead |
|---|---|---|---|
| C1 | "The Indian Railway safety board has no predictive layer; everything is reactive." | **Overstated / outdated** | A Railway Board meeting on 31.01.2025 formalised a national RDPMS strategy; 100+ stations already run RDPMS with OEM-defined rules; zones reported preventing certain failures with it [R1]. RDSO now publishes a full RDPMS specification, **RDSO/SPN/257/2025 v2.0** (effective 31.12.2025) [R69]. Say instead: *"A predictive layer is emerging but is fragmented, rule-based and data-starved."* |
| C2 | "Track failure reports are written in paper logbooks." | **Outdated** | SMMS (CRIS) holds assets and failures digitally; Western Railway alone registered 3,01,650 assets with ~30,000 daily maintenance entries [R24]. The real issue is *data quality and manual entry burden*, not paper [R2][R24]. |
| C3 | "No temporal correlation across 7,000+ stations." | **Partly true; station count now verified** | RDPMS data are siloed per OEM, and Railway Board only planned (Feb 2025) to unify them at CRIS "at a later stage" [R1]. Station count is not a guess: Indian Railways operated **7,461 stations** as at 31 March 2024 [R77], of which **6,660 had electronic interlocking** and **6,665 complete track circuiting** at 31 Dec 2025 [R5]. Say *"about 7,400 stations, 6,660 interlocked"*, not "7,000+". |
| C4 | "Engineers walk tracks with handheld IR probes and multimeters every 30 days." | **Half right; the "IR probes" detail is not supported** | Inspection *is* periodic and prescribed: technician-level DC track-circuit checks are **fortnightly and monthly**, sectional JE monthly, SSE quarterly, and **joint S&T–P.Way inspection is half-yearly** with train-shunt tests **quarterly** and test-card readings every six months [R73]; Signal Inspectors must inspect and test equipment at intervals **not exceeding one month** [R74]. Drop "handheld IR probes"; say *"scheduled manual inspection, from fortnightly checks to half-yearly joint inspections"*. |
| C5 | "Multi-kilometre cascading electrical failures." | **Physically inaccurate as phrased** | Track circuits are electrically isolated sections (insulated joints or tuned jointless boundaries). Correlated failures arise from *common causes*, *shared infrastructure*, *interlocking dependencies* and *maintenance errors* (Section 3.4), not from current "propagating" km along rails. Reframe as **correlated and cascading failure risk**. |
| C6 | Cited papers: "Deep Learning-based Railway Track Fault Detection (IEEE Trans. 2022)", "Graph Neural Networks for Infrastructure Failure Prediction (KDD 2023)", "Predictive Maintenance with Bayesian Deep Learning (ICML 2022)" | **Could not verify** | My searches did not find papers with these titles/venues. **Do not cite them.** Use the verified references in Section 24 (for example [R26]–[R29], [R33], [R35]–[R39]). |
| C7 | "Competitors: Siemens Railigent, Wabtec: both require proprietary hardware not installed in India. No Indian system exists." | **Incorrect as stated** | Siemens has Indian signalling and rolling-stock presence and markets Railigent X [R45]; Alstom's HealthHub covers trains, signalling and infrastructure [R46]; Indian RDPMS vendors (Efftronics, Bitcom, Energy7, Gadgeon, JARS, Aquasense) are registered on C-DOT's CCSP for the RDSO-RDPMS vertical [R20], and Indian vendors are already delivering RDPMS under the published RDSO specification [R20][R21][R69]. Wabtec is **not** absent from condition monitoring: it sells relay condition monitoring (Mors Smitt) [R71] and its crossings literature names "track circuit degradation" as a pain point it monitors [R72] — but neither is a physics-informed, graph-aware, RUL-producing analytics layer for Indian DC/AC/AF track circuits. Say instead: *"No vendor-neutral, physics-informed, network-aware analytics layer exists across these silos."* |
| C8 | "MVP feasible in 4 months with OpenMTS + simulated track graph." | **Feasible; the named simulator does not exist under that name** | No railway simulator called "OpenMTS" could be identified, so the name is dropped. Use **OSRD**, SUMO-rail, OpenTrack or a custom graph (Section 14.5) [R49]. A 4-month MVP is realistic *on simulated and lab-bench data only*. |
| C9 | Commercial "₹2000Cr+" | **Not reproducible from public numbers** | A bottom-up India-only estimate is far smaller unless scope broadens: **₹127–313 Cr capex + ₹20–53 Cr/yr opex** across all 6,665 circuited stations, about **₹227–580 Cr over five years** (Section 22.5). Present that range, never the headline. |
| C10 | Scores (Originality 9.8/10, Social Impact 10/10, etc.) | **Self-assigned** | Fine for internal ranking; do not present as measured facts. |

> **Takeaway for the pitch:** replace *"nothing exists"* with *"the Railway Board has named the exact gap; we deliver it"*. That is both truer and more persuasive.

---
# 3. Domain Primer: How Track Circuits Work and Fail

## 3.1 What a track circuit is (with an analogy)

A **track circuit** feeds a small electrical signal into the two running rails at one end of a track section. A **track relay** at the other end stays energised while the rails carry the current. When a train enters, its wheels and axles form a low-resistance shunt across the rails, the relay current collapses, the relay de-energises, and the system reads the section as *occupied*. [R52]

> **Analogy: the fence doorbell.** Imagine a doorbell wired along two parallel fence wires, with the bell-ringer at the far end. As long as current flows, the bell stays quiet. If someone drapes a metal chain across both wires (the train), the current takes the shortcut and the bell rings. If a wire breaks or the battery dies, the bell also rings. So the circuit is **fail-safe**: failures look like "occupied". The cost of this safety is availability: false "occupied" indications stop trains. [R52]

Track circuits come in several types: **DC**, **AC**, and **audio-frequency (AF)** jointless circuits; AF/AC types are used where stray traction currents would overwhelm tiny DC signals [R52]. On Indian Railways, **99.2% of the broad-gauge network (69,427 of 70,001 route-km) is electrified** as of November 2025 [R15b], so traction-return-current immunity (AC-immune relays, AF circuits) is a daily design concern; RDSO even specifies AC-immune biased track relays [R53].

## 3.2 Why ballast is the central physical variable

The ballast between and under the rails is not a perfect insulator. Some current leaks from one rail to the other through it. When ballast is dry, little leaks; when ballast is wet, fouled or muddy, much more leaks and less reaches the relay. Classic patents and modern literature describe exactly this wet/dry ballast swing and the need to discriminate *slow ballast change* from *fast train shunt* [R51][R30]. Swedish maintenance research lists low ballast resistance, insulated-joint failure, rail breaks, component faults and "no fault found" false alarms as the main DC track-circuit failure modes, and notes that wet or dirty ballast is a frequent cause [R30].

> **Analogy: the leaky garden hose.** Water (current) is pumped in at one end of a long hose. If the hose has many small holes (low ballast resistance), by the far end only a trickle arrives. In dry season the holes are few; in monsoon they multiply. The relay needs *enough* trickle to stay up. Today we mostly find out the hose leaks when the far-end tap goes dry.

Indian practice sets minimum ballast resistance: **not less than 2 ohm-km in station yards and 4 ohm-km in block sections**, with insulated liners available up to at least 97% where PSC sleepers are used [R50]. Railway Board's Summer & Monsoon Precautions for signalling (letter dated 11.03.2024) instruct joint SSE/P.Way–SSE/Sig inspection to clean ballast and keep **at least 50 mm clearance of ballast below the rail foot** to avoid leakage of track circuit currents, and to provide **100% insulated GFN liners and rubber pads** in track-circuited areas with PSC sleepers [R14]; the same 50 mm clearance is a standing permanent-way requirement in IRSEM [R50]. A real incident in the Railway Board minutes shows how small workmanship choices matter: iron liners at point-zone sleepers contributed to track section failures and were removed [R2].

## 3.3 Where track circuits sit in Indian Railways today

| Item | Current status (latest figure found) | Ref |
|---|---|---|
| Stations with electrical/electronic interlocking | 6,660 (as of 31 Dec 2025) | [R5] |
| Stations with complete track circuiting | 6,665 (up to 31 Dec 2025) | [R5] |
| Block sections with Block Proving Axle Counters (BPAC) | 6,142 (up to 31 Dec 2025) | [R5] |
| Automatic Block Signalling | 6,625 route-km (up to 31 Dec 2025) | [R5] |
| Level-crossing gates interlocked | 10,097 (up to 31 Dec 2025) | [R5] |
| Reported fall in signalling failures | about 58% over 11 years (ministry claim) | [R5] |
| New-station EI design basis | EI stations are estimated with **axle counters in parallel with DC track circuits** plus RDPMS, data logger RTU etc. | [R3] |

**What this tells us about scope.** Track circuits remain at the heart of *station yards* (complete track circuiting at 6,665 stations), while *block sections* increasingly use axle counters. New EI designs even specify *both* in parallel ("dual detection") [R3]. So our scope should be **station-yard and point-zone track circuits (DC and AF), plus a generalised pipeline that can ingest axle-counter health events later**. This also pre-empts the common expert question "aren't track circuits being replaced by axle counters?" (answer: not in yards; they co-exist).

### Growth of electronic/electrical interlocking (context for data readiness)

Verified points only:

| Date | Stations with EI/electrical interlocking | Source |
|---|---|---|
| 31 Dec 2025 | **6,660** | [R5] |
| 31 Mar 2024 | 7,461 stations in total on the network | [R77] |

Earlier-year EI counts circulated in Parliament replies (6,498 in Oct 2023, 6,589 in Jun 2024) could not be re-opened and re-read in this revision, so they are **not** quoted. The direction is not in doubt: EI coverage is close to saturation of the circuited-station base, so the *new* wave is **data and analytics**, not more interlocking. That is the gap NIDAN fills.

## 3.4 The failure taxonomy (what really goes wrong)

| # | Failure mode | Physical cause | Typical data signature | India-specific example or evidence |
|---|---|---|---|---|
| F1 | Low ballast resistance | Wet, fouled or muddy ballast; poor drainage; ballast touching rail | Slow decline of relay current/voltage over days to weeks; worse after rain | Monsoon precautions on ballast clearance [R14]; mechanism [R30][R51] |
| F2 | Insulated joint / glued joint failure | Joint breakdown, metal flash, contamination | Leakage to neighbour section; polarity anomalies; intermittent flicker | Insulated joint images are in public railway datasets (ProRail) [R40] |
| F3 | Rail bond / continuity failure, rail break | Corrosion, vibration, fracture | Sudden or stepwise change; rising impedance; open-circuit behaviour | CAG documented rail fractures and weld failures, and a 2016 derailment at Rura where a DC track-circuit failure preceded a probable rail fracture [R12] |
| F4 | Metallic bridging at points | Iron liners, bolts, debris at switch/point zone | Persistent partial shunting; repeatable at location | MoM case at a point zone with iron liners [R2] |
| F5 | Relay ageing | Old relays beyond codal life | Slower drop/pick timing; higher variance | A >16-year-old track relay failed at Chainwa (NER); SMMS data was wrong so "codal life overdue" alert did not help [R2] |
| F6 | Power supply and feed faults | High current in 110 V DC path opened relay contacts; IPS/battery issues | Voltage sag, ripple; correlated across circuits on same supply | MoM case where high current opened NWR/NWPR contacts [R2]; Monsoon IPS backup checks [R14] |
| F7 | Lightning and surge damage | Surges via cables | Multiple sections failing together; surge-count spikes | Multiple track section failures at a station during lightning on 23.03.25 [R2] |
| F8 | Cable faults and cuts | Excavation, rodents, water ingress | Intermittent open/short; correlated along cable route | CAG found OFC and signal cable cuts "continued unabated" [R10]; defective cable at Gonda [R2] |
| F9 | Shunting failure (wrong-side risk) | Rust/contamination on rail head, low wheel loads | Poor shunt signature; slow drop on occupancy | Contamination and low axle loads on lightly used lines [R31] |
| F10 | Stray/traction interference | Traction return current; harmonic noise | Noise floor rise; spurious drops | Broad gauge 99.2% electrified, 69,427 of 70,001 route-km [R15b]; AC-immune relay specs [R53] |
| F11 | Maintenance and configuration error | Wrong wiring, undocumented alteration, wrong disconnection/reconnection | Anomalies that precede or accompany accidents | CRS found "lapses at multiple levels" in the Balasore accident; wrong signalling due to circuit alteration; unusual point behaviour had been reported on the day [R17] |
| F12 | No-fault-found (NFF) intermittent faults | Intermittent contact, environmental | Short unexplained flickers | NFF is a significant subset of track-circuit failures and is unpredictable without continuous data [R30] |

## 3.5 Why failures are *correlated*, and how to say it correctly

Track circuits are separated by insulated joints or tuned boundaries so one circuit does not electrically feed its neighbour. Yet failures *cluster*. The correct causal story has four channels. This is the core technical reframing of "propagation":

| Channel | Mechanism | Example | Graph edge in our model |
|---|---|---|---|
| **Common cause (environmental)** | One weather cell, flood, or lightning event affects many circuits at once | Monsoon rain over a yard; lightning at a station [R2][R14] | *Co-location / weather-cell* edge |
| **Shared infrastructure** | Same power supply, relay room, cable route, location box, EI network | A single network failure knocking out several ABS sections [R2]; IPS backup checks [R14] | *Shared-asset* edge |
| **Functional/operational dependency** | A failed circuit blocks a route; interlocking and adjacent block logic couple sections | Route held up; BPAC and block dependencies [R54] | *Interlocking/route* edge |
| **Maintenance-induced** | Alterations, wiring changes, repeated resets | Balasore: wrong wiring after alteration [R17]; MSDAC "resets" without root-cause at Arariya Court [R2] | *Work-history* edge |

> **Analogy: the dark street.** If a whole street goes dark, the bulbs did not infect each other. A transformer, a cut cable or a storm affected them together. A smart city operator who only reads each bulb's status sees "50 unrelated failures". One who models the street's grid sees "1 transformer problem". That is exactly the difference our graph layer makes.

---

# 4. The Identified Problems

Each problem includes a real-world analogy so it can be told to non-engineers.

**P1. Silent degradation: the margin shrinks invisibly.**
*What:* Relay current/voltage slowly declines as ballast conductance rises, but nobody sees the trend until the relay drops. See the computed illustration in Section 5.3.
*Analogy:* A slow puncture. You only notice when the tyre is flat, though pressure has been falling for weeks.

**P2. Reactive maintenance culture ("find-and-fix", not "predict-and-prevent").**
*What:* Official statements describe signalling maintenance as manual and find-and-fix rather than predictive [R25]. CAG found 100% of required maintenance blocks were granted in SWR yet failures continued in substantial numbers, meaning *more blocks* alone does not fix the problem [R10].
*Analogy:* Servicing a car strictly every 10,000 km regardless of how it is actually being driven.

**P3. Fragmented data: every vendor, every station, a different language.**
*What:* About 100+ RDPMS stations use different OEM business rules; Railway Board is still defining standard data structures, CCSP compliance, a common broker layer and a unified dashboard [R1].
*Analogy:* Every hospital ward has its own bedside monitor with its own units and no central ICU screen.

**P4. Rule-based alerts have limited intelligence.**
*What:* Existing RDPMS uses OEM-defined business rules. Zones themselves said bigger datasets are needed to use AI/ML [R1]. Rules do not adapt to local ballast, climate, traffic or asset age.
*Analogy:* A smoke detector that beeps at a fixed threshold; it cannot tell burnt toast from a real fire.

**P5. Failures are treated as isolated events, though they cluster.**
*What:* Lightning, shared supply faults and single-point network failures hit many sections together [R2]. Without a graph/dependency view, the same root cause is investigated repeatedly as many "separate" faults.
*Analogy:* Fixing each dark bulb on a street without checking the transformer.

**P6. Dual detection can mask track-circuit decay.**
*What:* CAG found that where a station has both track circuiting and axle counters, the signal can clear as long as *either* shows clear, and operating instructions did not require the Station Master to examine a track-circuit failure. In the documented case, a DC track-circuit failure at **02:16:47 on 28 December 2016** at Rura (North Central Railway) was not followed up; trains ran until the Sealdah–Ajmer Express (12987) derailed at 05:30, injuring over 50 people, with rail fracture the probable cause per the supervisors' joint note [R12]. CAG concluded that had the track-circuit failure been used as a prompt to examine the track, the accident could have been prevented. New EI designs now *plan* axle counters in parallel with DC track circuits [R3], so the masking risk is structural.
*Analogy:* A house with two smoke alarms where the system accepts either one. If one battery quietly dies, nobody notices until the other also fails.

**P7. Data quality and manual-entry burden in SMMS.**
*What:* Railway Board repeatedly asked zones to ensure correct SMMS entries; one old relay failed because the asset record was wrong [R2]. S&T staff themselves say entries are done on phones, are cumbersome and error-prone, and backlogs form [R24].
*Analogy:* A hospital where nurses type patient vitals from memory at the end of the shift.

**P8. Black-box fear: alerts without reasons are ignored.**
*What:* Safety staff must justify actions to supervisors, CRS and auditors. A score without cause will not be trusted.
*Analogy:* A doctor who says "you will fall ill soon" without any test result.

**P9. Climate stress is rising and regional.**
*What:* Monsoon, flooding and lightning drive many incidents; Railway Board issues annual precautions (ballast clearance, point machine lifting in waterlogged areas, sealing of point machines before monsoon) [R14][R2]. Adaptive risk models per location are absent from public documentation.
*Analogy:* Giving every farmer the same irrigation schedule regardless of local rainfall.

**P10. Late detection of maintenance-induced errors.**
*What:* The Balasore accident investigation attributes the crash to wrong signalling from circuit alteration lapses, with earlier unusual behaviour reported but not acted on, and a similar earlier incident (2022) not followed by corrective measures [R17].
*Analogy:* A pilot ignoring repeated cockpit warnings from the previous flight.

**P11. Safety-critical certification and adoption friction.**
*What:* Any new equipment must align with RDSO specifications and approved lists; for RDPMS tenders, OEM status depends on RDSO-approved firms or a minimum number of installations [R-ELD: see R55]. A hackathon prototype cannot jump this barrier; it needs a trial path (Rail Tech Policy, Section 21).
*Analogy:* A new medicine needs clinical trials, not just a good lab result.

**P12. Evidence gap: no open benchmark dataset for Indian track-circuit health.**
*What:* Public railway AI datasets are few relative to the literature; maintenance datasets exist mainly for track geometry, bearings and similar assets, and railway companies rarely publish data [R40]. I found no public Indian track-circuit time-series dataset.
*Analogy:* Training a doctor with no patient records.

---

# 5. Real-World Evidence

## 5.1 The safety pyramid: why predictive analytics belongs at the base

| Layer | Quantity | Ref |
|---|---|---|
| Consequential events attributed to signalling failures nationally (five years to mid-2023) | **13** | [R18] |
| Signal failures/defects in *one zone* (SWR, 2018-19 to 2022-23) | **14,808** (average **2,961 per year**) | [R10][R11] |
| Of which "Miscellaneous" category (bad workmanship, lamp fused, route held up etc.) | 2,343 | [R11] |

Two numbers, three orders of magnitude apart. Accidents are rare; *failures* are numerous. Predictive maintenance acts on the huge base of precursor events so that the top of the pyramid stays small.

## 5.2 Wider operational context

* Punctuality index declined from 94.17 (2020) to 73.62 (2023) according to Railway Board data cited by IndiaSpend [R15a].
* The Ministry of Railways itself warned in September 2025 that repeated signal failures threaten safety and reliability [R16].
* Maintenance practices were found "directly linked" to asset failures that contributed an average 22.2% of overall punctuality loss in 2018 (rail, weld and signal failures) [R16b].
* Indian Railways carried **6,905 million passengers in 2023-24** and operated **7,461 stations** on **69,181 route-km** as at 31 March 2024 [R77]; the network has since grown to about **69,400 route-km** [R15b].
* Ministry claims train accidents fell **about 88% since 2014-15** [R59]; signalling failures fell about 58% in 11 years [R5]. Different outlets report different end-year accident counts, so quote the percentage and one named source, not a count. Our pitch should *build on* this progress ("the next gains come from prediction") rather than contradict it.
* CAG found that Indian S&T equipment MTBF and MTTR varied widely across zones (2013 thematic study) [R13].

## 5.3 A computed illustration: how ballast moisture erodes the safety margin

We built a small **transmission-line model** of a DC track circuit (feed end with limiting resistor, uniform rails with series resistance, uniform ballast leakage, relay at the far end). Transmission-line modelling of track circuits is standard in the literature [R43][R44]. **[Design choice / Assumption]** The parameters below are *illustrative, not Indian-Railways-calibrated*: length 0.75 km, rail loop resistance 0.10 ohm/km, feed 12 V through 3 ohm, 9 ohm relay, 0.5 ohm train shunt. Values are normalised to the dry-ballast relay current.

| Ballast resistance (ohm-km) | Relay current, section **free** (% of dry) | Relay current, section **occupied** (% of dry) |
|---|---|---|
| 50 | 96.7 | 17.8 |
| 20 | 92.1 | 17.6 |
| 10 | 85.4 | 17.3 |
| 8 | 82.4 | 17.2 |
| 6 | 77.8 | 17.0 |
| 5 | 74.5 | 16.8 |
| 4 | 70.1 | 16.6 |
| 3 | 63.7 | 16.1 |
| 2.5 | 59.4 | 15.8 |
| 2 | 53.9 | 15.4 |
| 1.5 | 46.6 | 14.7 |
| 1.0 | 36.8 | 13.5 |
| 0.7 | 28.8 | 12.1 |

ASCII view of the *free-section* relay current as ballast gets wetter (each `#` is about 5%):

```
Ballast (ohm-km)   Relay current when section is FREE (% of dry value)
 50  ###################  96.7
 20  ##################   92.1
 10  #################    85.4
  8  ################     82.4
  6  ###############      77.8
  5  ###############      74.5
  4  ##############       70.1   <- early-warning zone (assumed 70%)
  3  #############        63.7
  2  ###########          53.9
1.5  #########            46.6   <- assumed relay drop-away (~50%) crossed
1.0  #######              36.8
```

**Reading the table.** With these assumed numbers the relay would drop at roughly 1.7 ohm-km (about 50% of dry current), and an early-warning level of 70% is reached near 4 ohm-km. The point: *the circuit looks "healthy" (relay up) across most of that range*, yet the margin is vanishing. A binary alarm sees nothing until the end; a trend-aware estimator sees the slope.

### Synthetic monsoon-drift demonstration (fully reproducible)

The script in Appendix C (`nidan_twin.py`, seeded) simulates 60 days in which ballast resistance falls from 8.0 to 1.5 ohm-km with measurement noise, then applies a simple detector: 7-day slope more negative than −0.3 percentage points/day **and** level below 75%. Every number below is printed by running the script; nothing is hand-entered.

Linear wetting, seed 7:

| Day | Ballast (ohm-km, true) | Relay current (% of dry, noisy) | Twin's inverse estimate (ohm-km) |
|---|---|---|---|
| 0 | 8.00 | 82.2 | 7.90 |
| 10 | 6.92 | 79.7 | 6.71 |
| 20 | 5.83 | 75.9 | 5.38 |
| **26** | **5.18** | **73.1** | 4.64 (**trend alarm raised**) |
| 30 | 4.75 | 72.6 | 4.53 |
| 40 | 3.67 | 67.9 | 3.62 |
| 50 | 2.58 | 61.1 | 2.69 |
| **59** | **1.61** | **47.8** | 1.57 (**relay drop-away**) |
| 60 | 1.50 | 46.6 | 1.50 |

**Lead time in this toy example: 33 days (alarm day 26, drop-away day 59).** With an exponential (fast-onset) wetting the same detector alarms on day 16 and the relay drops on day 56, a lead of 40 days. The twin's inverse estimate stays within **10.4%** of the true ballast resistance at the checkpoints, which is the point of the physics layer: it recovers a hidden quantity from an observable one.

Three honest caveats, and they matter:

1. **This is not evidence about real Indian circuits.** It is a proof of mechanism that a physics-aware trend estimator can see a shrinking margin that a threshold alarm cannot.
2. **The lead time is a property of the scenario, not a result.** It scales with how slowly the wetting happens and with where the alert thresholds sit. Never quote 33 or 40 days as an expected field number.
3. **The v1.0 run is withdrawn.** It reported a 24-day lead from noise draws that were not saved and could not be regenerated. v1.1 replaces it with this seeded run, which anyone can reproduce with one command.

The full code and its exact output are in Appendix C.

---
# 6. What Already Exists (India and World)

## 6.1 India: the RDPMS programme and its ecosystem (the most important finding)

**RDPMS = Remote Diagnostic and Preventive/Predictive Maintenance System for signalling gear.** The Railway Board held a dedicated meeting on 31 January 2025 (minutes issued 25 February 2025) with Zonal Railways, RDSO, CRIS and five OEMs (Bitcom, Energy 7, Efftronics, JARS Service, Gadgeon) [R1]. Key facts from those minutes:

| Topic | What the Railway Board recorded | Ref |
|---|---|---|
| Current coverage | Around **100+ individual stations** have RDPMS, using **different business rules defined by OEMs** with zones | [R1] |
| Standardisation | RDSO drafted **standard business rules and a common protocol** in a new draft FRS; the FRS was to be released by Feb 2025 and apply to all new and ongoing projects [R1]. This has since materialised as the published specification **RDSO/SPN/257/2025 v2.0** (RDPMS, effective 31.12.2025) [R69] | [R1][R69] |
| Results so far | Zones said even OEM-defined rules had prevented certain failures and detected abnormalities | [R1] |
| AI/ML readiness | Zones said **bigger datasets were required** to leverage AI and machine learning | [R1] |
| Edge/IoT | New RDPMS edge and IoT devices must comply with **CCSP** standards; data structures to be standardised across OEMs; a **unified dashboard** to be built | [R1] |
| Common layer | **CRIS** to assess CCSP or an alternative common service protocol; coordinate with C-DOT | [R1] |
| Unified software | **CRIS** to develop a unified RDPMS application with a common dashboard; OEM software to be hosted on CRIS servers, **integrated with SMMS**, replacing OEM-specific apps eventually | [R1] |
| Sensor quality | RDSO to standardise **sensor calibration procedures and periodicity**, power-supply robustness for IoT/edge devices, and issue a pre-commissioning checklist (PCCL) | [R1] |

**Why this matters to us.** Railway Board has *written down* the gaps (fragmented rules, no common data model, small datasets, no unified analytics). Our project is a direct, constructive answer to that list. We can position ourselves as the **analytics and intelligence layer that plugs into the CRIS unified RDPMS programme**, not as a competitor to the OEMs.

**The standard now exists in print.** RDSO's specification list carries **RDSO/SPN/257/2025 Version 2.0, "Remote Diagnostic and Predictive Maintenance System (RDPMS)"**, effective 31.12.2025 [R69]. The specification's stated objective is to help the maintenance team act in advance to prevent signalling-gear failure, with probable-cause diagnosis to cut MTTR and ML-driven alerts for gears likely to fail — which is the strongest possible validation of the problem statement: the requirement is official, the standard is published, and the analytics layer is still the open part. Tenders issued since December 2025 (for example NCR Prayagraj's upgrade of seven stations and SCR Guntakal's eight-station RDPMS with analytics) specify compliance with this exact version [R69].

**C-DOT's CCSP registry.** C-DOT's Common Service Platform lists vendors (for example Bitcomm, Energy7, Gadgeon, Efftronics, Aquasense, JARS Services) under the "RDSO-RDPMS" vertical, alongside CRIS verticals such as IR-NIYANTRAC (Indian Railways Native IoT based Yield Analysis Telemetry, Recording and Control) [R20][R56]. This shows an established vendor ecosystem and a standard IoT platform to integrate with.

**Vendors and deployments (claims by sources, not independently audited):**

* Efftronics describes itself as the largest provider of data loggers and IoT solutions to Indian Railways and plans RDPMS at about 600 Southern Railway stations using 20-30 ms sampling to support AI/ML [R21]. (Company-sourced claim.)
* Western Railway commissioned RDPMS at Atul station; the stated functions are probable-cause diagnosis to reduce Mean Time To Restore, and automatic alerts for signalling gear likely to fail "based on the system learning" [R23].
* IRCON received a ₹51.61 crore work order from North Western Railway for RDPMS across sections of Jaipur, Ajmer, Bikaner and Jodhpur divisions, 24-month completion [R22].
* RDSO instructs that data loggers and RTUs should be able to work as IoT devices usable in RDPMS [R55].
* A metro system has already deployed a **Remote Health Monitoring System for signalling** from a centralised location, covering electrical parameters of outdoor equipment such as point machines and signals (Delhi Metro, Magenta Line), and lists it among its predictive-maintenance systems [R76][R75]. Note what it is *not*: centralised parameter monitoring, not physics-based RUL or common-cause analytics.

**SMMS (Signal Maintenance Management System, CRIS).** Western Railway registered 3,01,650 signalling assets in SMMS with roughly 30,000 daily maintenance entries; staff report that data entry is cumbersome and error-prone [R24]. Railway Board asks zones to ensure correctness of asset details, in-charges and cause-of-failure entries, and to run morning failure conferences through SMMS [R2][R-SMMS]. CAG notes SMMS is intended to facilitate predictive maintenance of signalling assets [R10].

**Earlier initiative.** In 2017 Indian Railways announced remote condition monitoring of signals, track circuits, axle counters, interlocking sub-systems, power supplies, relays and timers using non-intrusive sensors, with predictive/prescriptive analytics and pilots on Ahmedabad-Vadodara and Bengaluru-Mysuru sections [R25]. The idea is therefore not new in India; **execution at scale and intelligence quality are the open problems**.

**Adjacent Indian technology (not signalling):** Integrated Track Monitoring Systems (3 deployed, ML-based inspection of track components), Wheel Impact Load Detectors (24), Online Monitoring of Rolling Stock (25), Machine Vision Inspection Systems, drone-based OHE inspection; plus the **Rail Tech Policy adopted 26.02.2026** with a portal, 50:50 cost-sharing for prototype development and trials, and grants for extended trials or scale-up [R4][R57]. These show institutional appetite for AI and a **funding path for startups** [R4].

**Safety overlay (not health analytics).** Kavach is an ATP safety system (RFID tags, towers, optical fibre, loco equipment); version 4.0 adds direct interface to existing electronic interlocking [R19]. Kavach protects against collisions; it does not predict track-circuit decay. Since EI consumes track-occupancy inputs, healthy track circuits indirectly support reliable Kavach operation **[our inference]**.

**Indian research.** RSTGCN is the first graph-convolutional model for delay prediction on the entire Indian railway system [R37]. A reliability study used Indian logbook failure data (Kharagpur to Bali Chalk, 2005-2010) for inspection modelling of signalling subsystems [R64]. Neither targets track-circuit health with physics-informed or survival-based prediction.

## 6.2 International commercial platforms

| Platform | What it does | Relevance and limits | Ref |
|---|---|---|---|
| **Siemens Railigent X** | Cloud platform for predictive maintenance and operational decision support across rolling stock, infrastructure and signalling; Siemens is active in India (e.g., Auto Block Signalling technology; Railigent X on loco programmes) | Strong platform; typically tied to vendor ecosystems and commercial contracts; not an open, RDPMS-neutral layer for IR's multi-OEM fleet | [R45] |
| **Alstom HealthHub** | Web platform analysing data from trains, signalling and infrastructure, "including Alstom and non-Alstom" assets; used in Indian loco maintenance contracts | Same: commercial, vendor-led | [R46] |
| **Thales TIRIS** | "Discover, predict and advise" smart maintenance platform; remote condition monitoring in UK (Network Rail Anglia) | Shows maturity of RCM in UK; proprietary | [R47] |
| **Hitachi Rail OBCMS** | On-board sensors on 100 LHB Smart Coaches monitor wheel, bearing, ride and track, covering about 8,600 km route length | Rolling-stock-borne; monitors track *geometry/deterioration*, not signalling track-circuit electrical health | [R48] |
| **Wabtec** (named in the sheet) | Sells **relay condition monitoring** (Mors Smitt RCM: coil voltage, contact current, remaining-life estimate) [R71] and markets **Smart Crossings**, whose own literature names "maintenance of detection circuits, track circuit degradation" as the pain it addresses [R72]; broader portfolio is KinetiX inspection and train control | Relay-level and crossing-level condition monitoring, not physics-informed, graph-aware RUL for DC/AC/AF track circuits; no RDPMS/SMMS integration for Indian Railways | [R71][R72] |

## 6.3 Academic and applied research (verified)

| Work | What it shows | Limits relative to our goal | Ref |
|---|---|---|---|
| de Bruin et al., IEEE TNNLS 2017 (LSTM for track circuit fault diagnosis) | LSTM classifies 99.7% of test sequences with no false positive detections, and beats a CNN; thesis shows unsupervised pre-training helps when labels are scarce | Results on a generative-model-based setup; no network/graph, no survival, no Indian conditions | [R28] |
| Alstom, ICROMA 2025 (CVCM track circuits, deep learning + conformal prediction) | 10 anomaly classes; 99.31% accuracy; early detection within about 1% of anomaly onset; ISO 17359-aligned; conformal uncertainty; validated on 10 failure cases | Specific to one track-circuit technology (CVCM); per-circuit; no cross-asset graph or RUL; proprietary data | [R26] |
| Alstom, STDS track circuit (SVM) | Identifies which component is failing using current/voltage data from 10 field circuits | Small data; per-circuit | [R27] |
| Tao et al., Sci. Reports 2024 (MSAN) | Multi-scale attention network reaches 99.36% on real track-circuit fault data; notes operators mostly rely on manual inspection and centralised monitoring | Uninsulated (jointless) Chinese-type circuits; classification, not prognosis | [R29] |
| Czech Republic study (IEEE) | Survival models with left/right censoring for life expectancy of electronic track circuits from 10 years of failure reports | Component-level, no covariate-rich deep Bayesian approach; no graph | [R32] |
| Pascale et al. (Weibull for electronic signalling) | Constant-failure-rate assumptions can mislead; Weibull supports safety-oriented maintenance decisions | Methodological; no live data | [R34] |
| Zeng et al. 2023 (BNN-Surv) | Deep Bayesian survival for *rail* life with censoring, C-index 0.80, confidence intervals | Applied to rail (steel), not signalling | [R33] |
| Delay-propagation GNNs (Dutch GAT, HetGNN, STGCN, RSTGCN) | GNNs model spatio-temporal delay spread across stations/trains. The Dutch GAT is Huang, Guo, Liu & Corman (2024), *Transportation Research Part E* 184:103457, calibrated on Dutch network operations and using attention weights to explain *where* delay propagates; RSTGCN covers the Indian network | Predict *train delays*, not *infrastructure health*; do not model electrical or common-cause failure | [R35][R36][R37][R38] |
| Cascade failure GNN (I3) | GNNs for cascading failures in interdependent urban infrastructure | Urban infrastructure, not railway signalling | [R39] |
| Transmission-line modelling of track circuits | Track circuits modelled as transmission lines, including uneven ballast degradation; simulation methods | Simulation only; not integrated with data-driven pipelines | [R43][R44] |
| Patents on ballast estimation | Methods to infer ballast resistance from track impedance phase; software models to estimate track-circuit parameters (Alstom family) | IP-protected; per-circuit | [R51] |

**GitHub and open code.** My search found no public repository implementing GNN + Bayesian survival for track-circuit health. One student repository on railway traffic optimisation (10-block simulation with dashboard and RL) appeared but is not about asset health [R61]. Core libraries we would build on are well known (PyTorch Geometric, PyG-Temporal, SHAP, lifelines, OSRD, railML, SUMO) [R62; **retrieval not verified in this session**, check each link].

## 6.4 Public datasets

A systematic review found few open railway AI datasets compared with the literature; most maintenance datasets concern track geometry, bearings and similar assets; railway companies are conservative about sharing data [R40]. The review lists ProRail image datasets including insulated joints and fasteners [R40]. MetroPT (Porto metro compressor data) is a benchmark for predictive-maintenance methods [R41]. A broader overview catalogues degradation datasets for PHM tasks [R42]. **No public Indian track-circuit time series was found.** Section 15 explains how we handle that.

---

# 7. Why Existing Solutions Are Not Complete

| Solution class | What it does well | Why it is **not complete** for the problem |
|---|---|---|
| **Manual inspection + data logger review** | Catches visible and obvious defects; mandatory and trusted | Periodic, not continuous; relies on human judgement; slow-drift degradation invisible between visits; CAG saw full maintenance blocks yet failures persisted [R10] |
| **SMMS (asset & failure register)** | Asset registry, failure entries, codal-life alerts, morning conferences | Depends on manual entry; wrong data defeats alerts [R2][R24]; not a real-time analytics engine |
| **Current RDPMS (OEM rule-based)** | Real-time monitoring, probable-cause hints, alerts; reported prevented failures [R1][R23] | Business rules differ by OEM; no common data model yet; small datasets; thresholds do not adapt; no cross-station learning; silos [R1] |
| **Kavach, interlocking, ABS** | Prevent collisions and human error | Not health prediction; they *consume* healthy inputs |
| **ITMS/WILD/OMRS/MVIS** [R4] | Track geometry, wheel/bearing, visual inspection | Do not monitor signalling track-circuit electronics |
| **Commercial global platforms** [R45][R46][R47] | Mature analytics, proven abroad | Vendor-tied, commercial and may not fit multi-OEM IR reality; not designed around IR's dual-detection, SMMS, CCSP landscape |
| **Per-circuit deep learning papers** [R26][R28][R29] | Very high accuracy on their datasets | Single circuit type; no network view; limited prognosis; proprietary or non-Indian data; labels scarce |
| **Delay-propagation GNNs** [R35]-[R38] | Network effects of *train delays* | Wrong target variable (delay, not asset health) |
| **Survival studies** [R32][R33][R34] | Handle censoring and age effects | Not connected to live sensor streams, graph risk, or explainable dispatch |

**A summary in one sentence:** *each piece exists somewhere; nobody has combined physics, live sensing, graph risk, survival prognosis, calibrated uncertainty, explainability and Indian operational integration into one vendor-neutral, advisory-only layer.*

---

# 8. Gap Analysis: What Must Be Filled

| Gap | Description | Evidence | Severity | How we fill it |
|---|---|---|---|---|
| **G1** Interoperability | No common data model across RDPMS OEMs | [R1] | High | Canonical event schema + OEM adapters; align with CCSP/CRIS directions |
| **G2** Intelligence beyond rules | Fixed business rules; zones want AI but lack data | [R1] | High | Physics-informed anomaly detection + ML residuals; synthetic data to bootstrap |
| **G3** Hidden-parameter estimation | Raw thresholding ignores that ballast conductance etc. drive signals | [R43][R51] | High | Per-circuit digital twin with online parameter estimation |
| **G4** Network/common-cause view | Correlated failures investigated as isolated faults | [R2] | High | Heterogeneous dependency graph + spatio-temporal GNN |
| **G5** Prognosis, not just detection | Binary alarms; no time-to-failure with uncertainty | [R32][R33] | High | Bayesian survival with frailty + conformal prediction |
| **G6** Masked failures under dual detection | One system may hide the other's degradation | [R12][R3] | High | Cross-modal consistency monitor (TC vs axle counter vs EI events) |
| **G7** Data quality and trust | Wrong SMMS entries, staff burden | [R2][R24] | High | Data-trust scoring, reconciliation, auto-prefilled entries |
| **G8** Explainability | Black-box scores unacceptable in safety culture | Domain norm | High | Physics explanation + SHAP + precedent cases |
| **G9** Change-management risk | Maintenance alterations can create latent hazards (Balasore) | [R17] | Medium-High | Work-history edges, reset-pattern and "unexpected behaviour" alerts (advisory) |
| **G10** Climate adaptivity | One-size thresholds for varied monsoon/lightning exposure | [R14][R2] | Medium | Location-conditioned baselines; weather covariates; seasonal models |
| **G11** Certification and adoption path | Equipment needs RDSO approval; startups need trial route | [R60][R4] | Medium | Non-vital design; shadow-mode pilots; Rail Tech Policy route |
| **G12** No open benchmark | No public Indian TC dataset | [R40] | High | Open simulator + synthetic benchmark + data-sharing MoUs |

---

# 9. Our Proposed Solution: Concept and Positioning

## 9.1 Name, meaning and one-line pitch

**NIDAN (निदान)** — root-cause diagnosis. Pronounced *ni-DAAN*.

| Language | Word | Meaning |
|---|---|---|
| English | NIDAN | root-cause diagnosis |
| Hindi | निदान (Nidān) | diagnosis and root cause; in everyday Hindi also "remedy / solution" |
| Sanskrit | निदानम् (Nidānam) | cause, origin and diagnosis |

**Slide lock-up:** NIDAN | निदान — Predictive Failure Propagation Engine for Indian Railway Track Circuits

**Tagline.**

* **EN:** *Find the cause before the failure. Predict. Explain. Prevent.*
* **HI:** *विफलता से पहले, निदान। पूर्वानुमान · व्याख्या · रोकथाम*
* **SA:** *विफलतायाः पूर्वमेव निदानम्। पूर्वानुमानम् · व्याख्या · निवारणम्*

> *"NIDAN is a vendor-neutral, advisory-only intelligence layer that turns scattered track-circuit and signalling data into early, explainable, time-stamped warnings, and shows which warnings share a root cause."*

### Why NIDAN

1. **It speaks the Railways' language.** Their own programme is **RDPMS** — a *Diagnostic and Predictive Maintenance System* — and *nidān* literally means diagnosis. We are not inventing vocabulary; we are naming the thing the Railway Board already asked for [R1].
2. **It matches our core promise.** Our differentiator is showing *which warnings share a root cause*. "Nidān" covers both ideas — diagnosis (what is wrong) and root cause (why).
3. **It gives experts a memorable story.** NIDAN reads a track circuit the way a *vaidya* reads a pulse. Ayurveda's four diagnostic steps line up almost step for step with our system, which makes the architecture explainable to a non-ML audience in one slide.

### The vaidya analogy: Ayurveda's diagnostic steps mapped to NIDAN's layers

| Ayurvedic step | Meaning | NIDAN layer |
|---|---|---|
| **Pūrvarūpa** (पूर्वरूप) | Early warning signs, before the disease is manifest | Drift detection and **Watch** alerts on the circuit's own baseline (Steps D–E) |
| **Nidāna** (निदान) | The underlying cause | Physics twin + the three-part explanation: physics change, SHAP, similar past cases (Steps C, J) |
| **Samprāpti** (सम्प्राप्ति) | How the condition develops, stage by stage | Common-cause graph + survival model giving time-to-failure (Steps G–H) |
| **Upaśaya** (उपशय) | Response to a trial measure, used as a diagnostic clue | Rolling Block maintenance treated as an intervention, i.e. innovation **N8** (Step L) |

> **Analogy in one line.** A vaidya does not wait for the fever to name the disease: he reads the pulse, asks what changed, traces the cause, says how it will progress, and watches what the treatment does. NIDAN does exactly that for a track circuit.

## 9.2 Design principles

| # | Principle | Why |
|---|---|---|
| 1 | **Advisory and non-vital.** NIDAN never controls signals or influences vital logic. | Safety certification and trust; fits RDSO's cautious approval culture [R60] |
| 2 | **Non-intrusive sensing.** Read-only, galvanically isolated, high-impedance taps; also use *existing* data loggers and RDPMS feeds first | Matches Indian Railways' own "non-intrusive sensors" direction [R25] |
| 3 | **Physics first, ML second.** Use the transmission-line model to explain and constrain ML | Small data, safety culture, better generalisation [R43] |
| 4 | **Vendor-neutral.** Canonical schema + adapters | Railway Board is explicitly asking for interoperability [R1] |
| 5 | **Uncertainty-aware.** Every prediction ships with calibrated intervals | Maintainers need to know when *not* to trust it [R26] |
| 6 | **Human-in-the-loop, paperwork-reducing.** Alerts become pre-filled SMMS entries | S&T staff are already burdened with entries [R24] |
| 7 | **Data sovereignty and security.** Host on CRIS/Indian government infrastructure; CCSP-compliant edge | Railway Board directive on CCSP [R1] |
| 8 | **Honest about scope.** Station yards and point zones first; extensible to axle counters, points, power | Matches where TCs are deployed [R5][R3] |

## 9.3 What NIDAN does, end to end (plain English)

1. **Watches** the circuit's electrical "pulse" (feed voltage, relay current, timings, supply quality, environment) continuously and non-intrusively, plus the signalling logs that already exist.
2. **Understands** what the pulse *means physically* by fitting a model of the circuit (estimating ballast leakage, rail resistance, joint health) every few minutes.
3. **Detects** drift, intermittent faults and unusual patterns relative to *that circuit's own* normal behaviour, adjusted for weather and traffic.
4. **Connects the dots** across circuits, power supplies, cables, relay rooms, routes and recent maintenance to see whether many alarms share one cause.
5. **Predicts** time-to-failure with an uncertainty band.
6. **Explains** in one screen what changed and why it matters.
7. **Recommends** a ranked work list that respects maintenance windows, and **auto-prepares** the paperwork; the human approves or overrides.
8. **Learns** from what technicians find, so next month's predictions improve.

> **Analogy: from monthly check-up to wearable ECG with a cardiologist.** A monthly manual check is a periodic physical. NIDAN is a wearable that tracks heart rhythm continuously, knows *your* normal, notices drift, explains the trend and tells your doctor *which* of 50 patients to see first, and why.

---

# 10. Novelty and Innovations

## 10.1 Innovation list

| ID | Innovation | What is new | Why it matters | Evidence of gap |
|---|---|---|---|---|
| **N1** | **Physics-informed track-circuit twin with online parameter estimation** | Combine transmission-line model with filtering (e.g., UKF) to estimate ballast conductance, rail resistance, bond health from ordinary signals; ML only models the *residual* | Interpretable hidden states; data-efficient; gives explainable "why" | Modelling exists [R43][R44]; patents per circuit [R51]; not combined with network analytics |
| **N2** | **Dependency and common-cause heterogeneous graph for failure risk** | Graph with four edge types (weather-cell, shared asset, interlocking/route, work-history); spatio-temporal GNN predicts *correlated* risk | Moves from "isolated events" to "root-cause clusters"; avoids the physically wrong "km-long propagation" story | GNN rail work targets train delay [R35]-[R38]; cascade GNNs target urban infra [R39] |
| **N3** | **Masked-failure surfacing for dual detection** | Cross-modal monitor compares track-circuit state, axle-counter state and EI events to flag *degrading-but-hidden* circuits | Directly addresses the CAG observation [R12] and new dual-detection designs [R3] | Not found in literature or public IR documents |
| **N4** | **Bayesian survival with shared frailty + conformal prediction** | Time-to-failure per circuit with hierarchical effects (station, supply, climate zone) and distribution-free coverage guarantees | Proper handling of censoring and uncertainty; action thresholds in days with confidence | Survival [R32][R33][R34]; conformal [R26]; not integrated with graph and live data |
| **N5** | **Data-trust layer and SMMS auto-fill** | Score each asset record's trust (e.g., age vs. behavioural signature); reconcile with sensors; pre-fill failure/maintenance entries | Tackles documented data-quality and workload problems | [R2][R24] |
| **N6** | **Vendor-neutral canonical model and adapters** | One schema; adapters for Efftronics/Bitcom-style logs, EI loggers, CSV/MQTT/OPC-UA | Delivers what Railway Board asked CRIS/RDSO to build [R1] | [R1] |
| **N7** | **Three-part explanations** | (a) physics change ("ballast conductance up 38% in 12 days"), (b) SHAP feature contributions, (c) similar past cases from SMMS | Builds technician and auditor trust | General XAI practice; applied here to TC |
| **N8** | **Maintenance as intervention (causal learning)** | Treat cleaning/replacement during Rolling Block as interventions to estimate effect and generate labels | Converts routine work into training signal; counters label scarcity | Rolling Block exists [R5] |
| **N9** | **Sim-to-real pipeline** | Domain-randomised synthetic faults from the twin pretrain models; fine-tune with scarce field labels | Makes a 4-month MVP credible and gives the community an open benchmark | Label scarcity [R28]; no open IR dataset [R40] |
| **N10** | **Configuration-drift and reset-pattern alerts (advisory)** | Flag repeated resets, unexplained behaviour changes after work, and mismatches with as-built records | Targets Balasore-type latent hazards without touching vital logic | [R17][R2] |

## 10.2 Positioning against the closest prior work

| Capability | Rule-based RDPMS today [R1] | Per-circuit DL (Alstom CVCM) [R26] | Academic LSTM [R28] | Delay GNNs [R35]-[R38] | **NIDAN (ours)** |
|---|---|---|---|---|---|
| Live sensor ingestion | Yes (OEM-specific) | Offline study | Offline | No | **Yes (vendor-neutral)** |
| Physics-based hidden parameters | No | No | Generative model only | No | **Yes** |
| Early anomaly detection | Rules | Yes | Yes | n/a | **Yes** |
| Time-to-failure with uncertainty | No | Classification + conformal | No | No | **Yes (Bayesian survival + conformal)** |
| Network/common-cause view | No | No | No | Yes (for delays) | **Yes (for asset health)** |
| Dual-detection masking | No | No | No | No | **Yes** |
| Explainability for technicians | Probable cause hints [R23] | Limited | Limited | Some | **Physics + SHAP + precedents** |
| Fits Indian data/process landscape | Partly | No | No | Partly [R37] | **Designed for it** |

---
# 11. Methodology (Technical and Logical Detail)

## 11.1 Signals and data we use

| Group | Signals | Source (preferred order) | Notes |
|---|---|---|---|
| **Electrical (per track circuit)** | Feed voltage/current, relay voltage/current, relay pick-up and drop-away timings, ripple/noise, supply bus voltage; for AC/AF types also phase/frequency content | (1) existing data logger/RDPMS exports; (2) non-intrusive isolated sensors | Existing loggers sample at tens of milliseconds in current vendor plans [R21] |
| **Occupancy and traffic** | Occupied/free transitions, train counts, axle-counter counts and reset events, route settings | EI/data logger events, axle-counter health outputs [R54] | Needed for shunt-transient signatures and dual-detection cross-checks |
| **Environment** | Temperature, humidity, rainfall, enclosure humidity, lightning/surge counters | Local sensors + public weather feeds | Needed to separate "weather-explained" from "asset-explained" drift [R14] |
| **Maintenance and assets** | Failures with cause codes, work history, asset age and codal life, Rolling Block plan | SMMS [R24][R2], Rolling Block plans [R68] | SMMS accuracy is itself a risk (Section 19) |
| **Topology** | Station layouts, circuit boundaries, shared power supplies, cable routes, relay rooms, interlocking dependencies | Signal Interlocking Plans, cable route plans, railML-style export | Build once per station; reuse |

## 11.2 Processing pipeline (step by step)

**Step A: Quality control and calibration awareness.** Detect flat-lines, spikes, clock drift and sensor drift. RDSO is standardising sensor calibration procedures and periodicity [R1]; NIDAN records calibration status as metadata so models do not learn from uncalibrated drift.

**Step B: Edge feature extraction.** On the gateway, compute rolling RMS, DC level, slope, ripple, relay-timing statistics and shunt-transient shape on each occupancy transition. Keep raw bursts around events; send compact summaries otherwise.

**Step C: Physics-informed twin (per circuit).**
A DC track circuit is a lossy transmission line with series rail resistance and shunt ballast leakage, terminated by a relay. The characteristic quantities are gamma = sqrt(r*g) and Z0 = sqrt(r/g) (r = rail loop resistance per km, g = ballast conductance per km) [R43][R44]. Online estimation of hidden states uses a filter (for example an Unscented Kalman Filter):

```
State  x_t = [ g_ballast, r_rail, R_joint_leak, V_feed_effective ]
Model  y_t = h(x_t; L, R_source, R_relay) + noise      # h = transmission-line solution
Output x_hat_t with covariance, plus innovation residual e_t = y_t - h(x_hat_t)
```

*Honest limitation:* with only feed-end and relay-end measurements some parameters are not separately identifiable. We therefore (1) use Bayesian priors from circuit design data, (2) estimate an **effective** ballast conductance, and (3) add a tap or second measurement where possible. Patents show phase-of-impedance can indicate ballast resistance [R51], which supports using AC/AF measurements where available.

**Step D: Context-aware baseline.** Fit each circuit's *own* normal behaviour as a function of temperature, humidity, rainfall history and traffic (seasonal regression or small temporal model). Compute standardised residuals z_t so a monsoon-wet circuit is not flagged merely for being wet unless it is *abnormally* wet for its location.

**Step E: Anomaly detection ensemble.** Fuse (i) statistical change detectors (CUSUM/EWMA) on z_t, (ii) a self-supervised temporal model (LSTM-autoencoder or temporal convolution network), (iii) isolation-based detectors on summary features. Require persistence and cross-signal agreement before raising a watch-level alert, to control false alarms. Include a **flicker-rate feature** to tackle no-fault-found intermittents [R30].

**Step F: Fault-type diagnosis.** A classifier on windowed features and twin states labels the likely mode (taxonomy F1-F12, Section 3.4). Training mixes (a) synthetic faults generated by the twin with domain randomisation, (b) field labels from SMMS and technician confirmations. Pre-training on unlabeled data helps when labels are scarce, as shown in the track-circuit literature [R28]. Output uses **conformal prediction sets** so the system can say "mode is F1 or F4, not F5" with a coverage guarantee, as done in recent industrial work [R26].

**Step G: Failure-risk graph.**

```
Graph G_t = (V, E, X_t)
V : track circuits, point machines, signals, axle-counter sections,
    relay rooms, power supplies (IPS/battery), cable segments, weather cells
E : e1 weather-cell (co-location)     e2 shared-asset (power, cable, room, network)
    e3 interlocking/route dependency  e4 work-history (same crew/job/time window)
X : twin states, anomaly scores, age, last maintenance, environmental covariates
Model : heterogeneous GNN (GraphSAGE/GAT-style message passing per edge type)
        + temporal encoder (GRU or temporal conv) over a sliding window
Output: p_i(h) = P(circuit i fails within horizon h), h in {24 h, 72 h, 7 d}
        plus cluster posterior: P(common root cause k | alarms in window)
```

Why this design: heterogeneous GNNs model different entity types and interactions (HetGNN for railway delay evolution) [R36]; attention-based GNNs help explain *where* propagation is concentrated [R35]; cascading-failure GNNs handle high-order and inter-network dynamics [R39]. We adapt these ideas from *train delay* and *urban infrastructure* to *signalling asset health*. **Baselines and ablations:** (i) no graph (per-circuit model), (ii) a self-exciting point-process (Hawkes) model for failure clustering, (iii) a Bayesian network for cause attribution. If the GNN does not beat these, say so and use the simpler model.

**Step H: Bayesian survival and remaining useful life.**

```
Hazard   h_i(t | x_i(t), u) = h0(t) * exp( beta' x_i(t) + u_station + u_supply + u_climate )
Baseline h0(t): Weibull (interpretable) or neural (BNN-Surv style, MC-dropout) 
Covariates x_i(t): twin-state trends, age vs codal life, anomaly burden, maintenance history, climate zone
Censoring: right-censored (still working) and left-truncated (installed before records began)
Output   : S_i(t), median RUL, 10th/90th percentile RUL
```

Supported by prior work: survival models with left/right censoring for track-circuit life expectancy [R32]; Weibull rather than constant-failure-rate assumptions for electronic signalling [R34]; deep Bayesian survival with confidence intervals for rail life (C-index 0.80) [R33]. Random effects ("frailty") for station, supply and climate zone capture shared unobserved causes, which is the survival-analysis counterpart of the graph's common-cause edges.

**Step I: Calibration.** Apply conformal calibration to risk and RUL outputs (using held-out, time-ordered calibration data). Track calibration error and interval coverage continuously; recalibrate per zone.

**Step J: Explanation (three parts).**
1. *Physics:* "Effective ballast conductance rose 38% over 12 days; relay current margin fell from 82% to 66% of dry baseline."
2. *Feature attribution:* SHAP values for the classifier/risk model, shown as a force plot, as the problem sheet specified (which sensor or feature tripped the alarm).
3. *Precedent:* three most similar past events from SMMS with their confirmed causes and fixes.

**Step K: Decision and dispatch.** Rank circuits by *risk x consequence*, where consequence combines traffic density, availability of alternative detection (axle counter in parallel [R3]), proximity of the monsoon season, and cost of failure. Fit actions into **Rolling Block** windows, which are planned up to 52 weeks in advance under the Open Lines General Rules [R68]; where urgent, propose a special block. Generate **pre-filled SMMS entries** (asset ID, suspected cause, evidence) so the technician confirms rather than types [R24].

**Step L: Human-in-the-loop learning.** Technician feedback (one-tap "confirmed / not found / other") is stored as a label. Active learning requests feedback where model uncertainty is highest. Monthly retraining happens in shadow mode; promotion needs metric thresholds and sign-off (Section 16).

## 11.3 Alert policy (to avoid alarm fatigue)

| Level | Rule (example, **[Design choice]**) | Action |
|---|---|---|
| Info | Anomaly persistent for > N min, low confidence | Logged only |
| Watch | Risk(7 d) > 20% or RUL 10th percentile < 30 d, with persistence | Appears on SSE/JE worklist |
| Warning | Risk(72 h) > 30% or margin < early-warning level | Work order proposed; inclusion in next block |
| Critical | Risk(24 h) > 50% with high confidence or cluster root-cause detected | Immediate notification; propose special block |

An **alert budget** per section per day limits notifications; thresholds are tuned in shadow mode on real data, not guessed.

## 11.4 Edge AI specifics

* Gateway runs feature extraction plus a compact anomaly model (quantised, a few hundred kilobytes) so detection continues if backhaul is lost; data is buffered and forwarded.
* Time synchronisation (NTP/PTP/GPS) is mandatory; correlation across stations requires consistent timestamps.
* Device identity and message signing at the edge; compliance with CCSP edge/IoT standards as Railway Board directs [R1].

## 11.5 What we deliberately do **not** do

* No control of signals, points or any vital circuit.
* No connection to vital wiring except via certified, isolated, read-only taps approved by the zone/RDSO.
* No claim of SIL-rated functionality: NIDAN is advisory (SIL 0 context).

---

# 12. Before vs After

## 12.1 Side-by-side comparison

| Dimension | **Before (today)** | **After (with NIDAN)** |
|---|---|---|
| Detection timing | Mostly after relay drops or train stops; periodic inspections | Days to weeks ahead for drift-type faults (target; to be proven in pilot) |
| Data | OEM silos, data loggers, SMMS manual entries [R1][R24] | Canonical stream, adapters, data-trust scores |
| Intelligence | Fixed business rules [R1] | Physics twin + ML + graph + survival |
| Correlation | Each failure investigated separately [R2] | Common-cause clusters highlighted |
| Prognosis | None (alarms) | Time-to-failure with uncertainty |
| Dual-detection | Masked decay possible [R12] | Cross-modal monitor surfaces degrading circuit |
| Explainability | Probable cause hints [R23] | Physics + SHAP + precedents |
| Paperwork | Manual SMMS entry, backlogs [R24] | Pre-filled entries; confirm in one tap |
| Maintenance planning | Calendar/time-based | Risk-ranked, fits Rolling Block windows [R68] |
| Climate response | Annual circulars [R14] | Location-conditioned, season-aware risk |
| Learning | Slow, personal experience | Continuous, shared across zones |

## 12.2 A day in the life (illustrative story, synthetic numbers)

**Before.** Monsoon, mid-July. Track circuit "12T" at a busy yard has had a slowly sinking ballast resistance for weeks. Nobody sees it. At 17:40 heavy rain pushes the relay below drop-away; the section shows occupied with no train. The Station Master reports a failure; the ESM walks out in the rain. Trains queue. The failure is entered into SMMS after the shift. Next week, circuits 14T and 16T on the same drain fail too; each is logged as a separate event.

**After.** On day 35 NIDAN's twin shows effective ballast conductance rising and the relay margin falling faster than the weather explains. A **Watch** alert reaches the SSE's mobile worklist: *"12T: ballast conductance +31% in 12 days; margin 73% of dry; median RUL 21 days (10th pct: 9 days); likely cause F1 (drainage). Similar to 3 past events at this station."* The graph shows 14T and 16T share the same drain (weather-cell edge) and flags a *cluster*. The planner adds a 90-minute ballast-clearing job to the next Rolling Block. The monsoon day passes without failure. The SMMS entry is pre-filled; the technician confirms in one tap.

## 12.3 Process timeline (ASCII)

```
BEFORE  |-- normal --|-- slow drift (unseen) --|--FAIL--|-- delay + walk + repair + paperwork --|
                                                 ^ trains stop
AFTER   |-- normal --|-- slow drift --|WATCH|--- planned fix in block ---|-- normal continues --|
                                      ^ alert days ahead, with reason, root-cause cluster, pre-filled entry
```

---

# 13. Proposed System Architecture

## 13.1 Layered architecture (overview)

```
+------------------------------------------------------------------------------------+
|  L6  USERS & INTERFACES                                                            |
|  SSE/JE mobile app (offline-first)   Control-room dashboard   Zonal/CRIS analytics |
|  Alerts: app / SMS / SMMS pre-filled entries     APIs for CRIS unified RDPMS       |
+------------------------------------------------------------------------------------+
|  L5  DECISION & HUMAN-IN-THE-LOOP                                                  |
|  Risk x consequence ranking | Rolling-Block-aware scheduler | Approval / override |
|  Feedback capture (confirmed / not found) -> labels -> active learning             |
+------------------------------------------------------------------------------------+
|  L4  INTELLIGENCE                                                                  |
|  4a Physics twin (UKF)  4b Context baseline  4c Anomaly ensemble  4d Fault classifier|
|  4e Heterogeneous GNN risk graph  4f Bayesian survival (RUL)  4g Conformal calibration|
|  4h Explainer: physics + SHAP + precedent retrieval   4i Dual-detection monitor    |
+------------------------------------------------------------------------------------+
|  L3  DATA PLATFORM                                                                 |
|  Kafka topics (zone/division) + Schema Registry | stream processing (QC, features) |
|  Time-series DB (hot) | Parquet/object store (cold) | feature store | graph store   |
+------------------------------------------------------------------------------------+
|  L2  CONNECTIVITY & ADAPTERS                                                       |
|  MQTT/OPC-UA/Modbus/CSV adapters for OEM RDPMS, data loggers, EI logs, SMMS export |
|  CCSP/oneM2M-compatible gateway interface | mTLS | store-and-forward               |
+------------------------------------------------------------------------------------+
|  L1  EDGE (relay room / station)                                                   |
|  Industrial gateway: feature extraction, compact anomaly model, local buffer, clock|
|  Isolated, read-only sensors: current/voltage taps, humidity/temp, surge counter   |
+------------------------------------------------------------------------------------+
|  L0  EXISTING FIELD ASSETS (UNCHANGED, VITAL)                                       |
|  Track circuits, relays, axle counters, EI, data loggers/RTU, power supplies       |
+------------------------------------------------------------------------------------+
   Vital signalling chain is NEVER modified; NIDAN only observes (L0 -> L1 is one-way)
```

## 13.2 Data flow (end to end)

```
Sensors / Data loggers / OEM RDPMS
        |  (MQTT / adapters, signed, buffered)
        v
Edge gateway -- features + local alerts --> Station buffer
        |  (4G/OFC/CCSP gateway)
        v
Kafka (per-zone topics, Avro/Protobuf schemas)
        |-----> Stream QC & feature jobs ----> Time-series DB (hot) + Parquet (cold)
        |                                              |
        |                                              v
        |                                      Feature store
        v                                              |
Physics twin (per circuit) --> residuals --> Anomaly ensemble --> Fault classifier
        |                                                           |
        +--------------> Graph builder (topology + states) --> GNN risk + cluster posterior
        |                                                           |
        +--------------> Survival model (RUL, S(t)) ----------------+
                                                                    v
                                      Conformal calibration -> Explainer (physics+SHAP+precedent)
                                                                    v
                                         Decision engine -> Work-order proposals -> SMMS pre-fill
                                                                    v
                                      Mobile app / Dashboard <-> Technician feedback -> Labels
```

## 13.3 Deployment topology

| Tier | Where | What runs | Why |
|---|---|---|---|
| Edge | Station relay room / location box | Gateway, feature extraction, compact model, buffer | Low latency, works offline |
| Division / zone (optional) | Division HQ server or zone data centre | Kafka cluster slice, stream jobs, TSDB | Local analytics where connectivity limited |
| Central | CRIS-hosted/GI-cloud or on-prem Indian data centre | Model training, GNN, survival, dashboards, SMMS integration | Aligns with plan to host OEM RDPMS apps on CRIS servers integrated with SMMS [R1]; data sovereignty |
| Offline lab | Team bench / university | Simulator, benchmark, hardware-in-loop rig | Development and demo |

## 13.4 Scale sizing (back-of-envelope) **[Assumption]**

| Item | Assumption | Result |
|---|---|---|
| Stations in scope | 6,665 stations with complete track circuiting [R5] | 6,665 |
| Track circuits per station | **[Assumption]** about 30 on average (varies a lot) | about 200,000 circuits |
| Summary message rate | one 10-feature summary per circuit every 10 s, about 200 bytes | about 20,000 msg/s, about 4 MB/s |
| Daily volume | uncompressed about 345 GB/day; compression 5-10x | about 35-70 GB/day |
| At 1-minute summaries | about 3,300 msg/s | about 58 GB/day uncompressed |

These volumes are well within the capability of a standard partitioned log-based stream platform; the engineering challenge is device management, data quality and integration, not raw throughput.

## 13.5 Reliability and failure modes *of NIDAN itself*

| NIDAN failure | Consequence | Mitigation |
|---|---|---|
| Backhaul loss | No central alerts | Edge buffering; local alerts; delayed sync |
| Sensor drift | False trends | Calibration metadata; sensor-health models; cross-sensor checks [R1] |
| Model drift (season/hardware change) | Missed or false alarms | Drift monitors; shadow retraining; per-zone recalibration |
| Wrong asset metadata | Wrong explanations | Data-trust scoring and reconciliation [R2][R24] |
| Cyber intrusion | Data tampering or exfiltration | mTLS, signed messages, network segmentation, no write path to vital systems |
| Operator over-reliance | Missed hazards outside model scope | Training; clear "advisory" labelling; keep existing procedures |

---

# 14. Technology Stack: Domain-wise, With Justification

> **Selection logic.** Every row answers: *what is it, why this one, what problem does it solve, what else did we consider.* All choices are **[Design choices]**; versions should be pinned at build time. Open-source first (cost, auditability, no lock-in), matching the Rail Tech Policy's goal of cost-effective, scalable innovation [R4].

## 14.1 Edge, sensing and field hardware

| Component | Technology | Why this choice | How it helps the problem | Alternatives considered |
|---|---|---|---|---|
| Sensing front-end | Galvanically isolated, high-impedance voltage taps; non-intrusive current clamps (Hall/Rogowski); isolation amplifiers; simultaneous-sampling ADC | Read-only and fail-open so the vital circuit is never loaded; aligns with "non-intrusive sensors" direction [R25] | Captures the slow drift and timing signatures (P1) without safety risk (P11) | Direct wiring (rejected: safety); only logger data (insufficient for some signals) |
| Environment sensors | Temperature/humidity probes in enclosure and trackside; surge counter; rainfall via local gauge or public feed | Weather explains many variations [R14] | Separates weather from asset faults (P9) | Satellite-only rainfall (coarser) |
| Edge gateway | Industrial ARM-based gateway/SBC with wide temperature range, watchdog, secure element | Low power, rugged, runs containers and ONNX models | Local detection, buffering, signing | Raspberry-Pi-class boards for prototype only (not rugged) |
| Edge runtime | Linux + k3s or Docker; ONNX Runtime/TFLite | Same model artefacts as cloud; small footprint | Edge AI with offline operation | Bare-metal C (harder to update) |
| Time sync | GPS-disciplined NTP/PTP | Cross-station correlation needs accurate timestamps | Enables graph and cluster analysis (P5) | NTP only (less accurate) |
| Prototype bench | Resistor-ladder "ballast box" emulating leakage, relay, programmable DC source, fault injection switches | Enables a *physical* demo for experts and generates labelled data | Evidence for P1 mechanism and algorithm validation | Software-only (less convincing) |

## 14.2 Connectivity and messaging

| Component | Technology | Why | Problem addressed | Alternatives |
|---|---|---|---|---|
| Device messaging | MQTT (Mosquitto/EMQX) with TLS and per-device certificates | Lightweight, standard for IoT, works on poor links | Reliable transport from stations (P3) | HTTP polling (heavy), proprietary (lock-in) |
| Industrial adapters | OPC-UA, Modbus, CSV/SFTP adapters | Existing loggers and RDPMS vendors expose varied formats [R1] | Vendor-neutral ingestion (G1) | One-off scripts per vendor |
| Platform interface | CCSP/oneM2M-compatible interface (via C-DOT platform) | Railway Board directs CCSP compliance for new RDPMS edge/IoT devices [R1] | Compliance and interoperability | Custom cloud API only (risk of non-compliance) |
| Backhaul | 4G/5G, OFC where available, store-and-forward | Matches Indian rollout (OFC laying along tracks for Kavach) [R19] | Resilience | Satellite (cost) |

## 14.3 Streaming and ingestion

| Component | Technology | Why | Problem addressed | Alternatives |
|---|---|---|---|---|
| Event backbone | Apache Kafka (KRaft mode), topics per zone/division | The problem sheet specifies Kafka streaming; mature, partitioned, replayable, supports exactly-once semantics in pipelines | Handles ~tens of thousands msg/s (Section 13.4); replay for retraining and audits | Redpanda (Kafka-compatible), Pulsar |
| Schemas | Schema Registry with Avro/Protobuf; canonical data model | Enforce a common structure across OEMs [R1] | Interoperability (G1) | Free-form JSON (fragile) |
| Stream processing | Apache Flink or Kafka Streams (Python Faust for prototype) | Stateful windows, joins with topology, low latency | QC, feature windows, join with weather and events | Spark Structured Streaming (higher latency) |
| Connectors | Kafka Connect (to TSDB/object store), CDC from SMMS export if available | Standard integration | Pipeline robustness | Custom code |

## 14.4 Storage and data platform

| Component | Technology | Why | Problem addressed | Alternatives |
|---|---|---|---|---|
| Hot time series | TimescaleDB (PostgreSQL) or ClickHouse | SQL, compression, continuous aggregates; PostGIS available | Fast dashboards and feature queries | InfluxDB, VictoriaMetrics |
| Cold store | Parquet on S3-compatible storage (MinIO) | Cheap, columnar, ML-friendly | Long retention for survival modelling | HDFS |
| Metadata and assets | PostgreSQL + PostGIS | Spatial queries for weather cells, cable routes | Topology and geography | Neo4j (optional for graph exploration) |
| Graph store | Postgres tables + in-memory graph at training (PyG) | Simplicity; avoids operational burden | Graph construction (G4) | Neo4j/JanusGraph |
| Feature store | Feast (offline Parquet + online Redis) | Consistent features train/serve | Reproducibility | Hand-rolled |
| Cache/queue | Redis | Low latency lookups | Alert deduplication | Memcached |

## 14.5 Physics, simulation and digital twin

| Component | Technology | Why | Problem addressed | Alternatives |
|---|---|---|---|---|
| Track-circuit model | Python (NumPy/SciPy) transmission-line solver (see Appendix C) | Transparent, fast, unit-testable; established theory [R43][R44] | Hidden-state estimation, synthetic faults (G3, G12) | Modelica/Simulink (heavier), SPICE (slower at scale) |
| State estimation | Unscented Kalman Filter (filterpy or custom) | Non-linear measurement function; fast | Online ballast estimation | Particle filter (heavier) |
| Network topology | railML-style exchange, OpenStreetMap rail geometry for prototype | Open standards; railML is an open railway markup language [R49-related] | Digital twin map | Proprietary CAD |
| Traffic context simulation | OpenTrack, SUMO-rail, or OSRD | Generate traffic and occupancy patterns for synthetic scenarios [R49] | Realistic occupancy and shunt events | Custom timetable generator |
| "Digital twin" definition | Live graph state + per-circuit physics twin (not a 3D CAD twin) | Meaningful and achievable | Real-time state of the zone network | Full 3D (cost, little added value) |

> **Note on "OpenMTS":** the original sheet named a simulator "OpenMTS"; no railway tool with that name could be identified in this revision, so the name is dropped rather than repeated. The three tools in the row above are verified and sufficient: OSRD is an open-source railway simulation project, SUMO has documented railway extensions, and OpenTrack is a commercial timetable simulator [R49].

## 14.6 AI/ML

| Component | Technology | Why | Problem addressed | Alternatives |
|---|---|---|---|---|
| Core DL framework | PyTorch | Ecosystem for GNN/time-series; ONNX export | All models | JAX, TensorFlow |
| Graph learning | PyTorch Geometric + PyG-Temporal [R62] | Heterogeneous and temporal graph layers | N2, G4 | DGL |
| Time-series models | Temporal conv nets, LSTM/GRU autoencoders; tsai/Darts for baselines | Proven in track-circuit work [R28][R26] | Anomaly and diagnosis | Transformers (try if data allows) |
| Survival | lifelines (Weibull/Cox AFT), PyMC or NumPyro (Bayesian hierarchical/frailty), PyTorch BNN-Surv-style | Interpretable baseline + Bayesian uncertainty [R32][R33][R34] | G5 | scikit-survival |
| Gradient boosting | LightGBM/XGBoost | Strong tabular baseline; TreeSHAP | Fault classifier baseline | Random forests |
| Explainability | SHAP (force plots), counterfactual "what would restore margin" using the twin | Problem sheet requires SHAP force plots; supported by tree and deep explainers | G8 | LIME (less stable) |
| Uncertainty | MAPIE or custom split-conformal; calibration plots | Distribution-free coverage; used in industrial track-circuit work [R26] | N4 | Deep ensembles only |
| Edge inference | ONNX Runtime / TFLite with INT8 quantisation | Small footprint | Edge AI | Native C inference |
| Experiment tracking | MLflow + DVC | Reproducibility and audit trail | Governance | Weights & Biases |

## 14.7 Backend and services

| Component | Technology | Why | Problem addressed |
|---|---|---|---|
| API services | Python FastAPI (REST) + gRPC for internal | Same language as ML; fast to build; typed schemas | Unified APIs for apps and CRIS integration |
| Workflow orchestration | Temporal or Airflow/Prefect | Reliable retraining and batch jobs | Reproducible pipelines |
| Auth and roles | Keycloak (OIDC), role-based access by zone/division | Standard; fits Railway hierarchy | Access control and audit |
| Notification | SMS gateway, push, SMMS API/CSV connector | Reach field staff; reduce paperwork | G7 |
| Secrets | HashiCorp Vault or cloud KMS | Key management for device identities | Security |

## 14.8 Frontend and visualisation

| Component | Technology | Why | Problem addressed |
|---|---|---|---|
| Web dashboard | React + TypeScript + Vite | Large ecosystem, maintainable | Control-room usability |
| Geo/digital twin view | MapLibre GL JS + deck.gl | Open-source maps; WebGL performance for thousands of nodes | Live network twin |
| Charts | Apache ECharts or Plotly | Time series with confidence bands; SHAP plots | Explanations |
| Mobile app | Progressive Web App (offline-first with service workers + IndexedDB) | One codebase; works in poor connectivity; avoids app-store friction | Field staff reality [R24] |
| Localisation | i18n with English, Hindi, Odia and other regional languages | Staff diversity | Adoption |
| Accessibility | High-contrast, glove-friendly large targets, low-bandwidth mode | Field conditions | Adoption |

## 14.9 DevOps, MLOps, observability

| Component | Technology | Why |
|---|---|---|
| Containers/orchestration | Docker, Kubernetes (k3s at edge) | Portability, repeatability |
| CI/CD | GitHub Actions/GitLab CI, Argo CD | Automated tests and rollouts |
| Observability | Prometheus, Grafana, OpenTelemetry, Loki | Monitor pipeline and models |
| Model monitoring | Evidently or custom drift/calibration dashboards | Detect model drift (Section 13.5) |
| Infra as code | Terraform/Ansible | Auditability |

## 14.10 Security and compliance tooling

| Component | Technology | Why |
|---|---|---|
| Transport | mTLS everywhere; per-device certificates | Prevent spoofing |
| Message integrity | Signed payloads; secure element at edge | Data integrity (audit) |
| Segmentation | DMZ between corporate/IT and NIDAN; one-way (data diode style) from L0 to L1 | No write path to vital systems |
| Standards | Edge/IoT compliance with CCSP [R1]; industrial cybersecurity practice (IEC 62443-style) **[general practice, not retrieved here]** | Regulatory acceptance |
| Privacy | Minimise personal data (staff IDs, locations); retention policy | Data-protection law (Section 17) |

## 14.11 Testing and assurance

| Activity | Method |
|---|---|
| Unit and property tests | Physics invariants (e.g., relay current monotonic in ballast resistance) |
| Hardware-in-the-loop | Bench rig with injected faults |
| Replay testing | Replay recorded field streams through Kafka |
| Shadow mode | Run alongside existing RDPMS without affecting operations |
| Red-team and cyber testing | Pen-test of gateway and APIs |

## 14.12 Mapping: problem to stack

| Problem | Primary stack elements that solve it |
|---|---|
| P1 silent degradation | Isolated sensors, UKF twin, trend detectors |
| P2 reactive culture | Survival RUL + risk ranking + Rolling-Block-aware scheduler |
| P3 fragmentation | Adapters, Kafka + Schema Registry, canonical model, CCSP interface |
| P4 rule-based limits | Physics residuals + ML ensemble + context baselines |
| P5 clustering | Heterogeneous GNN with common-cause edges |
| P6 dual-detection masking | Cross-modal monitor (TC vs axle counter vs EI) |
| P7 SMMS data quality | Data-trust scoring + pre-filled entries |
| P8 black-box | SHAP + physics explanation + precedents |
| P9 climate stress | Weather covariates, location-conditioned baselines |
| P10 maintenance-induced hazards | Work-history edges, reset-pattern alerts |
| P11 certification friction | Non-vital design, shadow-mode pilots, Rail Tech route |
| P12 data scarcity | Simulator, synthetic benchmark, active learning |

---
# 15. Datasets and Data Strategy

## 15.1 The honest data situation

* **No public Indian track-circuit time-series dataset was found** in this research. A systematic review of open railway AI datasets found few datasets relative to the literature, mostly for track geometry, bearings, images and similar assets, and noted that railway companies rarely share data [R40].
* Zones themselves told the Railway Board that bigger datasets are needed for AI/ML [R1]. So **data scarcity is an industry-wide problem**, not just a student-project problem. Turning that into a strength (open simulator + benchmark + data-sharing framework) is part of our novelty (N9).

## 15.2 Data tiers (what we use and when)

| Tier | Source | What it gives | Limits | Use |
|---|---|---|---|---|
| **T0** | **Our physics simulator** (Appendix C) with domain randomisation and fault injectors F1-F12 | Unlimited labelled synthetic streams; controllable ground truth | Sim-to-real gap | Pre-training, ablations, demo, benchmark |
| **T1** | **Lab bench** (resistor-ladder ballast emulator + relay + programmable source) | Real electronics, real noise, labelled faults | Not real ballast/weather | Validate twin and detectors on physical signals |
| **T2** | **Public railway datasets**: ProRail insulated-joint and fastener images [R40]; MetroPT predictive-maintenance benchmark [R41]; PHM degradation dataset overview [R42] | Methodology benchmarks, image-based joint inspection, PdM evaluation practice | Not Indian track-circuit electrical data | Method sanity checks; auxiliary vision ideas |
| **T3** | **Indian Railways partners**: zone S&T departments (RDPMS exports, data-logger files, SMMS failure history), RDPMS OEMs [R1][R20] | Real signals, real failures, real labels | Access needs MoU and approvals | Pilot, fine-tuning, validation |
| **T4** | **Weather and environment**: public rainfall/lightning products and local sensors | Covariates for context baselines | Spatial resolution | Weather-conditioned baselines (P9) |
| **T5** | **Literature-derived parameters**: ballast, rail resistance and relay specs from standards and papers [R43][R44][R53] | Priors for the twin | Varies by site | Priors in Bayesian estimation |

## 15.3 Data request checklist (for a zone or OEM conversation)

| Data | Granularity | Period | Why we need it |
|---|---|---|---|
| Track-circuit electrical logs (feed/relay V and I) from data loggers or RDPMS | As recorded (tens of ms if available [R21]) | 12+ months incl. a monsoon | Training and validation |
| Occupancy and EI event logs, axle-counter events and resets | Event-level | Same | Dual-detection monitor; transients |
| SMMS failure records with cause codes, work history, asset age | Event-level | 3+ years | Labels, survival modelling [R24][R2] |
| Station layouts, circuit lengths, types (DC/AC/AF), cable and power maps | Static | Current | Graph and twin |
| Rolling Block and maintenance plans | Plan/actual | 12+ months | Intervention modelling [R68] |
| Local weather and lightning records | Hourly | Same | Context baselines |
| Sensor calibration records | Per device | Current | Data quality [R1] |

## 15.4 Synthetic data generator (NIDAN-Bench)

* **Inputs:** circuit length, rail type, source/relay parameters, ballast distribution by season, traffic pattern, supply quality, noise model.
* **Fault injectors (examples):** F1 ballast decline (ramps, rain pulses), F2 joint leakage (intermittent), F3 bond/rail break (step/impedance rise), F4 metallic bridging (partial persistent shunt), F5 relay ageing (timing drift), F6 supply sag/ripple, F7 surge bursts, F12 flicker.
* **Domain randomisation:** randomise parameters beyond nominal ranges so models learn physics-consistent features rather than memorising one circuit.
* **Outputs:** time series + ground-truth hidden states + fault labels + topology; released as an **open benchmark** (CC license) to fill gap G12.
* **Caution:** performance on synthetic data is **not** evidence of field performance. High accuracies reported in the literature (99.31% for CVCM anomaly classification [R26], 99.7% in a generative-model LSTM study [R28], 99.36% on a real dataset [R29]) come from specific circuits and setups; do not quote them as expected results for Indian circuits.

## 15.5 Labelling strategy

1. **Weak labels** from SMMS cause-of-failure codes and RDPMS rule triggers [R2][R1].
2. **Technician confirmation** in the app (one tap).
3. **Self-supervised pre-training** on unlabeled streams (helps when labels are few [R28]).
4. **Active learning** to ask for feedback on the most uncertain cases.
5. **Intervention labels** from Rolling Block work (cleaned ballast, replaced relay) as natural experiments (N8).

## 15.6 Data governance

MoU/NDA with zones and OEMs; data stays within Indian Railways-approved infrastructure; role-based access by zone; minimal personal data; audit logging; retention schedule; released public benchmark contains only synthetic or fully anonymised data.

---

# 16. Model Design, Evaluation and Validation

## 16.1 Tasks, models and metrics

| Task | Model | Primary metrics | Notes |
|---|---|---|---|
| T1 Anomaly detection | Physics residual + CUSUM/EWMA + temporal autoencoder + isolation forest | Detection lead time (hours/days before failure), false alarms per station-month, recall at fixed false-alarm budget | Operationally framed, not just AUC |
| T2 Fault diagnosis | GBM + temporal CNN/LSTM with conformal sets | Macro-F1, per-class recall, conformal coverage and set size | Subset of modes first (F1, F3, F5, F6, F12) |
| T3 Short-horizon risk | Heterogeneous GNN + temporal encoder | PR-AUC, precision@k on daily worklist, calibration (ECE), Brier | Compare vs no-graph and Hawkes |
| T4 Time-to-failure | Bayesian Weibull/Cox with frailty; BNN-Surv-style variant | C-index, time-dependent AUC, integrated Brier score, interval coverage | Handle left-truncation and censoring [R32][R33] |
| T5 Dual-detection consistency | Rule + learned discrepancy model | Detection of injected masked-decay cases; false positive rate | Needs TC and axle-counter data together |

## 16.2 Baselines (must beat these)

1. **Fixed threshold** on relay voltage/current (what a simple logger does).
2. **OEM-style business rules** (obtain examples from partners) [R1].
3. **Per-circuit LSTM/CNN** as in published track-circuit work [R28].
4. **Per-circuit model without graph** (ablation of N2).
5. **Constant-hazard / simple Weibull** without covariates [R34].
6. **Hawkes process** for clustering.

## 16.3 Validation protocol

| Element | Rule |
|---|---|
| Splits | Time-ordered train/validation/test; never shuffle across time |
| Leakage control | Group splits by station; exclude post-repair data from pre-failure windows; separate calibration set after validation |
| Generalisation | Leave-one-zone-out; hold out an entire monsoon season |
| Sim-to-real | Train on T0, fine-tune with small T3, test on T3 held-out |
| Informative censoring | Maintenance removes failures; treat repair as competing event or time-varying covariate (otherwise survival estimates are biased) |
| Ablations | Remove physics, graph, survival, conformal one at a time |
| Statistical rigour | Confidence intervals via bootstrapping at station level |
| Reporting | Model cards, calibration plots, failure case gallery |

## 16.4 Proposed acceptance targets for the pilot **[Design choice, to be agreed with partners]**

| Metric | Target |
|---|---|
| Median lead time for drift-type failures flagged as Warning | 72 hours or more |
| Precision@10 on the daily worklist | 0.5 or more |
| False Watch alerts | 1 or fewer per station-month |
| Calibration error (ECE) | 0.05 or lower |
| RUL interval coverage (nominal 80%) | 75-85% |
| Technician acceptance (would act on alert) | 70% or more in survey |
| Entry time per SMMS record | 50% reduction vs baseline |

---

# 17. Safety, Standards, Cybersecurity and Compliance

## 17.1 Safety stance

* NIDAN is **advisory and non-vital**. No output changes any signal aspect, route or interlocking state.
* Sensors are read-only, galvanically isolated, high-impedance and fail-open so a sensor failure cannot load or disturb the vital circuit.
* No NIDAN component is placed in the safety function chain; vital logic remains with certified interlocking. This fits the Indian Railways approach where RDPMS provides diagnostics and prediction, not control [R1][R23].

## 17.2 Standards and approvals map

| Area | Reference | Our action |
|---|---|---|
| Railway RAMS/software/safety electronics | EN 50126, EN 50128, EN 50129 are the established European railway standards for RAMS, software and safety-related electronics, and appear in predictive-maintenance literature on railway projects [R41] | Follow their good practice (traceability, verification) even for a non-vital tool; document the safety argument for non-interference |
| RDSO FRS/PCCL for RDPMS | RDPMS is now specified as **RDSO/SPN/257/2025 v2.0** (effective 31.12.2025), with standard business rules, common protocol, sensor calibration and pre-commissioning checklist [R69][R1] | Align data model and tests to the specification; seek RDSO review |
| OEM/approved-vendor rules | RDPMS tenders define the OEM either as a firm on an RDSO-approved list *or*, where no RDPMS list exists, as a manufacturer of outdoor and indoor signalling gear with **10 or more installations** with satisfactory performance, bidding directly or through an OEM authorisation letter [R60]. Current example: NWR Jaipur's RDPMS tender (SNT-Proj-JP-2024-25-01R), advertised value **₹48.29 Cr**, 24 months, over the Jaipur division's sections, procured against RDSO's RDPMS FRS (the 2021 FRS then in force, since superseded by RDSO/SPN/257/2025) [R60][R69] | Partner with an approved OEM for field deployment or enter via trial/Rail Tech route |
| CCSP | Edge/IoT devices in new RDPMS installations must comply with CCSP standards [R1] | CCSP-compatible gateway interface |
| Funding/trial route | Rail Tech Policy (adopted 26.02.2026) with 50:50 cost-sharing for prototype and trials [R4][R57] | Submit a proposal via the Rail Tech portal |
| Maintenance planning | **Rolling Block Programme** under rule 15.02(c) of the Indian Railways (Open Lines) General Rules, 1976, inserted by the Third Amendment Rules 2023 (G.S.R. 870(E), 29.11.2023): blocks planned **up to 52 weeks** ahead on a rolling basis, signal & telecom included [R68] | Scheduler respects block planning |
| Cybersecurity practice | Industrial control system security practice (e.g., IEC 62443-style) **[general practice, not retrieved here]** | Segmentation, device identity, logging |
| Personal data | India's Digital Personal Data Protection Act, 2023 **[general knowledge; confirm applicability with counsel]** | Minimise staff data; consent/notice where needed |

## 17.3 Ethical design

* **Assets, not people.** Alerts are about equipment health. The system must not be used to rank or discipline staff; this is both ethically right and essential for union and workforce acceptance (S&T staff already report heavy data-entry workload [R24]).
* **Human override always available.** Every recommendation can be rejected with a reason, which becomes a label.
* **Transparency.** Model cards, versioning and audit logs available to zone and RDSO reviewers.

---

# 18. Feasibility and Viability

## 18.1 Feasibility assessment

| Dimension | Assessment | Rating | Reasoning |
|---|---|---|---|
| **Technical** | Components are mature (streaming, GNN, survival, conformal, XAI). Hard part is *integration with Indian data* and *sensor identifiability*. Per-circuit ML works in literature [R26][R28][R29] | Medium-High | Lab bench + simulator make a credible MVP |
| **Data** | No public data; access needs partnership. Zones want AI and have RDPMS data growing [R1] | Medium (main risk) | Mitigated with T0/T1 plus pilot MoU |
| **Operational** | Advisory tool; shadow mode first; reduces paperwork | Medium-High | Respects existing procedures |
| **Regulatory** | Non-vital; but RDSO approval/trial route needed [R60][R4] | Medium | Rail Tech Policy provides a path [R4] |
| **Economic** | Retrofit cost is a tiny fraction of station EI capex (Section 22) | High | See estimates |
| **Organisational / timeline** | 4-month MVP feasible on simulation + bench; field results take longer | Medium | Plan phases (Section 21) |
| **Scalability** | Streaming load manageable (Section 13.4) | High | Standard architecture |

## 18.2 Viability (business and sustainability)

| Model | Who pays | Notes |
|---|---|---|
| **Analytics module with RDPMS OEMs** (B2B2G) | OEMs embed NIDAN intelligence in their RDPMS | Fastest path to field; aligns with CRIS unified-platform plan [R1] |
| **Direct to zone/CRIS under Rail Tech Policy** | Indian Railways (50:50 cost-share for trials) [R4] | Funding for prototype and trials; scale-up grants |
| **Metros, DFCCIL, state agencies** | Metro/freight corridor authorities | Metro operators already run centralised remote health monitoring for signalling, e.g. Delhi Metro's Magenta Line system for point machines and signals [R76][R75]; DFCCIL does S&T works [R-dfccil] |
| **International** | Rail operators with DC/AC/AF track circuits | Longer horizon; adapt to local standards |

**Moat:** (1) physics models tuned to Indian conditions; (2) labelled operational history from pilots (network effect); (3) integrations with CRIS/RDPMS/SMMS; (4) open benchmark that makes NIDAN the reference approach.

---

# 19. Challenges and Mitigations

| # | Challenge | Why it matters | Mitigation |
|---|---|---|---|
| 1 | **Data access** | Without real data, claims stay synthetic | Early MoU with a zone and an RDPMS OEM; use Rail Tech portal [R4]; lab bench |
| 2 | **Label scarcity / rare failures** | Failures are few; supervised learning struggles | Synthetic pre-training, self-supervision, survival with censoring, active learning |
| 3 | **Parameter identifiability** | Feed/relay-end data cannot separate all parameters | Effective-parameter estimation, Bayesian priors, extra tap or AF measurements |
| 4 | **False alarms and alarm fatigue** | Kills trust | Persistence rules, alert budget, conformal abstention, shadow-mode tuning |
| 5 | **Heterogeneous circuit types** (DC, AC, AF; varied lengths) | One model will not fit all | Type-specific twins; shared graph/survival layers; start with DC and AC station circuits |
| 6 | **Dual-detection and axle-counter dependence** | Axle counters replacing TCs in blocks | Scope = station yards + ingest axle-counter events [R54]; cross-modal monitor |
| 7 | **SMMS data quality** | Wrong age or cause entries | Data-trust scoring; reconciliation; pre-filled entries [R2][R24] |
| 8 | **Sensor installation permissions and power** | Relay rooms are controlled spaces | Use existing logger feeds first; partner with OEM; RDSO calibration/PCCL alignment [R1] |
| 9 | **Cybersecurity** | Critical infrastructure target | mTLS, signed data, segmentation, no write path; security audit |
| 10 | **Connectivity** | Poor backhaul at remote stations | Edge buffering; compact edge models; OFC/4G mix [R19] |
| 11 | **Seasonal and hardware drift** | Models decay | Drift monitors; per-zone recalibration; shadow retraining |
| 12 | **Workforce acceptance** | Staff fear surveillance or extra work | Assets-not-people policy; reduce paperwork; co-design with SSEs |
| 13 | **OEM resistance** | Fear of losing market | Partner model; vendor-neutral adapters; OEMs gain better analytics |
| 14 | **Certification friction** | Slow approvals | Non-vital design; trial route [R4]; documented safety argument |
| 15 | **Scope creep** | Team overreach | Stage-gated roadmap; MVP = DC/AC station circuits, subset of faults |
| 16 | **Over-claiming** | Expert credibility | Use Section 2.3 audit; state what is simulated vs. field |

---
# 20. Impact and Benefits (Who Gains, Where)

## 20.1 Stakeholder impact map

| Stakeholder | Current pain | Benefit from NIDAN | Evidence/logic |
|---|---|---|---|
| **Passengers** (6,905 million journeys in 2023-24 [R77]) | Delays from failures; punctuality index fell from 94.17 (2020) to 73.62 (2023) [R15a] | Fewer unexplained stops from false-occupied sections; more predictable service | Signal failures are named among main delay drivers [R15a][R16] |
| **Freight users and corridors** | Block-section and yard delays hit freight cycle times | Fewer yard track-circuit failures; better planning | Station yards hold the track circuits [R5]; DFC S&T works exist [R67] |
| **S&T maintainers (SSE/JE/ESM)** | Reactive firefighting; manual SMMS entry, error-prone, backlogs [R24] | Ranked worklist, reasons, pre-filled entries, fewer unnecessary walks | Design Section 11.2 (Steps J-K) |
| **Station Masters / controllers** | Unexplained occupancy faults; need to follow fallback procedures | Advance warning and clearer cause | CAG noted lack of follow-up on a track-circuit failure [R12] |
| **Zonal Railways / divisions** | Failures despite full blocks [R10]; MTBF/MTTR vary widely [R13] | Data-driven maintenance and block usage; benchmarking across divisions | [R10][R13] |
| **Railway Board, RDSO, CRIS** | Fragmented RDPMS; need standard data and unified dashboard [R1] | Reference analytics layer, open benchmark, integration | [R1] |
| **RailTel / RVNL / IRCON-type project agencies** | Deliver signalling works including RDPMS [R22] | Add-on predictive analytics for delivered projects | [R22] |
| **OEMs and startups** | Need bigger datasets and better models [R1] | Shared standards and analytics modules | [R1][R20] |
| **Safety regulators (CRS)** | Investigations find latent maintenance lapses (e.g., Balasore) [R17] | Evidence trails: drift, resets, alterations | [R17] |
| **Metro systems** | Centralised signalling monitoring is already deployed, but without physics-based prognosis [R76] | Technology transfer | [R76][R75] |
| **State governments** | Rail-dependent economies, disaster-prone regions | Higher reliability during monsoon/cyclone season | Monsoon precautions are an annual cycle [R14] |
| **Environment** | Stop-start energy waste; calendar-based part replacement | Marginally lower energy and waste (qualitative) | [Our inference] |

## 20.2 Where it helps geographically

* **All zonal railways:** every zone runs signalling and RDPMS-type monitoring at 100+ stations in total, with more planned [R1].
* **Most-benefit zones:** monsoon-, flood-, cyclone- and lightning-exposed regions (for example east coast, north-east, Kerala, Gangetic plains) where ballast and surge issues peak [R14][R2]. Choose pilot zones with both such exposure and an active RDPMS programme.
* **Outside Indian Railways:** metros and state rail projects with relay or DC/AC/AF track circuits — Delhi Metro already monitors signalling remotely from a central location [R76]; internationally, any operator using these circuit types (UK, Europe, Africa, South-East Asia) **[general, adapt per country]**.

## 20.3 An impact formula you can defend (instead of a made-up headline)

```
Annual failures avoided   = N_circuits_monitored x f_TC_failure_rate x P(pre-empted)
Delay-minutes saved       = Failures avoided x mean_delay_per_failure x trains_affected
Maintenance hours saved   = False-alarm walks avoided + faster MTTR (diagnosis hints) - extra investigation
Paperwork time saved      = Records pre-filled x (manual time - confirm time)
```

Sensitivity illustration **[Assumption, upper-bound style]:** the CAG recorded about 2,961 signal failures per year in one zone (all signalling, not only track circuits) [R10][R11]. If track circuits were, say, one quarter of them **[Assumption]** and NIDAN pre-empted 10-30% of those, that is roughly 74-222 failures per year per zone-equivalent. Only a pilot can replace these assumptions with real numbers; **present the formula and the pilot plan, not the number**.

## 20.4 Social and safety dimension

* **Fewer risky track walks.** Fewer unnecessary on-track inspections reduce exposure; the ministry reports a 66% fall in track-maintenance staff deaths since 2013-14 [R5], and further reducing exposure is aligned with that effort **[our inference]**.
* **Latent-hazard visibility.** Balasore showed how a maintenance alteration and ignored warnings can combine into tragedy [R17]; configuration-drift and reset-pattern alerts (N10) are a small step toward earlier visibility.

---

# 21. Implementation Plan

## 21.1 Phased roadmap

| Phase | Timing | Goal | Key deliverables | Exit criteria |
|---|---|---|---|---|
| **0. Alignment and verification** | Weeks 0-2 | Fix claims; secure expert input | Claims audit (Section 2.3); interviews with 2-3 SSE/Sig and one RDSO/CRIS contact; data-request letter; project one-pager for Rail Tech portal [R4] | Domain assumptions confirmed; named data contact |
| **1. Physics twin and synthetic benchmark** | Weeks 2-6 | Credible simulator + baseline detectors | Transmission-line simulator; fault injectors F1-F7, F12; trend and anomaly baselines; unit tests | Detects injected drift with lead time on synthetic data |
| **2. Data platform and dashboard MVP** | Weeks 4-10 | End-to-end pipeline on simulated network | MQTT -> Kafka -> TSDB; stream QC; geo dashboard with 30-50 circuits; replay tool | Live demo with replayed scenarios |
| **3. Intelligence stack** | Weeks 8-16 | Graph, survival, calibration, explainability | GNN risk model with ablations; Bayesian survival with frailty; conformal layer; SHAP + physics explanations; SMMS-style pre-fill | Beats baselines on synthetic benchmark; calibration targets met |
| **4. Lab bench and hardware-in-loop** | Weeks 6-16 | Physical evidence | Resistor-ladder ballast emulator, relay, sensors, gateway; fault injection; data collection | Bench data replicates twin behaviour; demo-ready |
| **5. Showcase release (MVP)** | Week 16 | Industry presentation | Demo script; 7-minute walkthrough; technical note; open NIDAN-Bench v0.1 | Expert Q&A rehearsed (Section 23) |
| **6. Shadow-mode pilot** | Months 5-10 | Real data, no operational impact | 2-3 stations at one division; read-only data feeds or isolated sensors; weekly review with SSE; labels via app | Pilot acceptance targets (Section 16.4) assessed |
| **7. Integration and standards alignment** | Months 10-18 | Fit CRIS/RDSO programme | Adapters to RDPMS OEM outputs; CCSP-compatible interface; SMMS connector; RDSO review of data model; Rail Tech co-funded trial [R4] | Data model accepted by partners; trial agreement |
| **8. Scale-out** | Months 18-36 | Multi-zone deployment | Zone-wise deployments; extension to axle counters, points, power | Uptime, adoption and KPI dashboards |

## 21.2 Sixteen-week MVP Gantt (ASCII)

```
Week            1  2  3  4  5  6  7  8  9 10 11 12 13 14 15 16
Alignment/verify##  ##
Physics + synth     ## ## ## ##
Data platform          ## ## ## ## ## ##
Intelligence                  ## ## ## ## ## ## ## ##
Lab bench                  ## ## ## ## ## ## ## ## ##
Dashboard/mobile              ## ## ## ## ## ## ##
Hardening+demo                                  ## ## ## ##
```

## 21.3 Suggested team roles (5-6 people)

| Role | Responsibilities |
|---|---|
| Domain and safety lead | Interviews, standards, safety argument, Q&A prep |
| Physics and simulation engineer | Twin, simulator, fault injectors, UKF |
| Data and streaming engineer | Kafka, TSDB, adapters, schemas |
| ML engineer (graph + survival) | GNN, Bayesian survival, conformal, explainability |
| Embedded/edge engineer | Sensors, gateway, bench rig, edge models |
| Full-stack engineer | Dashboard, mobile PWA, SMMS pre-fill |

## 21.4 Shadow-mode pilot design

1. Choose a division with an active RDPMS programme and monsoon/lightning exposure [R1][R14].
2. Select 2-3 stations (one busy yard, one small station) with data-logger access.
3. Run NIDAN in parallel; no alerts affect operations at first; weekly review with SSE.
4. Compare NIDAN alerts to OEM RDPMS alerts and to actual failures and findings.
5. Publish results against pre-registered metrics (Section 16.4).
6. Only after shadow-mode success, propose limited live alerting under zone approval.

## 21.5 Engagement and funding path

* **Rail Tech portal:** submit as a self-initiated challenge; policy provides 50:50 cost-sharing for prototype and trials and grants for extended trials or scale-up [R4][R57].
* **CRIS (SMMS and unified RDPMS):** propose NIDAN as an analytics module integrated with the planned CRIS dashboard [R1].
* **RDSO (Signal Directorate):** request review of the canonical data model and sensor-calibration approach [R1].
* **OEMs:** propose analytics partnerships (Efftronics, Bitcom, Energy7, Gadgeon, JARS, Aquasense are registered RDPMS vendors under CCSP) [R20].
* **Academic partners:** IIT/NIT labs for bench support and publications **[suggestion]**.

## 21.6 The 7-minute demonstration flow (for the showcase)

1. **(1 min)** The story: a monsoon failure; show the 60-day drift chart (Section 5.3).
2. **(1 min)** *Why now*: the Railway Board's own RDPMS minutes list the exact gaps [R1].
3. **(2 min)** Live bench: wet the "ballast box" (lower resistance); watch twin estimate ballast conductance rise and alert fire days earlier in accelerated time.
4. **(1 min)** Dashboard: graph view clusters three circuits sharing a drain; SHAP + physics explanation.
5. **(1 min)** Worklist: Rolling Block-aware plan; pre-filled SMMS entry; technician confirmation.
6. **(1 min)** The ask: data access for a shadow-mode pilot, RDSO review, Rail Tech co-funding.

---

# 22. Assumptions, Cost Estimation and Market Sizing

## 22.1 Assumptions register

| ID | Assumption | Basis | Risk if wrong |
|---|---|---|---|
| A1 | Average ~30 track circuits per circuited station (about 20 monitored per station for costing) | **[Assumption]**; varies by yard size | Cost per station changes linearly |
| A2 | Station-yard DC/AC circuits are the first scope | Track circuits remain in yards [R5][R3] | Scope narrower if AF dominate |
| A3 | Existing data-logger/RDPMS feeds can be accessed via partners | RDSO says loggers/RTUs should be IoT-capable [R55]; OEM ecosystem exists [R20] | If not, rely on added sensors |
| A4 | Non-vital advisory deployment is acceptable to zones | Principle; shadow-mode first | Longer approvals |
| A5 | Synthetic pre-training transfers partially to real data | Common sim-to-real practice | More field labels needed |
| A6 | Zones will share SMMS failure history under MoU | Zones want AI and data [R1] | Weaker labels |
| A7 | Cost figures below are order-of-magnitude, to be replaced by vendor quotes | **[Estimate]** | Budget variance |

## 22.2 Reference prices from Indian Railways documents

| Item | Value | Ref |
|---|---|---|
| EI on 2-road single-line station (includes RDPMS, data logger RTU, axle counter in parallel with DC TC, building ₹1.48 Cr) | ₹9.70 Cr per station | [R3] |
| EI on 3-road single-line | ₹11.02 Cr | [R3] |
| EI on 4-road double-line | ₹13.10 Cr | [R3] |
| EI on 5-road double-line | ₹14.48 Cr | [R3] |
| Double distant signalling | ₹70 lakh per station/location | [R3] |
| Automatic Block Signalling | ₹1.36 Cr per route-km | [R3] |
| RDPMS work order (NWR sections, 24 months) | ₹51.61 Cr (IRCON) | [R22] |
| EI replacement approved on Eastern Railway (32 stations) | ₹405 Cr | [R58] |

## 22.3 Our retrofit cost model per station **[Estimate]**

| Item | Low (₹ lakh) | High (₹ lakh) | Note |
|---|---|---|---|
| Edge gateway (rugged) | 0.6 | 1.2 | One per relay room |
| Sensing front-ends (20 circuits x ₹4k-10k) | 0.8 | 2.0 | Isolated V/I taps |
| Installation, commissioning, approvals, training | 0.5 | 1.5 | Zone dependent |
| **Capex per station** | **1.9** | **4.7** | Compared with EI station capex of ₹9.7-14.5 Cr [R3], that is about **0.1% to 0.5%** |
| Software, cloud, support per station-year | 0.3 | 0.8 | Ongoing |

If existing data-logger/RDPMS feeds suffice, the hardware line shrinks; software integration dominates.

## 22.4 Programme budgets **[Estimate]**

| Stage | Scope | Indicative cost |
|---|---|---|
| MVP (16 weeks) excluding salaries | Bench hardware ₹0.6-1.5 L; cloud/GPU ₹0.3-0.8 L; travel and expert meetings ₹0.3-0.6 L | **₹1.2-2.9 L** |
| Shadow pilot (3 stations, 6 months) | Hardware ₹5.7-14.1 L plus engineering effort | ₹6-15 L hardware + people |
| 20-station extended trial | Capex ₹0.38-0.94 Cr; ops ₹0.06-0.16 Cr/yr | Co-fundable via Rail Tech [R4] |

## 22.5 India-only market sizing for track-circuit yard analytics **[Estimate]**

| Scenario | Stations | Capex (₹ Cr) | Ops per year (₹ Cr) |
|---|---|---|---|
| Pilot | 20 | 0.4-0.9 | 0.06-0.16 |
| Division | 150 | 2.9-7.1 | 0.45-1.2 |
| All circuited stations | 6,665 [R5] | **127-313** | **20-53** |
| 5-year total (capex + 5 years ops), all stations | 6,665 | **about 227-580** | n/a |

**Reality check on "₹2000Cr+".** The ₹2,000 crore figure came from the original problem sheet and cannot be reproduced from public numbers; NIDAN does not repeat it. Bottom-up, India-only track-circuit-yard analytics is **₹127–313 Cr capex plus ₹20–53 Cr/yr opex**, i.e. **about ₹227–580 Cr over five years** (table above). A four-digit-crore figure is plausible only if scope expands to points, axle counters, power supplies and cables; metros and DFC; and international markets; or over a longer horizon. **Present it as a staged opportunity, not a headline.** If an examiner asks where ₹2,000 crore came from, the honest answer is: *"it was an unsourced claim in the brief; here is the bottom-up number instead."*

## 22.6 Revenue and sustainability **[Estimate]**

* Price band for analytics subscription: roughly ₹0.6-1.5 lakh per station-year (above the ₹0.3-0.8 lakh cost band).
* At 1,000 stations: about ₹6-15 Cr per year revenue.
* Additional revenue: integration fees, OEM licensing, training, metro/other projects.

---

# 23. Expert Q&A Preparation and Showcase Strategy

## 23.1 Likely expert questions and strong answers

| # | Question | Suggested answer |
|---|---|---|
| 1 | "Isn't RDPMS already doing this?" | RDPMS exists at 100+ stations with OEM-defined rules; Railway Board's own minutes say rules differ, datasets are small and a unified application is still to come [R1]. We build the analytics layer that sits on those feeds. |
| 2 | "Is your system vital? Can it affect signals?" | No. Advisory only, read-only isolated taps or existing logger data, no write path to vital systems (Section 17.1). |
| 3 | "Track circuits are being replaced by axle counters." | In yards, track circuiting is at 6,665 stations and new EI designs even put axle counters in parallel with DC track circuits [R5][R3]. We also monitor dual-detection consistency and can ingest axle-counter health [R54]. |
| 4 | "Failures don't propagate electrically between circuits." | Correct, and we model *common causes, shared infrastructure, dependencies and maintenance-induced effects*, which is why the graph has four edge types (Section 3.5). |
| 5 | "What data do you have? It's synthetic." | Yes for now: physics simulator and lab bench. That is why we propose a shadow-mode pilot and have an explicit data request (Section 15.3). Synthetic is for pre-training and demonstration, not claimed field accuracy. |
| 6 | "How do you avoid false alarms?" | Persistence rules, alert budgets, conformal abstention, and tuning in shadow mode (Section 11.3). |
| 7 | "How is this different from published deep-learning papers?" | They do per-circuit classification on specific technologies [R26][R28][R29]. We add physics twin, network/common-cause graph, survival prognosis with uncertainty, dual-detection monitoring and Indian integration. |
| 8 | "What about cybersecurity?" | mTLS, signed messages, segmentation, one-way data flow from field, CCSP-compatible edge, security audit [R1]. |
| 9 | "Who owns the data?" | Indian Railways. Hosting on CRIS/Indian infrastructure; role-based access; our benchmark uses synthetic/anonymised data only. |
| 10 | "Why GNN and not simpler models?" | We test against no-graph and Hawkes baselines; if GNN doesn't win, we keep the simpler model (Section 16.2). |
| 11 | "How do you handle different circuit types?" | Type-specific twins feeding shared graph/survival layers; start with DC/AC station circuits (Section 19 #5). |
| 12 | "What about staff acceptance?" | Assets-not-people policy; pre-filled SMMS entries cut workload [R24]; co-design with SSEs. |
| 13 | "How will you get approvals?" | Non-vital design, shadow pilot, OEM partnership, Rail Tech Policy route [R4][R60]. |
| 14 | "What is your real accuracy?" | State plainly: simulated/bench results now; field metrics after pilot. Cite acceptance targets (Section 16.4). Never quote 99% as expected field accuracy. |
| 15 | "Is ₹2000 crore realistic?" | No, and we no longer claim it. India-only yard analytics sizes to ₹127–313 Cr capex and ₹20–53 Cr/yr opex, about ₹227–580 Cr over five years; growth comes from adjacent assets, metros and exports (Section 22.5). |
| 16 | "What is novel?" | The integrated combination (Section 10) and the masked-failure monitor, SMMS auto-fill, and open benchmark. |

## 23.2 The 60-second pitch

*"Indian Railways keeps trains safe with track circuits, but their health decays silently, especially in the monsoon, and failures are investigated one by one. In January 2025 the Railway Board wrote down the problem: about a hundred stations run remote diagnostics using different vendor rules, with too little data for AI and no unified view. We built NIDAN — Hindi and Sanskrit for diagnosis, the act of finding the root cause — a safe, advisory-only intelligence layer: a physics twin of each circuit, a graph that finds shared root causes, survival models that say how many days remain, and explanations a maintainer can trust. It pre-fills the paperwork and plans around Rolling Block windows. We have a simulator, a lab bench and a plan for a shadow-mode pilot. We're asking for one zone's data and an RDSO review."*

## 23.3 Do and don't for the showcase

| Do | Don't |
|---|---|
| Lead with the Railway Board RDPMS minutes [R1] | Say "nothing exists" |
| Say "correlated and cascading risk" | Say "failures propagate for kilometres" |
| Show bench + simulator and label them as such | Quote 99% accuracy as field performance |
| Mention Rail Tech Policy path [R4] | Cite the unverified papers from the original sheet |
| Show the formula for impact and a sensitivity range | State ₹2000 Cr as fact |
| Emphasise assets-not-people and advisory-only | Claim safety certification |

---
# 24. References (with Links)

## 24.1 How to read this section (honesty legend)

Every `[Rxx]` tag used in Sections 1-23 resolves to a row below. Because the original research session ran out of credit before this section was written, the links were **re-resolved in a second session** from the research trail (the source list inside the chat export) plus fresh searches. Each row carries a status so you know how far to trust the mapping:

| Status | Meaning |
|---|---|
| **O** | Page was opened and read, in the original research session (visible in the chat export) or re-opened in the second session |
| **L** | Link found by search; title and publisher match the claim it supports; page not re-opened to re-read the exact sentence |
| **T** | **Tentative**: best candidate found; confirm it supports the exact claim before quoting it on a slide |
| **N** | Not recovered; instructions for finding it are given |

Tags R6–R9, R63, R65 and R66 are deliberately **not used** in v1.1: the EI-count series was replaced by two verified points (R77, R5), the ₹147.3 lakh metro-tender claim was dropped in favour of Delhi Metro's own presentation (R75, R76), and R65/R66 were never used. `[R-ELD]` in Section 4 (P11) means the same source as **R55**. `[R-SMMS]`, `[R-dfccil]` and `[R49-related]` are listed at the end of their tables.

## 24.2 Indian Railways, Government of India and audit sources

| Tag | What it supports | Link | Status |
|---|---|---|---|
| **R1** | Railway Board minutes, meeting of 31.01.2025 on RDPMS implementation (100+ stations, OEM rules, CCSP, unified dashboard, sensor calibration, bigger datasets for AI/ML) | [ecr.indianrailways.gov.in: RB Minutes 31.01.25 RDPMS](https://ecr.indianrailways.gov.in/cris//uploads/files/1744352589344-RB%20Minutes%20of%20Meeting%20held%20on%2031.01.25%20regarding%20RDPMS%20implementation..pdf) | **O** |
| **R2** | Minutes of Signal Incidences VC held on 15.04.2025 (incidents 08.03.2025 to 11.04.2025): iron liners, Chainwa relay, lightning at a station on 23.03.25, MSDAC resets, SMMS data accuracy | [ecr.indianrailways.gov.in: MoM Signal Incidences 15.04.2025](https://ecr.indianrailways.gov.in/cris//uploads/files/1745497028153-MoM%20of%20Signal%20Incidences%20VC,%20held%20on%2015.04.2025%20%28Signal%20Incidences%2008.03.2025%20to%2011.04.25%29.pdf). Related: [AM Signal meeting with PCSTEs/CSEs, 24.03.25](https://ecr.indianrailways.gov.in/cris//uploads/files/1743502565530-RB-Minutes%20of%20Meeting%20held%20by%20AM%20Signal%20with%20PCSTEs%20&%20CSEs%20through%20VC%20on%2024.03.25.pdf) | **L** |
| **R3** | Railway Board GATI-SHAKTI "Typical Abstract Estimate" (EI station costs, axle counters in parallel with DC track circuits, ABS per route-km) | [indianrailways.gov.in: Typical Abstract Estimate 31.12.2024](https://indianrailways.gov.in/railwayboard/uploads/directorate/GATISHAKTI/2024/Typical%20Abstract%20Estimate%2031_12_2024.pdf) | **O** |
| **R4** | Ministry of Railways / PIB release on AI/ML devices (ITMS, WILD, OMRS, MVIS, drones) and the Rail Tech Policy | [PIB PRID=2238772](https://pib.gov.in/PressReleasePage.aspx?PRID=2238772) | **O** |
| **R5** | Ministry reply in Rajya Sabha (as reported by ANI): 6,660 EI stations; 6,665 stations with complete track circuiting; 6,142 BPAC block sections; 6,625 ABS route-km; 10,097 interlocked gates; about 58% fall in signalling failures in 11 years; 66% fall in track-maintenance staff deaths (from 196 in 2013-14) | [NewKerala/ANI: "Indian Railways safety measures yield results, 58% drop"](https://www.newkerala.com/news/a/indian-railways-safety-measures-yield-results-58-drop-312.htm). Other coverage: [Lokmat Times](https://www.lokmattimes.com/national/indian-railways-safety-measures-yield-results-58-drop-in-signalling-failures-contribute-to-sharp-decline-in-accidents/amp), [Odisha TV](https://odishatv.in/national/indian-railways-safety-drive-shows-major-gains-accidents-signalling-failures-and-staff-deaths-decline-sharply-11083856), [Free Press Journal](https://www.freepressjournal.in/mumbai/railway-staff-deaths-in-track-work-drop-66-due-to-enhanced-safety-tech-upgrades-union-minister-ashwini-vaishnaw) | **O** (figures re-checked). Rolling Block / 52-week statements now cite **R68**, not this row |
| **R10** | CAG Report No. 24 of 2025 (South Western Railway signalling: failures, maintenance blocks, cable cuts, SMMS intent) | [CAG press brief](https://cag.gov.in/uploads/PressRelease/PR-Press-Brief-Report-No-24-of-2025-English-06944f30a469df2-13334022.pdf); [full report](https://cag.gov.in/uploads/download_audit_report/2025/Report-No.-24-of-2025,-Union-Government,-Railway(English)-06a2ba6801a50f4.83964134.pdf) | **L** |
| **R11** | 14,808 failures / average 2,961 per year in SWR (2018-19 to 2022-23); "Miscellaneous" category 2,343 | [Deccan Herald](https://www.deccanherald.com/india/nearly-3000-incidents-of-signal-failures-in-south-western-railways-per-year-cag-3837126); [OneIndia](https://www.oneindia.com/india/signal-failures-south-western-railway-cag-report-011-7945728.html); [Devdiscourse](https://www.devdiscourse.com/article/business/3735355-cag-report-reveals-alarming-signal-failures-in-south-western-railway) | **L** |
| **R12** | CAG Report No. 45 of 2018 (Union Government – Railways), Para 2.2.1.5: dual detection (track circuit + axle counter) clears the signal if either shows clear; operation instructions did not require the Station Master to investigate a track-circuit failure; at Rura (NCR) a DC track-circuit failure at **02:16:47 on 28.12.2016** was not followed up and the Sealdah–Ajmer Express (12987) derailed at 05:30, over 50 injured, probable rail fracture; CAG recommended using track-circuit drop as a rail-fracture prompt. Also documents 16 accidents from deficient track maintenance (2014-15 to 2016-17) | [CAG Report No. 45 of 2018, full PDF](https://cag.gov.in/webroot/uploads/download_audit_report/2017/Report_No.45_of_2018_%E2%80%93_Compliance_Audit_on_Maintenance_of_track_on_heavy_traffic_sections_over_India.pdf); [executive summary](https://cag.gov.in/uploads/download_audit_report/2018/Executive_Summary_of_Report_No.45_of_2018_%E2%80%93_Compliance_Audit_on_Maintenance_of_track_on_heavy_traffi.pdf) | **O** (text re-read and quoted in this revision) |
| **R13** | CAG finding that MTBF/MTTR of S&T equipment varied widely across zones (2013) | [CAG Compliance Audit, Railways, Report 11 of 2013, Chapter 3](https://cag.gov.in/webroot/uploads/download_audit_report/2013/Union_Compliance_Railway_11_2013_chap_3.pdf) | **T** |
| **R14** | Railway Board Summer and Monsoon Precautions (signalling): ballast clearance 50 mm below rail foot, 100% insulated GFN liners and rubber pads, IPS backup checks | [Signal Directorate: Summer & Monsoon (11.03.2024)](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2024/Summer%20%26%20Monsoon%20110324.pdf); [Precautionary measures (11.03.2024)](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2024/Precautionary%20measures%20110324.pdf) | **T** (check which of the two carries the 50 mm / GFN wording) |
| **R15a** | Punctuality index 94.17 (2020) to 73.62 (2023), per Railway Board data cited by IndiaSpend | [Scroll (IndiaSpend): "Reliant on British-era infrastructure"](https://scroll.in/article/1088973/reliant-on-british-era-infrastructure-the-indian-railways-is-strained-beyond-capacity); [Moneylife reprint](https://www.moneylife.in/article/indian-railways-are-under-strain-whats-burdening-them/78854.html); [The News Minute reprint](https://www.thenewsminute.com/news/behind-every-delay-the-infrastructure-crisis-crippling-indian-railways-2) | **L** |
| **R15b** | Broad gauge **99.2% electrified: 69,427 of 70,001 BG route-km** (November 2025) | [PIB Backgrounder PRID=2211852](https://pib.gov.in/PressReleasePage.aspx?PRID=2211852); corroborated by [PIB PRID=2203715](https://www.pib.gov.in/PressReleasePage.aspx?PRID=2203715&reg=3&lang=2) (99.2%, 14 Dec 2025) | **O** (figures re-checked in this revision). Passenger and station counts moved to **R77** |
| **R16** | Railway Board warning to all zones (Sep 2025) on repeated signal failures and damaged signal cables | [Deccan Herald](https://www.deccanherald.com/india/damaged-signal-cables-could-lead-to-catastrophic-consequences-railways-to-all-zones-3731312); [The Week](https://www.theweek.in/wire-updates/national/2025/09/17/des123-rail-signal-safety.html); [Railway Board letter on cable-cut failures](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2025/Signal%20failure%20due%20to%20frequent%20cable%20cut%20damages%20along%20the%20track.pdf); [Ensuring Safety of Signalling System](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2025/Ensuring%20Safety%20of%20Signalling%20System.pdf) | **L** |
| **R16b** | Maintenance "directly linked" to asset failures contributing an average 22.2% of punctuality loss in 2018 | Candidate: same punctuality coverage as R15a ([Scroll](https://scroll.in/article/1088973/reliant-on-british-era-infrastructure-the-indian-railways-is-strained-beyond-capacity), [Newslaundry](https://www.newslaundry.com/2025/11/24/130-kmph-tracks-55-kmph-speed-why-are-indian-trains-still-this-slow-despite-mission-raftaar)) | **T** |
| **R17** | CRS inquiry into the Balasore (Bahanaga) accident: lapses at multiple levels, wrong signalling after circuit alteration, earlier red flags | [ThePrint](https://theprint.in/india/odisha-train-accident-inquiry-finds-multi-level-lapses-says-reporting-past-red-flags-could-have-averted-tragedy/1653092); [Business Standard](https://business-standard.com/india-news/lapses-at-multiple-levels-what-led-to-balasore-train-accident-on-june-2-123070400138_1.html); [Moneylife](https://www.moneylife.in/article/balasore-train-accident-commissioner-of-rail-safety-finds-lapses-at-multiple-levels-in-st-dept-signalling-circuit-alteration/71276.html); [The Wire](https://thewire.in/government/commissioner-of-railway-safety-signaling-operations-staff-balasore-tragedy) | **L** |
| **R18** | 13 consequential events attributed to signalling failures in five years (reply of July 2023) | [Rajya Sabha PQ 260, 21.07.2023, U307](https://rsdebate.nic.in/bitstream/123456789/741278/1/PQ_260_21072023_U307_p409_p410.pdf); coverage: [Orissa Post](https://www.orissapost.com/13-cases-of-signalling-failure-in-five-years-no-incident-due-to-defects-in-interlocking-signal-system-rail-minister/amp/) | **L** |
| **R19** | Kavach: RFID tags, towers, OFC, loco equipment; version 4.0 interface to existing EI | [PIB PRID=2112824](https://pib.gov.in/PressReleasePage.aspx?PRID=2112824); [Business Today on Kavach 4.0](https://www.businesstoday.in/amp/india/story/indian-railways-activates-kavach-40-on-key-route-targets-pan-india-rollout-in-six-years-full-details-487082-2025-07-30) | **T** |
| **R20** | C-DOT Common Service Platform verticals incl. RDSO-RDPMS vendors and IR-NIYANTRAC | [C-DOT CCSP verticals](https://cdot.in/cdotweb/web/ccsp_verticals.php) | **L** |
| **R21** | Efftronics: IoT/data loggers, RDPMS plan for about 600 Southern Railway stations, 20-30 ms sampling (company claim) | [Efftronics Expands IoT Solutions For Indian Railways](https://letsdatascience.com/news/efftronics-expands-iot-solutions-for-indian-railways-9d68eb93) | **L** |
| **R22** | IRCON: Rs 51.61 crore RDPMS work order from North Western Railway, 24 months | [Indian Masterminds](https://indianmasterminds.com/news/ircon-secures-rs-51-61-crore-railway-order-for-predictive-maintenance-system-117864/); [MarketScreener](https://in.marketscreener.com/quote/stock/IRCON-INTERNATIONAL-LIMIT-64310764/news/North-Western-Railway-Receives-Letter-of-Acceptance-from-North-Western-Railway-50001554/) | **O** |
| **R23** | Western Railway RDPMS at Atul station: probable-cause diagnosis, alerts "based on the system learning" | [Rail Analysis: WR commissions RDPMS at Atul](https://news.railanalysis.com/western-railway-commissions-remote-diagnostic-predictive-maintenance-system-at-atul-station/) | **L** |
| **R24** | SMMS at Western Railway: 3,01,650 assets, about 30,000 daily entries, cumbersome/error-prone entry | [Devdiscourse: Streamlining Signals](https://www.devdiscourse.com/article/business/3546255-streamlining-signals-western-railways-digital-leap); [Tablets for signal staff](https://english.metrovaartha.com/amp/story/news/national/provide-tablet-computers-to-signal-staff-for-faster-failure-analysis-western-railway-to-divisions); [The Week](https://www.theweek.in/wire-updates/national/2025/08/19/des49-rail-signal-staff-tablet.html) | **L** |
| **R25** | 2017 announcement: remote condition monitoring of signalling gear with non-intrusive sensors, predictive analytics, pilots on Ahmedabad-Vadodara and Bengaluru-Mysuru | [YourStory](https://yourstory.com/2017/11/railways-use-artificial-intelligence-preventing-signal-failures); [The Quint](https://www.thequint.com/news/india/train-accidents-prevention-artificial-intelligence-india); [The News Minute](https://www.thenewsminute.com/news/indian-railways-use-artificial-intelligence-prevent-signal-failures-71945); [The Better India](https://www.thebetterindia.com/122122/railways-signals-ai/) | **L** |
| **R53** | RDSO specification for AC-immune biased track relays | [RDSO SPN 84 Ver 2 Amdt 1](https://rdso.indianrailways.gov.in/uploads/spn_84_ver%202%20Amdt%201.pdf) | **T** (confirm SPN 84 is the AC-immune relay specification) |
| **R54** | Axle counters / BPAC and their role in block sections | [RDSO IRS S-105/2025 BPAC specification](https://rdso.indianrailways.gov.in/uploads/2025-07-30-Finalized%20copy%20of%20specification%20IRS_S-105_2025%20for%20%20BPAC%20using%20UFSBI-30072025.pdf); [Railway Board: Train Detection, Track Circuits & Axle Counters](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2023/17-Train%20Detection%20-%20Track%20Circuits%20&%20Axle%20Counters.pdf) | **L** |
| **R55** | RDSO: data loggers and RTUs to be IoT-capable and usable for RDPMS (also the source behind `[R-ELD]`) | [RDSO data logger specification](https://rdso.indianrailways.gov.in/uploads/files/Datalogger%20Spec%20uploaded%20on%20RDSO%20Website.pdf); [RDSO reasoned document](https://rdso.indianrailways.gov.in/uploads/files/Reasoned%20Document%20uploaded%20on%20RDSO%20Website.pdf) | **T** |
| **R56** | CCSP (oneM2M-based) platform | [C-DOT CCSP verticals](https://cdot.in/cdotweb/web/ccsp_verticals.php); [CCSP FAQ](https://ccspweb.railsaver.gov.in/docs/FAQ.html); [CCSP oneM2M presentation](https://tsdsi.in/wp-content/uploads/2024/12/CDOT_Presentation-CCSP_oneM2M-Stakeholder-1.pdf) | **L** |
| **R57** | Rail Tech Policy (launched 26.02.2026): portal, 50% funding of technology development | [All India Radio](https://www.newsonair.gov.in/union-minister-ashwini-vaishnaw-unveils-rail-tech-policy-portal-and-e-railway-claims-tribunal); [Business Standard](https://www.business-standard.com/india-news/railways-rail-tech-portal-govt-to-fund-50pc-tech-development-126022601354_1.html); [Inc42](https://inc42.com/buzz/railways-unveils-tech-policy-to-foster-startup-led-innovation/); [PIB PRID=2238772](https://pib.gov.in/PressReleasePage.aspx?PRID=2238772) | **L** |
| **R58** | Rs 405 crore signalling upgrade, 32 Eastern Railway stations | [All India Radio](https://newsonair.gov.in/indian-railways-approves-%E2%82%B9405-crore-to-modernise-signalling-project-on-eastern-railway/); [NBM&CW](https://www.nbmcw.com/news/metro-railways/indian-railways-approves-rs-405-crore-signalling-upgrade-at-32-eastern-railway-stations.html) | **L** |
| **R59** | Ministry claim: train accidents down **about 88% since 2014-15** (baseline 135 accidents) | [NBM&CW](https://www.nbmcw.com/news/metro-railways/rail-accidents-down-88-since-2014-15-as-safety-spending-kavach-deployment-gather-pace.html); [Business Today](https://www.businesstoday.in/latest/trends/photo/indian-railways-cut-train-accidents-by-88-in-12-years-heres-exactly-how-it-was-done-546267-2026-07-30); [All India Radio](https://www.newsonair.gov.in/train-accidents-in-india-drastically-reduced-by-89-railways-minister-ashwini-vaishnaw/) (says 89%) | **O** for the percentage; end-year counts differ between outlets (10/11/16), so the dossier quotes the percentage only |
| **R60** | RDPMS tender eligibility: where no RDSO list of RDPMS vendors exists, an OEM is a manufacturer of outdoor/indoor signalling gear with **10 or more installations** of satisfactory performance, bidding directly or with an OEM authorisation letter; tender scope, 24-month period, advertised value | North Western Railway (Jaipur division) tender **SNT-Proj-JP-2024-25-01R**, closing 04.10.2024, advertised value **₹48,29,45,751.13 (₹48.29 Cr)**, 24 months, RDPMS over AII–BKN, MTD–LUNI, RE–BTI, RE–MD, JP and MD–PNU sections: [tender document](https://www.tenderfiles.com/tenderdocuments/92024/14/4b3eda8e-01a0-421e-9c43-4f07d7485ab1?FileName=4b3eda8e-01a0-421e-9c43-4f07d7485ab1.pdf). Specification now [RDSO/SPN/257/2025 v2.0](https://www.tenderfiles.com/tenderdocuments/72026/16/13ad1581-dc1f-4537-bceb-30e3715f4e80?FileName=IRSRDSOlatestspecificationdetailsdt15-07-2026.pdf) [R69] | **O** (NIT header and eligibility clause read). Supersedes the old "definition of similar nature" letters |
| **R67** | DFCCIL signalling and telecom (S&T) works | [DFCCIL tender: S&T financial bid](https://dfccil.com/upload/FinancialBid_DFCC_AII_S&T_NewMadar_R_8JI6.pdf); [DFCCIL tender document](https://dfccil.com/upload/Tender_Document_37_EXJB.pdf) | **L** |
| **R68** | Rolling Block Programme: blocks planned on a rolling basis up to **52 weeks** ahead, covering signal and telecom assets | Indian Railways (Open Lines) General Rules, 1976, **rule 15.02(c)** as inserted by the **Indian Railways (Open Lines) General (Third Amendment) Rules, 2023**, G.S.R. 870(E), 29.11.2023 ([Gazette notification](https://gazettetracker.com/g/CG-DL-E-30112023-250327)); background: [PIB PRID=2115515](https://pib.gov.in/PressReleasePage.aspx?PRID=2115515) | **O** (rule text read) |
| **R69** | **RDSO/SPN/257/2025 Version 2.0**, "Remote Diagnostic and Predictive Maintenance System (RDPMS)", effective 31.12.2025: standard business rules, common protocol, sensor calibration, pre-commissioning checklist. Tenders issued from Dec 2025 specify compliance (e.g. NCR Prayagraj `NCRPU-ALJN-RDPMS-T-06`, SCR Guntakal `01-SNT-01-2026`) | [RDSO specifications portal](https://rdso.indianrailways.gov.in/) → Specifications → Signal → SN 44; [RDSO signal specification list, 15.07.2026](https://www.tenderfiles.com/tenderdocuments/72026/16/13ad1581-dc1f-4537-bceb-30e3715f4e80?FileName=IRSRDSOlatestspecificationdetailsdt15-07-2026.pdf) | **L** (listing, title and effective date read; open the PDF before quoting a clause number) |
| **R73** | Prescribed track-circuit maintenance periodicity: technician fortnightly/monthly checks, sectional JE monthly, SSE quarterly, joint S&T–P.Way inspection half-yearly, quarterly train-shunt tests, six-monthly test-card readings | [CAMTECH: DC Track Circuit Maintenance, CAMTECH/S&T/S/2009/P/DCTC/2.0](https://rb.indianrailways.gov.in/uploads/directorate/eff_res/camtech/S&T%20Engineering/YearWise/Pamphlet%20on%20DC%20Track%20Circuit%20maintenance%20ver2.pdf) | **O** (pamphlet read) |
| **R74** | Signal Inspectors must inspect and test equipment at intervals not exceeding one month | Indian Railways Signal Engineering Manual (SEM), inspection schedule chapter; corroborated by [CAMTECH pamphlet R73](https://rb.indianrailways.gov.in/uploads/directorate/eff_res/camtech/S&T%20Engineering/YearWise/Pamphlet%20on%20DC%20Track%20Circuit%20maintenance%20ver2.pdf) | **T** (SEM clause number to be confirmed) |
| **R77** | **Indian Railways Year Book 2023-24**: 6,905 million passengers originating, 7,461 railway stations, 69,181 route-km (all gauges) as at 31 March 2024, 66,820 BG route-km | [Indian Railways Year Book 2023-24 (English PDF)](https://rb.indianrailways.gov.in/uploads/directorate/stat_econ/2025/IR%20Year%20Book%202023-24-English.pdf) | **O** (Key Statistics table read) |
| **R78** | At least one Indian OEM has commissioned RDPMS indigenously | Company/zone announcement of an indigenous RDPMS commissioning (Efftronics / IRCON / zone RDPMS commissioning reports; see R21–R23) | **T** (confirm the specific commissioning before naming it) |
| **R-SMMS** | Railway Board directions on SMMS correctness and morning failure conferences | [AM Signal meeting 24.03.25](https://ecr.indianrailways.gov.in/cris//uploads/files/1743502565530-RB-Minutes%20of%20Meeting%20held%20by%20AM%20Signal%20with%20PCSTEs%20&%20CSEs%20through%20VC%20on%2024.03.25.pdf); [Ensuring Safety of Signalling System](https://indianrailways.gov.in/railwayboard/uploads/directorate/signal/2025/Ensuring%20Safety%20of%20Signalling%20System.pdf) | **T** |
| **R-dfccil** | Same as R67 | See R67 | **L** |

## 24.3 Scientific, technical, vendor and open-source sources

| Tag | What it supports | Link | Status |
|---|---|---|---|
| **R26** | Alstom, CVCM track circuits, deep learning + conformal prediction (99.31%, 10 anomaly classes) | [arXiv 2508.09054](https://arxiv.org/abs/2508.09054v1) | **L** |
| **R27** | Alstom, STDS track circuit data analytics (SVM, component identification) | [arXiv 2508.11693](https://arxiv.org/pdf/2508.11693) | **L** |
| **R28** | de Bruin et al., track circuit fault diagnosis using recurrent neural networks (IEEE TNNLS) | [TU Delft repository](https://repository.tudelft.nl/record/uuid:fbc6c15e-01a8-403e-b3a8-c3578fcffb97); [TU Delft PDF](https://pure.tudelft.nl/ws/files/11547393/TNNLS_2016_P_6261.pdf); [PubMed 27116755](https://www.pubmed.gov/27116755/) | **L** |
| **R29** | Tao et al., multi-scale attention network (MSAN) for track circuit fault diagnosis, Scientific Reports 2024 | [PMC11024151](https://pmc.ncbi.nlm.nih.gov/articles/PMC11024151) | **L** |
| **R30** | Swedish research on DC track-circuit failure modes (ballast, insulated joints, rail break, no-fault-found) | [Trafikverket: Dependability issues of Track Circuits, a hybrid approach](https://fudinfo.trafikverket.se/fudinfoexternwebb/Publikationer/Publikationer_002001_002100/Publikation_002047/Dependability_issues_of_Track_Circuits_A_hybrid_approach.pdf) | **T** |
| **R31** | US FRA studies on track circuit shunting, contamination and low axle loads | [FRA: Track Circuit Shunt](https://railroads.dot.gov/sites/fra.dot.gov/files/2021-07/Track%20Circuit%20Shunt-A.pdf); [FRA: Track circuit shunting performance study](https://railroads.dot.gov/elibrary/track-circuit-shunting-performance-study) | **L** |
| **R32** | Survival models with left/right censoring for track-circuit life expectancy (Czech data, IEEE) | [IEEE Xplore 8009937](https://ieeexplore.ieee.org/document/8009937/figures); [dblp entry NovakDBKK17](https://dblp1.uni-trier.de/rec/conf/qrs/NovakDBKK17.html) | **T** |
| **R33** | Zeng et al., deep Bayesian survival analysis of rail useful lifetime (BNN-Surv, C-index 0.80) | [TU Delft repository](https://repository.tudelft.nl/record/uuid:80afdb88-bda1-4613-90e2-42a7113acb76); [Southampton ePrints](https://eprints.soton.ac.uk/505896) | **L** |
| **R34** | Weibull versus constant failure rate for electronic railway signalling (Safety, 2018) | [MDPI Safety 4(2):17](https://www.mdpi.com/2313-576x/4/2/17); [DOAJ record](https://doaj.org/article/c9229c90d0084e57b8fe093bea19e1e2) | **L** |
| **R35** | Graph attention network for railway delay propagation: Huang, Guo, Liu & Corman (2024), *Transportation Research Part E* 184:103457, calibrated on Dutch network data, attention weights used to explain where delay concentrates | [IDEAS/RePEc record and abstract](https://ideas.repec.org/a/eee/transe/v184y2024ics1366554524000474.html) | **O** (abstract read) |
| **R36** | HetGNN: railway network delay evolution (heterogeneous graph neural network) | [DTU Orbit](https://orbit.dtu.dk/en/publications/railway-network-delay-evolution-a-heterogeneous-graph-neural-netw/); [IDEAS/RePEc](https://ideas.repec.org/a/eee/transe/v184y2024ics1366554524000474.html) | **L** |
| **R37** | RSTGCN: railway-centric spatio-temporal GCN for train delay prediction (Indian network) | [arXiv 2510.01262](https://arxiv.org/pdf/2510.01262) | **L** |
| **R38** | Railway delay prediction with spatial-temporal graph convolutional networks (IEEE ITSC 2020) | [Unpaywall: 10.1109/ITSC45102.2020.9294742](https://unpaywall.org/10.1109%2FITSC45102.2020.9294742) | **L** |
| **R39** | Predicting cascade failures in interdependent urban infrastructure networks | [arXiv 2503.02890](https://arxiv.org/pdf/2503.02890) | **L** |
| **R40** | Systematic review of AI public datasets for railway applications (Infrastructures 2021) | [doi 10.3390/infrastructures6100136](https://dx.doi.org/10.3390/infrastructures6100136); [MDPI](https://mdpi.com/2412-3811/6/10/136) | **L** |
| **R41** | MetroPT predictive-maintenance benchmark (Porto metro compressor) | [arXiv 2207.05466](https://arxiv.org/abs/2207.05466v3); [UCI MetroPT-3](https://archive.ics.uci.edu/dataset/791); [PMC9747912](https://pmc.ncbi.nlm.nih.gov/articles/PMC9747912) | **L** |
| **R42** | Overview of publicly available degradation datasets for PHM tasks | Candidate: [arXiv 2403.13694](https://arxiv.org/pdf/2403.13694v2) | **T** |
| **R43** | Transmission-line frequency response with unevenly distributed properties, applied to railway safety monitoring | [arXiv 2012.09247](https://arxiv.org/pdf/2012.09247); [NSF PAR](https://par.nsf.gov/biblio/10431459) | **L** |
| **R44** | Transmission-line track-circuit simulation (transient response of a jointless track circuit) | Candidate: [PMC9078798, ZPW-2000A transient response](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9078798/) | **T** |
| **R45** | Siemens Mobility Railigent X | [Siemens developer portal](https://developer.siemens.com/railigent-x/overview.html) | **L** |
| **R46** | Alstom HealthHub | [Alstom: HealthHub](https://www.alstom.com/stories/future-services-digital-healthhub); [Alstom digital railway solutions](https://www.alstom.com/solutions/services/digital-railway-solutions-unlock-higher-asset-availability-reliability-and-performance) | **L** |
| **R47** | Thales TIRIS smart maintenance | [Thales TIRIS](https://www.thalesgroup.com/en/tiris-smart-maintenance) | **L** |
| **R48** | Hitachi Rail on-board condition monitoring on Indian LHB smart coaches | [Hitachi India: Smart Railways](https://www.hitachi.com/en-in/insights/articles/smart-railways/) | **T** (confirm the 100 coaches / 8,600 km figures) |
| **R49** | Railway simulation and exchange formats (OSRD, SUMO-rail, railML, OpenTrack) | [OSRD on GitHub](https://github.com/OpenRailAssociation/osrd); [SUMO railways](https://sumo.dlr.de/docs/Tools/Railways.html); [railML and SUMO](https://www.railml.org/en/software/sumo); [OSRD + SUMO workflow (FOSDEM)](https://fosdem.org/schedule/event/RV3KS9-railway-analysis-workflow-osrd-sumo). OpenTrack: product site not re-located | **L** (OpenTrack **N**) |
| **R50** | IRICEN-style handbook excerpt: minimum ballast resistance 2 ohm-km (yards), 4 ohm-km (block) | Only secondary copies found: [Scribd: DC Track Circuit](https://www.scribd.com/document/250220746/DC-Track-Circuit-Ver-1); [Scribd: Signalling](https://www.scribd.com/document/463665235/singnalling-pdf) | **T** (verify in the Signal Engineering Manual, as already warned in Section 3.2) |
| **R51** | Patents on estimating ballast resistance from track impedance phase and track-circuit parameter estimation | [US 7,295,017 B2](https://patents.google.com/patent/US7295017); [US 11,912,322 (parameter estimation)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11912322); [US 11,260,888 (health assessment)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11260888) | **L** |
| **R52** | Track-circuit principles (DC, AC, audio-frequency) | [Wikipedia: Track circuit](https://en.wikipedia.org/wiki/Track_circuit) | **L** |
| **R61** | Student repository on railway traffic optimisation (10-block simulation, dashboard, RL) | Not recovered; on GitHub search for "Railway Traffic Optimization System" | **N** |
| **R62** | Open-source libraries named in Sections 6.3 and 14.6 | Canonical project pages (not re-verified in either session): [PyTorch Geometric](https://github.com/pyg-team/pytorch_geometric), [PyTorch Geometric Temporal](https://github.com/benedekrozemberczki/pytorch_geometric_temporal), [SHAP](https://github.com/shap/shap), [lifelines](https://github.com/CamDavidsonPilon/lifelines), [OSRD](https://github.com/OpenRailAssociation/osrd), [SUMO](https://github.com/eclipse-sumo/sumo) | **T** |
| **R64** | Indian logbook failure data (Kharagpur to Bali Chalk, 2005-2010) for inspection modelling of signalling subsystems | Candidates: [Reliability and Inspection Modelling of Railway Signalling Systems](https://pure.kfupm.edu.sa/en/publications/reliability-and-inspection-modelling-of-railway-signalling-system/); [Reliability analysis of track circuit of Indian railway signalling system (Inderscience)](https://www.inderscience.com/offers.php?id=16258); [MDPI Modelling 2(3):18](https://mdpi.com/2673-3951/2/3/18) | **T** |
| **R71** | Wabtec Mors Smitt **Relay Condition Monitoring System**: coil voltage/current, contact current, remaining-life estimate for signalling relays | [Wabtec: Relay Condition Monitoring System](https://www.wabteccorp.com/Relay-Condition-Monitoring-System) | **L** |
| **R72** | Wabtec **Smart Crossings**: literature names "maintenance of detection circuits, track circuit degradation" as the pain point it addresses | [Wabtec: Smart Crossings](https://www.wabteccorp.com/smart-crossings) | **L** (marketing text read; not a technical performance claim) |
| **R75** | Delhi Metro (Magenta Line) centralised **Remote Health Monitoring System for signalling**, covering electrical parameters of point machines and signals | Delhi Metro Rail Corporation presentation, *State of play of use of artificial intelligence in rail*, UNESCAP workshop, 10 Sep 2025 ([PDF](https://www.unescap.org/sites/default/d8files/event-documents/2_AmitKumar.pdf)) | **O** (slides read) |
| **R76** | Metro predictive-maintenance practice: centralised parameter monitoring, not physics-based RUL | Same DMRC presentation as R75 | **O** |
| **R49-related** | railML is an open railway markup language | [railML.org](https://www.railml.org/en/software/sumo); [Wikipedia: RailML](https://www.wikipedia.org/wiki/RailML) | **L** |

## 24.4 Items to fix or confirm before you present

This section is the **v1.1 change log**. Every item that v1.0 flagged as unverified has been either resolved against a primary source or removed from the body. One item remains genuinely open and is the only thing you must not put on a slide without checking first.

### 24.4.1 Resolved in v1.1

| # | v1.0 issue | v1.1 resolution |
|---|---|---|
| 1 | Electrification figure was 99.1% (Oct 2025) and passenger/network figures came from the wrong source | Now **99.2% of BG electrified, 69,427 of 70,001 BG route-km** (Nov 2025) from PIB PRID=2211852, and **6,905 million passengers, 7,461 stations, 69,181 route-km** (2023-24) from the Indian Railways Year Book 2023-24 [R15b][R77]. Sections 3.1, 3.3, 3.4 F10, 5.2 and 20.1 updated |
| 2 | Accident-reduction claim had inconsistent end-year counts | Body now quotes the **percentage only** ("about 88% since 2014-15") with one named source, and states explicitly that end-year counts differ between outlets [R59] |
| 3 | Rolling Block "52 weeks" was cited to a news article that does not contain it | Now cited to the actual rule: **rule 15.02(c)**, Indian Railways (Open Lines) General (Third Amendment) Rules 2023, **G.S.R. 870(E), 29.11.2023** [R68]. Sections 11.2 K, 14.2, 17.2 and 19 updated |
| 4 | The 28 Dec 2016 / 02:16:47 CAG detail could not be re-read | **Verified and quoted**: CAG Report No. 45 of 2018, Para 2.2.1.5 — Rura (NCR), train 12987 Sealdah–Ajmer Express, over 50 injured, probable rail fracture, no Station Master follow-up [R12]. Sections 3.4 F3, 4 P6, 8 G6 and 19 updated |
| 5 | Rajya Sabha EI-count links could not be opened | The four-year EI count table was **deleted**. It added no argument that the two verified points (7,461 stations; 6,660 EI stations) do not already make [R77][R5] |
| 6 | RDPMS OEM-eligibility and metro-monitoring claims had no recoverable source | RDPMS eligibility now cites the **NWR Jaipur RDPMS tender** (SNT-Proj-JP-2024-25-01R) and the published **RDSO/SPN/257/2025 v2.0** [R60][R69]; the metro claim now cites **Delhi Metro's own presentation** on centralised signalling health monitoring [R75][R76]. The ₹147.3 lakh tender claim (old R63) is **dropped** |
| 7 | The 60-day drift run was not reproducible | Replaced by **`nidan_twin.py`**, a seeded script whose output is pasted verbatim into §5.3 and Appendix C. Anyone can re-run it; the v1.0 numbers are explicitly withdrawn |
| 8 | Wabtec was listed as "[Unverified] competitor" | Now described accurately: Wabtec sells **relay** condition monitoring (Mors Smitt) and its crossings literature names track-circuit degradation, but neither is physics-informed, graph-aware RUL for Indian track circuits [R71][R72] |
| 9 | "7,000+ stations" was a guess | Replaced by **7,461 stations** (Year Book 2023-24) and **6,660 EI / 6,665 fully track-circuited** (Dec 2025) [R77][R5] |
| 10 | "OpenMTS" simulator was unverifiable | Name **dropped**; the dossier now names OSRD, SUMO-rail and OpenTrack, all verified [R49] |
| 11 | "30-day IR probe" workflow was unverified | Replaced with the **prescribed periodicity** (fortnightly technician checks, monthly JE/inspector checks, quarterly shunt tests, half-yearly joint S&T–P.Way inspection) [R73][R74] |
| 12 | ₹2,000 Cr headline was unsourced | Kept only as a **reality check**: the dossier states the figure cannot be reproduced and gives the bottom-up **₹127–313 Cr capex + ₹20–53 Cr/yr opex ≈ ₹227–580 Cr over five years** (Section 22.5) |

### 24.4.2 Still open (do not quote without checking)

| # | Item | Why it is still open | Safe wording today |
|---|---|---|---|
| O1 | **R78** — "an Indian OEM has commissioned RDPMS indigenously" | The commissioning is reported in trade press, but the primary zone/OEM release was not re-read in this revision, so the tag is defined but **not used anywhere in the body** | Say "Indian vendors are already delivering RDPMS under the RDSO specification" and cite R20/R21/R69, which are verified |

Everything else in this dossier is either a primary-source fact, a labelled estimate, or explicitly framed as engineering judgement.

### 24.4.3 How to re-run the illustration

```
python3 nidan_twin.py
```

Requires Python 3 and NumPy. The script prints four blocks: the deterministic ballast sweep, the threshold locations, the lead-time comparison for linear versus exponential wetting, and the checkpoint detail with the inverse estimate. The numbers in §5.3 and Appendix C.4 are copied from that output. If you change any parameter, re-copy all of them — do not mix old and new numbers.

---

# 25. Appendices

## Appendix A. Glossary

| Term | Meaning in this document |
|---|---|
| **ABS** | Automatic Block Signalling: signals in a block section controlled by train detection rather than by manual block working |
| **AF track circuit** | Audio-frequency (jointless) track circuit; uses tuned audio carriers instead of insulated joints |
| **Axle counter** | Train detection by counting axles in and out of a section; used in block sections and in parallel with track circuits in some station designs |
| **Ballast** | Crushed stone bed under sleepers. Its electrical leakage between the rails is the central variable of a DC track circuit |
| **BPAC** | Block Proving Axle Counter: confirms a block section is clear using axle counts |
| **BNN-Surv** | Bayesian neural-network survival model |
| **C-index** | Concordance index: how well a survival model ranks who fails earlier (0.5 random, 1.0 perfect) |
| **CAG** | Comptroller and Auditor General of India |
| **CCSP** | C-DOT Common Service Platform, a oneM2M-based IoT platform that Railway Board wants RDPMS edge devices to comply with |
| **C-DOT** | Centre for Development of Telematics |
| **Codal life** | Prescribed service life of an asset under railway codes |
| **Conformal prediction** | Method that wraps a model's outputs in sets or intervals with a coverage guarantee, without assuming a data distribution |
| **CRIS** | Centre for Railway Information Systems; runs SMMS |
| **CRS** | Commissioner of Railway Safety; statutory accident investigator |
| **CUSUM / EWMA** | Cumulative-sum and exponentially weighted moving-average change detectors |
| **DFCCIL** | Dedicated Freight Corridor Corporation of India Ltd |
| **Digital twin (here)** | A live graph state plus a per-circuit physics model; not a 3D CAD model |
| **ECE** | Expected calibration error: gap between predicted and observed probability |
| **EI** | Electronic (or electrical) Interlocking: logic that prevents conflicting routes and signal aspects |
| **ESM / JE / SSE** | Electric Signal Maintainer / Junior Engineer / Senior Section Engineer (Signal), the field maintenance hierarchy |
| **FRS** | Functional Requirement Specification (RDSO document) |
| **Frailty** | Random effect in a survival model capturing shared unobserved risk (station, supply, climate zone) |
| **GNN** | Graph neural network |
| **Hawkes process** | Self-exciting point process used for clustered event times |
| **IPS** | Integrated Power Supply for signalling |
| **ITMS / WILD / OMRS / MVIS** | Integrated Track Monitoring System / Wheel Impact Load Detector / Online Monitoring of Rolling Stock / Machine Vision Inspection System |
| **Kavach** | Indian automatic train protection system |
| **MTBF / MTTR** | Mean time between failures / mean time to restore |
| **MoM** | Minutes of meeting |
| **NFF** | No fault found: an intermittent fault that disappears when inspected |
| **NIDAN (निदान / निदानम्)** | The project name. Hindi: diagnosis and root cause, also "remedy"; Sanskrit: cause, origin, diagnosis. Pronounced *ni-DAAN* |
| **OEM** | Original equipment manufacturer (here, RDPMS and data-logger vendors) |
| **PCCL** | Pre-commissioning checklist |
| **Pūrvarūpa / Nidāna / Samprāpti / Upaśaya** | Ayurvedic diagnostic sequence: early signs, underlying cause, staged development, and response to a trial measure. Used as the storytelling frame for NIDAN's layers (Section 9.1) |
| **RDPMS** | Remote Diagnostic and Predictive (Preventive) Maintenance System for signalling |
| **RDSO** | Research Designs and Standards Organisation |
| **RUL** | Remaining useful life |
| **Rolling Block** | Planned engineering/maintenance block windows, scheduled in advance by zones |
| **RTU** | Remote terminal unit |
| **SHAP** | Shapley-value feature attribution method |
| **SIL** | Safety integrity level; NIDAN is advisory (outside the vital safety chain) |
| **SMMS** | Signal Maintenance Management System (CRIS): asset and failure register |
| **Track circuit** | Electrical train detection using the two rails as conductors |
| **UKF** | Unscented Kalman filter |

## Appendix B. Data schemas (illustrative **[Design choice]**)

These are NIDAN's proposed canonical shapes. **The real SMMS and OEM export formats are not public**; replace field names after a partner shares samples (Section 15.3).

### B.1 Measurement event (Kafka topic `tc.measurement.<zone>`; Avro/Protobuf in production)

```json
{
  "schema_version": "1.0",
  "event_id": "uuid",
  "ts_utc": "2026-07-14T12:04:10.250Z",
  "clock_quality": "gps_disciplined",
  "zone": "ECoR", "division": "KUR", "station": "XYZ",
  "asset_id": "XYZ/TC/12T",
  "circuit_type": "DC",
  "source": "datalogger | rdpms_oem | tap_sensor",
  "source_vendor": "string or null",
  "features": {
    "feed_v": 11.8, "feed_i": 0.62, "relay_v": 8.1, "relay_i": 0.82,
    "ripple_mv": 14.0, "supply_bus_v": 109.7
  },
  "window_s": 10,
  "quality": {"flatline": false, "spike": false, "calibration_status": "in_date", "calibrated_on": "2026-05-02"}
}
```

### B.2 Occupancy and interlocking event (`ei.event.<zone>`)

```json
{
  "ts_utc": "2026-07-14T12:04:11.100Z",
  "asset_id": "XYZ/TC/12T",
  "state": "occupied | clear",
  "detector": "track_circuit | axle_counter | ei_logic",
  "route_id": "R-04 or null",
  "axle_count_in": 38, "axle_count_out": 38,
  "reset_event": false
}
```

The dual-detection monitor (N3) compares `detector` states on the same section over time.

### B.3 Asset and topology record

```json
{
  "asset_id": "XYZ/TC/12T", "type": "track_circuit",
  "length_m": 420, "circuit_type": "DC",
  "installed": "2009-03-01", "codal_life_years": 15,
  "relay_asset_id": "XYZ/RLY/TR12", "supply_asset_id": "XYZ/IPS/1",
  "cable_route_id": "XYZ/CBL/N2", "relay_room_id": "XYZ/RR/1",
  "weather_cell_id": "wx-20.30N-85.83E",
  "data_trust": {"score": 0.62, "flags": ["age_vs_signature_mismatch"]}
}
```

Graph edges (Section 11.2 Step G) are derived rows: `(src, dst, edge_type, since)` with `edge_type` in `weather_cell | shared_asset | route_dependency | work_history`.

### B.4 Alert with three-part explanation (`nidan.alert`)

```json
{
  "alert_id": "uuid", "asset_id": "XYZ/TC/12T", "level": "Watch",
  "created_utc": "2026-07-14T05:10:00Z",
  "risk": {"h24": 0.04, "h72": 0.11, "h7d": 0.24, "ece_zone": 0.04},
  "rul_days": {"p10": 9, "median": 21, "p90": 38},
  "likely_modes": ["F1"], "mode_set_coverage": 0.90,
  "cluster": {"id": "c-9917", "members": ["XYZ/TC/12T","XYZ/TC/14T","XYZ/TC/16T"], "shared": "weather_cell/drain"},
  "explanation": {
    "physics": "Effective ballast conductance +31% in 12 days; relay margin 73% of dry",
    "shap_top": [{"feature": "relay_i_slope_7d", "value": -0.41}, {"feature": "rain_72h", "value": -0.12}],
    "precedents": ["SMMS-evt-118", "SMMS-evt-204", "SMMS-evt-377"]
  },
  "proposed_action": {"type": "ballast_clearing", "block_window": "next_rolling_block", "est_minutes": 90},
  "model_versions": {"twin": "0.3.1", "gnn": "0.2.0", "survival": "0.2.4"}
}
```

### B.5 SMMS pre-fill draft (human confirms; NIDAN never writes silently)

```json
{
  "asset_id": "XYZ/TC/12T",
  "suspected_cause_code": "TO_BE_MAPPED_TO_SMMS_CODE_LIST",
  "evidence_summary": "Ballast conductance trend, relay margin 73% of dry",
  "linked_alert_id": "uuid",
  "technician_response": null,
  "response_options": ["confirmed", "not_found", "other"]
}
```

## Appendix C. Simulator and verification code

### C.1 What this code is, and is not

It implements the **uniform-line transmission model** of Section 5.3 and 11.2 Step C. Parameters are illustrative: L = 0.75 km, rail loop resistance 0.10 ohm/km, 12 V feed through 3 ohm, 9 ohm relay, 0.5 ohm train shunt at the relay end. It is **not calibrated to any Indian Railways circuit**. The script is saved as `nidan_twin.py` and needs only NumPy.

### C.2 Code

The file below is `nidan_twin.py`, byte-for-byte. It is also saved alongside this document, so you can run it without retyping anything.

```python
#!/usr/bin/env python3
"""
NIDAN Appendix C: illustrative DC track-circuit transmission-line twin.

ILLUSTRATIVE PARAMETERS, NOT CALIBRATED TO ANY INDIAN RAILWAYS CIRCUIT.
  L = 0.75 km, rail loop resistance r = 0.10 ohm/km, feed 12 V through Rs = 3 ohm,
  relay Rr = 9 ohm, train shunt 0.5 ohm placed across the relay end.

Model: uniform lossy line (series r ohm/km, shunt g = 1/Rb S/km), source at x=0, relay at x=L.
  gamma = sqrt(r*g), Z0 = sqrt(r/g), ABCD matrix of the line, solved for relay current.

Every number printed here is reproducible: fixed seed, no hidden state.
Usage:  python3 nidan_twin.py
Needs:  numpy
"""
import numpy as np

L, R_LOOP, VS, RS, RR, R_SHUNT = 0.75, 0.10, 12.0, 3.0, 9.0, 0.5


def relay_current(ballast_ohm_km, occupied=False):
    """Relay current (A). ballast_ohm_km=None means perfectly dry (no leakage)."""
    load = RR * R_SHUNT / (RR + R_SHUNT) if occupied else RR
    if ballast_ohm_km is None:
        return VS / (RS + R_LOOP * L + load) * (load / RR)      # series-only circuit
    g = 1.0 / ballast_ohm_km
    gam, z0 = np.sqrt(R_LOOP * g), np.sqrt(R_LOOP / g)
    c, s = np.cosh(gam * L), np.sinh(gam * L)
    a, b, cc, d = c, z0 * s, s / z0, c                           # ABCD of the line
    z_in = (a * load + b) / (cc * load + d)
    v_in = VS * z_in / (RS + z_in)
    v_relay = v_in / (a + b / load)
    return v_relay / RR


DRY = relay_current(None, occupied=False)


def pct_free(rb):
    return 100.0 * relay_current(rb) / DRY


def pct_occupied(rb):
    return 100.0 * relay_current(rb, occupied=True) / DRY


def estimate_ballast(pct_of_dry, lo=0.05, hi=500.0):
    """Invert the twin: effective ballast resistance (ohm-km) from free-section relay current
    (% of dry). pct_free is monotonic increasing in Rb, so bisection in log-space is safe.
    This is the 'effective parameter' of Section 11.2 Step C, not a full UKF."""
    for _ in range(80):
        mid = np.sqrt(lo * hi)
        if pct_free(mid) < pct_of_dry:
            lo = mid
        else:
            hi = mid
    return float(np.sqrt(lo * hi))


def drift_alarm(days, pct, window=7, slope_thr=-0.3, level_thr=75.0):
    """Trend detector used in Section 5.3: 7-day slope strongly negative AND level below 75%.
    'Strongly negative' is a design choice here: slope < -0.3 percentage points/day."""
    for i in range(window, len(days)):
        x, y = days[i - window:i + 1], pct[i - window:i + 1]
        slope = np.polyfit(x, y, 1)[0]
        if slope < slope_thr and pct[i] < level_thr:
            return int(days[i])
    return None


def first_below(days, pct, thr=50.0):
    for d, p in zip(days, pct):
        if p < thr:
            return int(d)
    return None


def scenario(shape, days=60, rb0=8.0, rb1=1.5, seed=7, noise=0.04, level_noise=0.4):
    """Synthetic monsoon wetting from rb0 to rb1 ohm-km over `days`, with measurement noise.
    shape='linear'  : ballast resistance falls at a constant rate
    shape='exp'     : ballast resistance falls exponentially (fast early, slow late)
    Returns (days, true_rb, observed_pct)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0, days + 1)
    frac = t / float(days)
    true_rb = rb0 * (1.0 - frac) + rb1 * frac if shape == "linear" else rb0 * (rb1 / rb0) ** frac
    obs_rb = true_rb * np.exp(rng.normal(0.0, noise, t.size))
    obs_pct = np.array([pct_free(r) for r in obs_rb]) + rng.normal(0.0, level_noise, t.size)
    return t, true_rb, obs_pct


if __name__ == "__main__":
    print(f"Dry relay current: {DRY:.3f} A\n")

    print("TABLE 1: deterministic sweep (reproduces Section 5.3 table)")
    print("ballast_ohm_km | free_pct | occupied_pct")
    for rb in [50, 20, 10, 8, 6, 5, 4, 3, 2.5, 2, 1.5, 1.0, 0.7]:
        print(f"{rb:>14} | {pct_free(rb):8.1f} | {pct_occupied(rb):10.1f}")

    # Where do the two thresholds of Section 5.3 sit?
    print(f"\nEarly-warning (70%) reached near {estimate_ballast(70.0):.2f} ohm-km")
    print(f"Assumed drop-away (50%) reached near {estimate_ballast(50.0):.2f} ohm-km")

    # TABLE 2: sensitivity of detection lead time to the shape of the wetting.
    print("\nTABLE 2: lead time vs wetting shape (60 days, 8.0 -> 1.5 ohm-km, seed 7)")
    print("scenario  | alarm day | drop day | lead time (days)")
    for shape in ("linear", "exp"):
        t, true_rb, obs_pct = scenario(shape)
        a, d = drift_alarm(t, obs_pct), first_below(t, obs_pct)
        lead = d - a if (a is not None and d is not None) else None
        print(f"{shape:>9} | {a:^9} | {d:^8} | {lead:^16}")

    # TABLE 3: detail of the linear scenario, including the inverse estimate.
    print("\nTABLE 3: linear scenario, checkpoint detail (seed 7)")
    t, true_rb, obs_pct = scenario("linear")
    a, d = drift_alarm(t, obs_pct), first_below(t, obs_pct)
    checkpoints = sorted({0, 10, 20, 30, 40, 50, 59, 60} | {x for x in (a, d) if x is not None})
    errs = []
    for day in checkpoints:
        est = estimate_ballast(obs_pct[day])
        errs.append(abs(est - true_rb[day]) / true_rb[day])
        mark = "  <- trend alarm" if day == a else ("  <- relay drop-away" if day == d else "")
        print(f"  day {day:>2}: ballast(true)={true_rb[day]:5.2f}  relay={obs_pct[day]:5.1f}%  "
              f"inverted_estimate={est:5.2f} ohm-km{mark}")
    print(f"  trend alarm day: {a}   first day below 50%: {d}"
          + (f"   lead time: {d - a} days" if (a is not None and d is not None) else ""))
    print(f"  max inversion error at checkpoints: {100.0 * max(errs):.1f}%")
```

### C.3 Output of the script (run on 22 November 2026, Python 3.14.2, NumPy 2.4.2)

```
Dry relay current: 0.994 A

TABLE 1: deterministic sweep (reproduces Section 5.3 table)
ballast_ohm_km | free_pct | occupied_pct
            50 |     96.7 |       17.8
            20 |     92.1 |       17.6
            10 |     85.4 |       17.3
             8 |     82.4 |       17.2
             6 |     77.8 |       17.0
             5 |     74.5 |       16.8
             4 |     70.1 |       16.5
             3 |     63.7 |       16.1
           2.5 |     59.4 |       15.8
             2 |     53.9 |       15.4
           1.5 |     46.6 |       14.7
           1.0 |     36.8 |       13.5
           0.7 |     28.8 |       12.1

Early-warning (70%) reached near 3.99 ohm-km
Assumed drop-away (50%) reached near 1.71 ohm-km

TABLE 2: lead time vs wetting shape (60 days, 8.0 -> 1.5 ohm-km, seed 7)
scenario  | alarm day | drop day | lead time (days)
   linear |    26     |    59    |        33       
      exp |    16     |    56    |        40       

TABLE 3: linear scenario, checkpoint detail (seed 7)
  day  0: ballast(true)= 8.00  relay= 82.2%  inverted_estimate= 7.90 ohm-km
  day 10: ballast(true)= 6.92  relay= 79.7%  inverted_estimate= 6.71 ohm-km
  day 20: ballast(true)= 5.83  relay= 75.9%  inverted_estimate= 5.38 ohm-km
  day 26: ballast(true)= 5.18  relay= 73.1%  inverted_estimate= 4.64 ohm-km  <- trend alarm
  day 30: ballast(true)= 4.75  relay= 72.6%  inverted_estimate= 4.53 ohm-km
  day 40: ballast(true)= 3.67  relay= 67.9%  inverted_estimate= 3.62 ohm-km
  day 50: ballast(true)= 2.58  relay= 61.1%  inverted_estimate= 2.69 ohm-km
  day 59: ballast(true)= 1.61  relay= 47.8%  inverted_estimate= 1.57 ohm-km  <- relay drop-away
  day 60: ballast(true)= 1.50  relay= 46.6%  inverted_estimate= 1.50 ohm-km
  trend alarm day: 26   first day below 50%: 59   lead time: 33 days
  max inversion error at checkpoints: 10.4%
```

### C.4 How this checks Section 5.3 (read this before quoting numbers)

* **Deterministic table: reproduced exactly.** Every free-section value matches Section 5.3 to one decimal. The occupied column matches within rounding (at 4 ohm-km the computed value is 16.55, shown as 16.6 in the table and 16.5 here).
* **Thresholds: reproduced.** The 70% early-warning level sits near 4 ohm-km and the 50% drop-away near 1.7 ohm-km, as stated in the text.
* **Drift demonstration: now fully reproducible.** Section 5.3's table is the linear-wetting scenario with seed 7, and every row comes from this script's TABLE 3. The detector alarms on day 26 and the relay drops on day 59, giving a **33-day lead**; the exponential variant alarms on day 16 and drops on day 56, giving 40 days.
* **What changed from v1.0.** The earlier draft reported a ~24-day lead derived from noise draws that were never saved, and Appendix C could only interpolate between surviving checkpoints. That is gone: v1.1 prints the whole trajectory, so the table and the lead time cannot drift apart.
* **The lead time is a property of the scenario, not a result.** It scales with how slowly the wetting happens and with where the thresholds sit. Never quote 33 or 40 days as an expected field number. The defensible claim is the *mechanism*: a trend-aware estimator sees a shrinking margin that a threshold alarm cannot.
* **None of this is evidence about real Indian circuits.** The parameters are illustrative and the model is not calibrated to any IR circuit.

## Appendix D. Verification and pre-showcase checklist

### D.1 What is simulated versus real (say this out loud)

| Item | Status |
|---|---|
| Transmission-line model and tables in Section 5.3 | Simulated; illustrative parameters |
| 60-day drift demonstration | Synthetic |
| Detection lead times, risk numbers in Section 12.2 | Illustrative story, synthetic numbers |
| Acceptance targets in Section 16.4 | Proposed design choices, not results |
| Cost and market figures in Section 22 | Estimates built on stated assumptions |
| Railway Board, CAG, PIB, CRS statements | Sourced (see Section 24 for status of each link) |
| Accuracy figures from papers (99.31%, 99.7%, 99.36%) | From the papers' own setups; **not** expected field accuracy |

### D.2 Expert conversations to book before the showcase

1. **An SSE/Sig or ESM:** confirm the local variation in inspection periodicity (the codal schedule is in R73/R74) and how SMMS entries are actually made.
2. **An RDSO or CRIS contact:** confirm the clause-level requirements of RDSO/SPN/257/2025 v2.0 and the canonical data model expectations.
3. **An RDPMS OEM engineer:** confirm available sampling rates and export formats.
4. **Someone who has handled a CRS inquiry:** confirm how latent-maintenance findings are usually presented.

### D.3 Slide-level checks

* [ ] Open each source you put on a slide and copy the sentence you rely on (§24.4.2 lists the two remaining open items).
* [ ] Use the verified numbers: **99.2% BG electrified**, **6,905 million passengers (2023-24)**, **7,461 stations**, **6,660 EI / 6,665 fully track-circuited** [R15b][R77][R5].
* [ ] Say **"no public physics-informed, graph-aware RUL product"**, not "no competitor" — Wabtec and Siemens do sell adjacent condition monitoring [R71][R72][R45].
* [ ] Never say "OpenMTS"; name OSRD, SUMO-rail or OpenTrack [R49].
* [ ] Show the ₹2,000 crore figure only as *"claimed in the original sheet; our bottom-up India-only estimate is ₹227–580 Cr over five years"* (Section 22.5).
* [ ] Label every chart and demo as **simulated** or **bench**.
* [ ] State "advisory only, non-vital, no write path" on the architecture slide.
* [ ] Rehearse the 7-minute flow (Section 21.6) and the 16 questions (Section 23.1).

### D.4 Reproducibility checklist for your own repository

* [ ] Commit `nidan_twin.py` and its output; re-run after any parameter change.
* [ ] Pin library versions when the real pipeline is built (Section 14).
* [ ] Keep one file recording each assumption **A1-A7** and who owns confirming it.
* [ ] Keep this reference table (Section 24) as a spreadsheet and mark each link as opened or not as you verify it.

---

*End of dossier.*
