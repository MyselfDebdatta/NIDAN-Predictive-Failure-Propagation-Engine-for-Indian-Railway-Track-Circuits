# NIDAN — Front-End Research & Implementation Specification

**Predictive Failure Propagation Engine for Indian Railway Track Circuits**

| | |
|---|---|
| Document | Front-end research, design system and implementation specification |
| Version | 1.0 |
| Date | 14 July 2026 |
| Status | Build-ready specification; static mockups are the visual contract |
| Scope | Web application (desktop control room + field PWA), advisory only |
| Companion artefacts | `design/mockups/` — seven screens, shared tokens/styles/script, captured screenshots |
| Audience | Product, design, front-end, CRIS/RDSO review, OEM integration |

> **Advisory, non-vital.** Nothing in this interface writes to interlocking, signals, routes, points or track circuits. The product holds no command path and no write credential. Every screen says so, and the absence of control affordances is itself a safety feature.

---

## Contents

1. [Executive summary](#1-executive-summary)
2. [What NIDAN is, and is not](#2-what-nidan-is-and-is-not)
3. [Design thesis](#3-design-thesis)
4. [Domain model and vocabulary](#4-domain-model-and-vocabulary)
5. [Information architecture and routes](#5-information-architecture-and-routes)
6. [Signature interaction patterns](#6-signature-interaction-patterns)
7. [Screen specifications](#7-screen-specifications)
8. [Design tokens and theming](#8-design-tokens-and-theming)
9. [Typography and the bilingual system](#9-typography-and-the-bilingual-system)
10. [Accessibility and inclusive field use](#10-accessibility-and-inclusive-field-use)
11. [Component library and TypeScript contracts](#11-component-library-and-typescript-contracts)
12. [Data contracts: REST, streaming and offline](#12-data-contracts-rest-streaming-and-offline)
13. [State, data fetching and mutation](#13-state-data-fetching-and-mutation)
14. [Technology stack decision record](#14-technology-stack-decision-record)
15. [Repository structure and engineering conventions](#15-repository-structure-and-engineering-conventions)
16. [Performance, resilience and field constraints](#16-performance-resilience-and-field-constraints)
17. [Benchmark: what to borrow and what to avoid](#17-benchmark-what-to-borrow-and-what-to-avoid)
18. [Delivery roadmap, instrumentation and risks](#18-delivery-roadmap-instrumentation-and-risks)
19. [References](#19-references)

---

## 1. Executive summary

NIDAN is a predictive failure propagation engine for Indian Railways track circuits. Its back end fuses a physics twin, a failure-mode classifier, a propagation graph and a survival model. Its front end has one job: turn that stack into a decision a section engineer can defend at 02:40, in monsoon, with a block that starts in ninety minutes.

This specification defines that front end — the research behind it, the design system that makes it coherent, and the React implementation that makes it real. It is written to be built from, not admired. The seven static mockups in `design/mockups/` are the visual contract; this document is the behavioural and technical contract.

**The product thesis in five sentences.**

1. A probability is not an alert. A usable alert names a failure mode, shows the physical evidence, states what would falsify it, and gives a remaining-life interval.
2. A queue is not a list. Work is ordered by expected consequence and by whether it fits a Rolling Block that is already published.
3. Common causes should collapse into one job. Three circuits sharing a drain are one drain problem, not three tickets.
4. The field is not a smaller desktop. It is sunlight, gloves, no signal, and a technician who needs three large steps and an offline queue.
5. Trust is a feature. Calibration, coverage, drift and data quality are user-facing, because a supervisor is being asked to act on a model that is expressly non-vital.

**The design answer** is a deep-ink control surface with a teal signal accent, an amber caution and a red reserved for Critical alone. Its signature pattern is the **Signal Spine** — one ordered, state-shaped line through a division — paired with a **three-lens Explanation Card** (physics, model, precedents) that makes every score interrogable. The four Ayurvedic diagnostic stages — Pūrvarūpa, Nidāna, Samprāpti, Upaśaya — supply the narrative spine: early signs, cause, course, response. They are a UX motif grounded in the domain's own diagnostic logic, not decoration and not a medical claim.

**What has been delivered.**

| Artefact | Path | Notes |
|---|---|---|
| Command centre | `design/mockups/pages/command-center.html` | KPIs, Signal Spine, propagation map, cluster rail, priority queue, Rolling Block windows |
| Circuit detail | `design/mockups/pages/circuit-detail.html` | RUL band, three-lens explanation, signals, failure modes, cluster, recommended action, asset record |
| Alert queue | `design/mockups/pages/alert-queue.html` | Filters, saved views, bulk triage, dense table, ranking rationale |
| Field confirmation | `design/mockups/pages/field-tablet.html` | Light high-contrast theme, 56 px targets, offline queue, three-step confirm, SMMS draft |
| Model health | `design/mockups/pages/model-health.html` | Reliability diagram, calibration by level, registry, drift, data trust, promotion gates |
| Design system | `design/mockups/pages/design-system.html` | Colour, type, spacing, state language, components, data display, motion, accessibility, vocabulary |
| Cover / gallery | `design/mockups/pages/index.html` | Thesis and numbered screen index |
| Screenshots | `design/mockups/screenshots/*.png` | Rendered with headless Chrome at 1600 px desktop and 1024 px tablet |
| Tokens | `design/mockups/assets/tokens.css` | 122 tokens, field-theme inversion |
| Components | `design/mockups/assets/app.css` | Shell, panels, tables, spine, explanation, RUL, queue, field, model health |
| Shared behaviour | `design/mockups/assets/app.js` | Shell injection, tabs, sparklines, keyboard tab handling, clock |

The mockups are dependency-free HTML/CSS/JS. They share one token file and one component stylesheet, so every screen is demonstrably one product. They are intentionally static: no framework, no build step, no invented API.

**The recommended build** is React 19 + TypeScript, Vite, Tailwind CSS v4 mapped onto the same CSS custom properties, shadcn/ui primitives on Radix, TanStack Query v5, TanStack Table v8 with virtualization, Zustand for ephemeral UI state, and a Workbox service worker with an IndexedDB outbox for the field route. The core data visualisations — RUL band, sparklines, SHAP bars, propagation graph — are hand-authored SVG, not a charting dependency. Section 14 records the reasoning and the rejected alternatives.

**The one thing not to compromise.** The interface must never look like it can control the railway. There is no disabled "Set route" button, no greyed-out "Operate points" menu, no lock icon implying a permission that could be granted. The limit is architectural, and the UI should make it feel deliberate rather than missing.

---

## 2. What NIDAN is, and is not

### 2.1 Product scope

NIDAN ingests condition data from track circuits and their supporting assets, estimates degradation and failure mode, reasons over dependencies and common causes, and produces a ranked, explainable, advisory work list that fits Indian Railways maintenance practice.

**In scope**

- Track circuits (DC and AC), relay ends, feed/supply points, cable routes, insulated joints, ballast and drainage conditions.
- Failure modes F1–F12: ballast resistance, insulated/glued joint, rail bond/continuity, metallic bridging at points, relay ageing, power supply, lightning/surge, cable faults, shunting failure, stray/traction interference, maintenance/config error, no-fault-found.
- Alert levels Watch, Warning, Critical with explicit, auditable policy.
- Remaining useful life as a **distribution** (p10 / median / p90), with conformal coverage.
- Common-cause clusters and predicted propagation to dependent assets and routes.
- Rolling Block-aware work orders and SMMS draft pre-fill.
- Model assurance: calibration, coverage, drift, data trust, promotion gates.

**Out of scope, permanently**

- Any write path to interlocking, signals, routes, points, block instruments or track circuits.
- Automatic block request, automatic signal control, automatic route setting.
- Automatic closure of an alert without a human outcome.
- Replacing the SSE's judgement, the SMMS record of work, or the prescribed inspection regime.
- Safety certification as a vital system. NIDAN is advisory and non-vital by design.

### 2.2 Users and jobs

| Role | Primary job | What the interface owes them |
|---|---|---|
| Technician (field) | Confirm or refute a predicted cause under block; record evidence | Offline-first task, huge targets, plain language, bilingual labels, three steps, no typing if avoidable |
| SSE / Sig (section) | Decide what to fix, when, with whom; defend the decision | Ranked queue, falsifiers, block fit, one-click SMMS draft, audit trail |
| Section engineer / supervisor | Balance crews and blocks across sections | Cluster view, Rolling Block calendar, workload and deferral consequences |
| Divisional control | Understand risk to traffic and routes, not asset minutiae | Consequence framing, predicted cascade, route exposure, no false precision |
| CRIS / RDSO reviewer | Assure the model and the process | Calibration, coverage, drift, registry, promotion gates, immutable audit |
| OEM / maintainer | Diagnose an asset family and feed back outcomes | Asset history, precedents, failure-mode evidence, exportable pack |
| Leadership | See whether the programme is working | Averted failures, false-positive rate, lead time, interventions completed |

### 2.3 Non-negotiable constraints

1. **Advisory only.** No control affordance, no write credential, no ambiguous "apply" verb.
2. **Human closure.** An alert closes only through a technician outcome, an SMMS entry, or an explicit, attributed SSE decision.
3. **Uncertainty is visible.** No point estimate without an interval; no probability without calibration context.
4. **Field reality.** Offline, gloves, sunlight, low-end Android tablets, 3G at best, English and Hindi.
5. **Correct vocabulary.** Track circuit, relay room, IPS, axle counter, block section, Rolling Block, SMMS — not generic SaaS language.
6. **Explainability is tri-modal.** Physics, model contribution and precedent must be one click apart.
7. **Colour is never the sole carrier.** Shape, word and number always accompany it.
8. **The UI never implies certainty the model does not have.** "Data trust 0.62" is shown next to the alert, not buried.

### 2.4 The demo dataset used across the mockups

A single coherent scenario runs through every screen, taken from the programme dossier:

- Asset `ADRA/TC/12T`, Adra Yard, Down Goods, 420 m DC track circuit, relay `XYZ/RLY/TR12`, installed 01 Mar 2009, codal life 15 years, data trust 0.62.
- Watch level; risk 4% / 11% / 24% at 24 h / 72 h / 7 d; RUL p10 9 d, median 21 d, p90 38 d.
- Likely mode F1 (low ballast resistance), conformal set {F1, F4}, coverage 0.90.
- Cluster `c-9917` with 14T and 16T, shared weather cell `wx-20.30N-85.83E` and drain; predicted cascade to 21T in 6–11 days.
- Recommended action: ballast clearing + drain rodding, 90 minutes, inside Rolling Block RB-28 on 16 Jul, 02:10–03:40.
- Model versions: twin 0.3.1, GNN 0.2.0, survival 0.2.4, classifier 0.2.0.

Using one dataset is a deliberate QA device: inconsistency between screens is immediately visible.

---

## 3. Design thesis

The interface is a **control-room instrument**, not an analytics dashboard. Ten principles follow, each with a test that a reviewer can apply to a screenshot.

**1. Signal before statistics.**
The page answers "what should I do next?" before "what is the model doing?". The Signal Spine and the queue come before any chart. *Test:* a new SSE can name the top three actions in ten seconds without reading a legend.

**2. One spine, one ranking.**
Every surface uses the same ordering logic: calibrated risk × consequence × exposure, discounted by data trust. There is no second, contradictory priority list. *Test:* the fourth item in the command-centre queue matches the fourth row of the queue screen.

**3. Explain, then ask.**
The explanation is adjacent to the action, not behind a "details" link. Physics, model and precedents are tabs in the same card that carries the recommendation. *Test:* the user can reach a falsifier in one click from any alert.

**4. Uncertainty is a first-class object.**
RUL is a band. Risk is a curve across horizons. Coverage is printed. A model that cannot state its error bars is not allowed to raise an alert. *Test:* remove the median from the RUL chart; the band still communicates the decision.

**5. Fit the railway's existing time.**
Rolling Blocks are the unit of intervention. A recommendation that needs a special block is marked as such and ranked lower. *Test:* every action row names a block and a duration, or says explicitly that none exists.

**6. Collapse common cause.**
The cluster is a first-class object, not a tag. Fixing the drain is one job that clears three alerts, and the UI says so once. *Test:* no screen asks a user to acknowledge three copies of the same physical cause.

**7. The field is a different instrument.**
The field mode is not the desktop squeezed. It is a light, high-contrast, glove-safe, offline-first confirmation flow with its own type scale, targets and language. *Test:* the primary action is reachable with a thumb and legible in direct sun at 50 cm.

**8. Calm surface, precise data.**
Deep ink, one accent, restrained motion. Numbers are tabular. Labels are small but never tiny. Nothing pulses except a live-data dot. *Test:* a wall display does not flicker, and a screenshot is readable in greyscale.

**9. The Ayurvedic spine is structural, not ornamental.**
Pūrvarūpa (early signs), Nidāna (cause), Samprāpti (course), Upaśaya (response) maps exactly onto drift → diagnosis → prognosis → intervention. It is always paired with English; it never becomes a puzzle. *Test:* a reviewer who does not read Sanskrit can still use every stage label.

**10. Honesty is visible.**
"Advisory · non-vital" is in the chrome, the footer, the model-health page and the field footer. Data trust is on the alert. The system does not pretend to certainty, and it does not pretend to control. *Test:* no screen contains an affordance that could be mistaken for a command path.

### 3.1 Visual direction

| Dimension | Decision |
|---|---|
| Base | Deep ink/navy `#060C12` → `#1A2C3A`, never pure black |
| Accent | Teal `#38E0CE` for nominal, live, primary action; not for decoration |
| Caution | Amber `#F9BE5C`, used for Warning and for uncertainty |
| Critical | Red `#FF6B70`, reserved for Critical and destructive actions only |
| Type | Inter (Latin grotesk) + Noto Sans Devanagari; JetBrains Mono for IDs and telemetry |
| Grid | 12 columns, 20 px gutters, 8-point spacing |
| Surfaces | Three levels of panel plus hairline borders; one soft elevation, no glassmorphism |
| Motion | 120/180/240 ms, opacity and 4 px translate only; reduced-motion collapses to instant |
| Density | Dense but scannable; 44 px panel heads, 32 px controls, 27 px compact controls |
| Field | Warm paper `#F4F3EE`, deep teal `#06645E`, 56 px targets, 2 px borders |

---

## 4. Domain model and vocabulary

### 4.1 The physical object

A track circuit is a length of running rail used to detect the presence of a train. A transmitter feeds one end; a relay or receiver at the other picks up through the rails. A train's axles short the rails, dropping the relay and proving occupancy. The circuit's reliability depends on the **ballast resistance** between the rails, the continuity of bonds and joints, the cable and feed, and the relay's own condition. Water in the ballast lowers resistance; a fouled or drained formation therefore degrades every circuit that shares it.

Three consequences shape the UI:

- **The asset is a chain, not a box.** A "track circuit" alert may actually be a relay-room feed, a cable route or a drain. The asset record must show the chain.
- **Failure modes are physical and finite.** F1–F12 are the vocabulary; a generic "anomaly" is not acceptable copy.
- **False detection has a wrong-side risk.** A circuit that fails to shunt can fail to detect a train. F9 is treated with special gravity in the copy and the review queue.

### 4.2 The diagnostic spine

| Stage | Sanskrit | System meaning | UI expression |
|---|---|---|---|
| Early signs | Pūrvarūpa | Drift from baseline before a threshold | Watch level, sparkline slope, 30-day baseline |
| Cause | Nidāna | Named failure mode with physical evidence and a falsifier | Likely mode card, twin state, SHAP, exclusions |
| Course | Samprāpti | Propagation, cluster membership, remaining life | RUL band, cluster graph, cascade prediction |
| Response | Upaśaya | Intervention and its expected effect inside a block | Recommendation, Rolling Block fit, SMMS draft, causal trial log |

The mapping is used as the section order of the circuit page and as the stage rail on the detail screen. It is not used as a substitute for English labels, and no diagnosis is ever presented as medical.

### 4.3 Alert policy (as specified in the dossier)

| Level | Trigger | Persistence / confidence rule | UI obligation |
|---|---|---|---|
| Watch | 7-day risk > 20% **or** RUL p10 < 30 days | Persist over 3 evaluations | Show trend, cluster, next block; no interruption |
| Warning | 72-hour risk > 30% and relay margin below early-warning band | Model agreement and calibrated confidence | Plan inside next publishing cycle; show block fit |
| Critical | 24-hour risk > 50% with high confidence, **or** cluster root cause | Human review within the shift | Red, diamond glyph, act-today language, deferral recorded |

Thresholds live server-side and are versioned. The front end renders the policy but never computes or escalates a level. A UI that "rounds up" a Warning into a Critical destroys trust faster than a missed alert.

### 4.4 Vocabulary rules

| Use | Not | Why |
|---|---|---|
| Track circuit | track sensor, loop | The asset has a specific meaning and a safety role |
| Relay room | signal cabin | Cabin implies an operational signal box |
| Block / Rolling Block | outage, downtime | Work is granted within a block; downtime is a data-centre word |
| Failure mode F1–F12 | fault type, bug | The taxonomy is the shared language with SMMS and the OEM |
| Watch / Warning / Critical | low / medium / high, P1 | The three levels are policy objects, not severity adjectives |
| Remaining useful life, p10–p90 | ETA, expiry | RUL is a distribution, not a promise |
| Acknowledge | Accept, Approve | Acknowledge records seeing; it does not approve work |
| Data trust | data quality score | Trust is about fitness for this decision, not general hygiene |
| Section engineer / SSE (Sig) | manager | Use the actual role |
| Adra division, South Eastern Railway | SER zone | Division and railway are distinct |

Bilingual pairings used in the field mode and headings: ट्रैक सर्किट (track circuit), रिले कक्ष (relay room), ब्लॉक (block), विफलता प्रकार (failure mode), निगरानी / चेतावनी / गंभीर (Watch / Warning / Critical), शेष उपयोगी आयु (remaining useful life), बैलास्ट प्रतिरोध (ballast resistance).

### 4.5 Roles and permissions (front-end view)

Roles are enforced server-side. The client uses them to shape the experience, never as a security boundary.

| Capability | Technician | SSE / Sig | Section engineer | Divisional control | CRIS/RDSO | OEM | Leadership |
|---|---|---|---|---|---|---|---|
| View division queue | own tasks | section | section group | division | all | contracted assets | aggregate |
| Acknowledge / snooze | own task | yes | yes | no | no | no | no |
| Create SMMS draft | from field | yes | yes | no | no | no | no |
| Defer a Critical | no | yes, with reason | yes | no | no | no | no |
| View model health | summary | summary | summary | summary | full | own models | summary |
| Record assurance review | no | no | no | no | yes | no | no |
| Export pack | no | yes | yes | yes | yes | yes | yes |

A capability the role lacks is **absent**, not disabled, when its absence is structural (e.g., a technician never sees a "defer Critical" control). It may be disabled with an explanation when the action exists but is temporarily unavailable (e.g., SMMS offline).

---

## 5. Information architecture and routes

### 5.1 Shape of the product

Two shells, one design language:

- **Control shell** — persistent top bar, left rail, status bar. Used by command centre, queue, circuit detail, clusters, model health, design system.
- **Field shell** — no rail, large top bar, sticky action footer, light theme. Used by the field task route on tablets and phones.

The field route is a separate shell, not a responsive collapse of the control shell. It shares tokens and primitives, but its layout, targets and copy are authored for the field.

### 5.2 Route table

| Route | Screen | Shell | Primary question | Data |
|---|---|---|---|---|
| `/` | Command centre | Control | What needs attention across the division this week? | Alerts summary, spine, clusters, blocks |
| `/alerts` | Alert queue | Control | What do I work next, and why in this order? | Paged alerts, saved views, counts |
| `/alerts/:alertId` | Alert triage (drawer over queue) | Control | What is this one alert and what are my options? | Single alert + explanation |
| `/assets/:assetId` | Circuit detail | Control | What is happening to this asset and what should be done? | Asset, telemetry, RUL, explanation, cluster, blocks |
| `/clusters` | Common cause | Control | Which physical causes explain multiple alerts? | Clusters, members, shared edges |
| `/blocks` | Rolling Block planner | Control | What work fits the blocks already published? | Block windows, jobs, crew |
| `/models` | Model health | Control | Can I trust the scores I am acting on? | Metrics, calibration, drift, registry |
| `/field` | Field task list (offline) | Field | What is my next job, and can I do it without signal? | Cached tasks, outbox |
| `/field/tasks/:taskId` | Field confirmation | Field | What did I find, and how do I record it? | Task, measurements, draft |
| `/design` | Design system | Control | How do I build another screen correctly? | Static reference |
| `/search` | Global search | Control | Where is this asset, alert or SMMS record? | Federated search |

The mockups implement `/`, `/alerts`, `/assets/:id`, `/models`, `/design`, `/field/tasks/:id` and a cover/gallery route.

### 5.3 Navigation model

The rail has three groups and eight items, all visible at 1280 px and above:

- **Operate:** Command centre, Alert queue (count), Circuit detail, Common cause (count).
- **Assure:** Model health, Field app.
- **Reference:** Design system, Cover & gallery.

Counts are live objects, not badges for their own sake. The queue count is the number of open alerts in the user's scope; the cluster count is the number of open clusters. If the count is zero, the count disappears rather than showing "0".

The top bar carries: current scope as a breadcrumb (`SER / ADRA / ADRA YARD`), the advisory chip, global search (`⌘K` / `Ctrl K`), live freshness, language toggle, and the signed-in role. The status bar carries: the advisory statement, SMMS link state, model versions, and IST clock.

### 5.4 Scope and breadcrumbs

Scope is a first-class filter, not a page title. Changing scope from `SER / ADRA` to `SER / ADRA / ADRA YARD` changes the queue, spine and blocks; it does not navigate. The breadcrumb is therefore interactive in the real product, with a scope picker on each segment. The mockups show the result, not the picker.

### 5.5 Global search

`⌘K` opens a command palette that searches assets, alerts, clusters and SMMS IDs. Results are grouped and keyboard-navigable. Search never executes a command; it navigates. The palette is the only global overlay, and it closes on `Esc` with focus returned to the invoking control.

### 5.6 Routes not to build

- A dashboard of charts with no action.
- A "model insights" page that exposes raw feature tables to operators.
- A settings page that lets a user change alert thresholds. Thresholds are governed, versioned and signed; the UI may show them, not edit them.
- Any route that ends in "apply to interlocking".

---

## 6. Signature interaction patterns

Four patterns carry the product. They must be built once, documented, and reused; variants are how design systems decay.

### 6.1 Signal Spine

**Purpose.** One ordered line through a scope, showing state by shape and rank by number, with enough metadata to decide whether to open the row.

**Anatomy.** A vertical hairline; one node per asset; node shape encodes state (hollow ring = Watch, filled triangle = Warning, diamond with dark core = Critical, solid dot = Nominal); identifier in mono; route/asset metadata; risk value; a 54 px bar. The line fades at the bottom to signal continuation.

**Rules.**
- The spine is always ordered by the same priority function as the queue.
- A row is a link, not a checkbox; selection belongs to the queue.
- The state glyph appears once per row (the node), not again inside the label.
- Risk text is tabular and right-aligned; the bar is supplementary, never the only value.
- Maximum eight rows in the command-centre panel; the full set is the queue.

**Why it works.** It converts a table into a place. The eye follows the line, and the shape differences survive greyscale, colour-blindness and a bad projector.

**Component contract.**

```ts
type AlertLevel = "watch" | "warning" | "critical" | "nominal";

interface SpineItem {
  assetId: string;
  route: string;          // "Down Goods"
  lengthM: number;
  likelyMode?: FailureModeCode;
  level: AlertLevel;
  risk7d: number;         // 0..1
  href: string;
}

interface SignalSpineProps {
  items: SpineItem[];
  label?: string;         // "Section spine"
  stage?: "purvarupa" | "nidana" | "samprapti" | "upasaya";
  onOpen?: (assetId: string) => void;
}
```

### 6.2 The three-lens Explanation Card

**Purpose.** Make a score interrogable without a data-science translator.

**Structure.** A tablist with three lenses, each with a Devanagari micro-label and an English name:

1. **Physics** — a plain-language claim, the twin's state table, environmental facts that changed, and an explicit falsifier ("if insulation falls below 0.5 MΩ the ranking moves to F2").
2. **Model** — signed SHAP contributions in log-odds, calibration context, conformal set, agreement between models, and a warning that risk is not to be multiplied by cost.
3. **Precedents** — three nearest confirmed SMMS cases, similarity scores, and a feedback control that trains the precedent index only.

**Rules.**
- The card sits next to the recommendation on the same screen.
- The default lens is Physics; the model is never the first thing an operator sees.
- Numbers carry units and horizons. "−0.41" is labelled as a log-odds contribution, not a percentage.
- SHAP is rendered as signed bars around a centre line, with direction readable in text.
- The falsifier is mandatory. A hypothesis without a falsifier is an assertion.
- Feedback on a precedent never retrains the risk model; it trains the retrieval index.

**Why it works.** It matches how an SSE actually reasons: what is the physical story, what does the model think, and has this happened before? The order is deliberate.

### 6.3 RUL band

**Purpose.** Replace a false point estimate with a decision-shaped interval.

**Anatomy.** Horizontal day axis; a p10–p90 band; a median tick and dot; a threshold line at 30 days; a highlighted Rolling Block window; today marker; direct labels for p10, median and p90. No legend is required.

**Rules.**
- The band is the visual subject, not the median.
- The block window is shown in the chart because it is the decision.
- If the block falls inside p10, the copy says so; if it falls outside, the copy says that too.
- The chart is an `<svg role="img">` with an accessible summary naming all three values and the block.
- A table equivalent is available for screen readers and print.

### 6.4 Rolling Block fit row

**Purpose.** Make the railway's time visible in every recommendation.

**Anatomy.** Date and window; job title; assets and cluster; duration; a fit chip (`fits 90′`, `+20′`, `Special`, `Monitor`); a consequence line if deferred.

**Rules.**
- "Fits" means inside the published window with the stated duration and crew.
- Any extension is explicit (`+20′`), never implied.
- "Special" is a warning, not a failure; it carries a red chip because it consumes a scarce resource.
- The row never offers "request block" as a casual action; it opens a draft with the block details pre-filled and requires SSE confirmation.

### 6.5 Pattern anti-patterns

| Avoid | Because |
|---|---|
| Donut charts of failure modes | Parts of a whole are not the decision; use ranked bars |
| Gauges for risk | They imply a limit and a control loop that do not exist |
| Pulsing Critical rows | Motion draws the eye to the wrong thing and exhausts attention |
| Gradient heat maps of "health" | Colour-only encoding, and "health" hides the failure mode |
| Sparkline without a baseline | A line that rises is meaningless without the dry reference |
| A "confidence" percentage without calibration | False precision; use ECE and coverage |
| A disabled control path | Suggests the system could control the railway if permitted |

---

## 7. Screen specifications

Each specification states the question, the layout contract, the data on screen, the interaction model and what is deliberately absent. Screenshot filenames refer to `design/mockups/screenshots/`.

### 7.1 Command centre — `/` (`pages/command-center.html`, screenshot `01-command-center.png`)

**Question it answers:** what needs attention across this division in the next seven days, and in what order?

**Layout**

| Band | Grid | Content |
|---|---|---|
| Page header | 12 | Eyebrow `SER / ADRA / ADRA YARD`, title, scope chips, `Export pack` and `Refresh` actions |
| KPI strip | 4 × 3 | Open alerts (11), Critical this shift (1), Cluster-adjusted work (5), Rolling Block fit (78%) |
| Working band | 5 / 7 | `Section spine` (left, 5 columns) and `Propagation map` (right, 7 columns) |
| Cluster band | 5 / 7 | `Common cause` cluster list and its supporting summary |
| Queue | 12 | `Priority queue`, eight rows, one action per row |
| Blocks | 12 | `Rolling Block · week 29`, seven-day strip with work fitted into published windows |

**Data on screen.** Eleven open alerts; four KPI values with deltas; the spine ordered by the priority function; the propagation map showing 12T→14T→16T as cluster `c-9917` and 21T as predicted cascade; a queue whose first row is `ADRA/TC/12T`, risk 24% at 7 d, RUL p10 9 d, fit `RB-28 · 90 min`.

**Interaction model**
- Spine rows are links to `/assets/:assetId`; the whole row is the target, not the identifier.
- Queue rows select on click and open on `Enter`; selection is single, never multi, because the action is per-asset.
- Hover raises the row by background only (no lift, no shadow) so the line of the spine is not broken.
- `Refresh` requests a new server snapshot; it does not recompute risk in the browser.
- The KPI strip is a filter control in the real product: selecting `Critical` filters the queue and the spine together. The mockup shows the resulting state.

**What is absent.** No chart wall, no map of the whole zone, no traffic-control affordance, no "resolve all" bulk action. Bulk action lives in the queue, where an operator has already chosen a filter and can see the selection.

### 7.2 Circuit detail — `/assets/:assetId` (`pages/circuit-detail.html`, screenshot `02-circuit-detail.png`)

**Question it answers:** what is happening to this asset, what is the physical story, and what should be done inside which block?

**Layout, in reading order**

1. **Asset header** — identifier in mono (`ADRA/TC/12T`), plain-language location (`Adra Yard · Down Goods`), level badge, data trust, and a link back to the queue.
2. **Diagnostic stage rail** — Pūrvarūpa, Nidāna, Samprāpti, Upaśaya, with the current stage marked; this is navigation within the page, not decoration.
3. **Remaining useful life** — the band as the visual subject, p10/median/p90 as direct labels, the Rolling Block window plotted, the risk curve for 24 h / 72 h / 7 d, and the conformal coverage statement.
4. **Explanation** — three tabs: Physics, Model, Precedents. Default is Physics.
5. **Signals** — four sparklines with dry baseline: relay current, ballast conductance, feed voltage, cable insulation. Each has a stated normal band.
6. **Likely failure mode** — F1 at 0.71 with the conformal set `{F1, F4}` at 0.90 coverage, plus the two exclusions that matter (F2 joint, F5 relay).
7. **Cluster** — `c-9917` with members 12T, 14T, 16T, shared weather cell and drain, and the predicted 21T cascade with a date range.
8. **Recommended action** — ballast clearing and drain rodding, 90 minutes, inside `RB-28` (16 Jul, 02:10–03:40), with the consequence of deferral.
9. **Asset record** — 420 m DC, installed 2009, codal life 15 y, relay, IPS, cable, relay room, weather cell, data trust 0.62 with the `age_vs_signature_mismatch` flag, and provenance.

**Interaction model**
- Tabs are a real ARIA tablist: `←`/`→` move, `Home`/`End` jump, focus follows selection.
- Each tab panel is mounted lazily but kept after first visit; switching back must not re-fetch.
- The RUL band has a table equivalent behind a `Show as table` control and an `aria-label` summary.
- `Draft SMMS entry` is the primary action. It opens a pre-filled draft; it does not submit work.
- Data trust is a link to the data-quality explanation, not a tooltip.

**What is absent.** No "acknowledge" on the detail page (acknowledgement is a queue or field act), no manual level change, no free-text diagnosis box that could be mistaken for the record of work. The asset record is read-only; SMMS remains the system of record.

### 7.3 Alert queue — `/alerts` (`pages/alert-queue.html`, screenshot `03-alert-queue.png`)

**Question it answers:** what do I work next, and why is it ranked above the row below it?

**Layout**

| Band | Content |
|---|---|
| Header | Title, scope, queue counts by level, saved-view selector |
| KPI strip | Open (11), Critical (1), Watch (7), Median age (3.2 h) |
| Filter bar | Level, failure mode, route, cluster, block fit, data trust, saved view, search |
| View tabs | `Triage`, `By cluster`, `By block`, `Deferred` |
| Bulk bar | Appears on selection: count, `Assign`, `Merge to cluster`, `Defer`, `Export` |
| Table | 10 rows, dense: level, asset, route, mode, risk 24 h / 72 h, RUL p10, cluster, block fit, age |
| Side panel | Selected alert summary, `Why this order`, queue discipline note |

**Table rules**
- Level is rendered as shape + word + colour; sorting by level sorts by the policy rank, not the alphabet.
- Risk cells are tabular numerals with the horizon in the column header, never repeated per cell.
- RUL shows the p10 with the median in the tooltip and in the drawer; p10 is the planning number because it is the conservative one.
- Block fit is a chip with three values: `fits`, `+20 min`, `special`. Missing data renders `—` with an accessible label `no block data`, not a blank cell.
- Rows are 44 px on desktop, 56 px on touch; the whole row is clickable and `Enter` opens the drawer.

**Bulk action safety**
- Bulk selection is capped at 50 rows and the bulk bar always states the count.
- `Defer` requires a reason and a review date; a `Critical` row cannot be deferred in bulk.
- `Merge to cluster` previews the resulting cluster membership before committing.
- The table keeps its scroll position after an action; the acted rows leave with a 90 ms fade and the count updates optimistically with rollback on failure.

**Why this order.** A persistent, collapsible panel explains the ranking in words: risk × consequence × exposure, discounted by data trust, with block fit as a tie-breaker. It names the weights in the interface so an SSE can argue with the ranking rather than guess at it.

### 7.4 Field confirmation — `/field/tasks/:taskId` (`pages/field-tablet.html`, screenshot `04-field-tablet.png`)

**Question it answers:** what am I checking, what did I find, and how do I record it without signal?

**Deliberate differences from the control shell**

| Dimension | Control | Field |
|---|---|---|
| Theme | Deep ink | Warm paper `#F4F3EE`, white cards, 2 px borders |
| Targets | 32 px controls, 44 px rows | 56 px minimum, 16 px gaps |
| Type | 13.5 px body | 16–18 px body, 24 px task title |
| Chrome | Top bar, rail, status bar | Single top bar, sticky footer, no rail |
| Colour | Teal accent on dark | Deep teal `#06645E` on light, amber `#7A4A00`, red `#8F1116` |
| Content | Dense tables | One task, three steps, one decision at a time |

**Layout**
1. **Top bar** — back, asset and task, offline state, language toggle (`EN | हिं`).
2. **Task card** — `ADRA/TC/12T`, 420 m, Down Goods, block `RB-28` 02:10–03:40, level Watch, and the one-line hypothesis with the falsifier.
3. **Step 1 — Measurements** — four large numeric fields with units, a numeric keypad, a `Use last reading` affordance, and a camera placeholder for the ballast crib.
4. **Step 2 — Finding** — three glove-sized choices: `Confirmed`, `Not found`, `Something else`. Selecting one reveals only the relevant follow-up.
5. **Step 3 — Confirm** — a summary of what will be written, the SMMS draft fields, and the single `Queue offline` primary action. No multi-page wizard.
6. **Sticky footer** — last sync time, `Save draft`, `Queue & continue`.

**Offline contract**
- Every measurement is written to IndexedDB on blur, not on submit.
- The outbox is visible: a badge says `3 queued offline`.
- The confirm action is idempotent; a replayed request returns the original receipt.
- If the device is online, the action still writes to the outbox first and syncs immediately, so the code path is identical in both states.
- Conflict rule: server wins on the SMMS record, device wins on the technician's own observations; a conflict is surfaced as a merge task, never silently resolved.

**What is absent.** No charts, no SHAP, no cluster graph, no rail. The technician is not asked to interpret the model; they are asked to confirm or refute one physical claim and record what they saw.

### 7.5 Model health — `/models` (`pages/model-health.html`, screenshot `05-model-health.png`)

**Question it answers:** can I trust the scores I am acting on, and what would make me stop trusting them?

**Layout.** Four KPI tiles (ECE 0.031, coverage 0.897, registry 5 active, drift 1 monitor amber), then:
- `Reliability diagram` — predicted vs observed with the diagonal and bin counts.
- `Calibration by level` — predicted/observed/n per level, lead time by level, and the deliberate conservatism of the Critical band.
- `Registry` — five models with version, trained date, data window, owner and status, in one horizontal band.
- `Performance by failure mode` — precision/recall for F1–F6 with counts, so a weak mode is visible.
- `Drift monitors` — PSI per feature group with thresholds and a state.
- `Data trust` — division-level trust, flag counts, and the rule that low trust is displayed, never suppressed.
- `Promotion gates` — four gates (calibration, coverage, subgroup parity, shadow period) with pass/fail and the signature line.

**Interaction model.** Metrics are static snapshots with a stated as-of time and window; there is no live ticker. A `Why this threshold?` control opens the policy text that governs each gate. The page never offers a control to promote, roll back or retrain: those are governed actions in the MLOps plane, and the UI is evidence for a review, not the review itself.

**Honesty rules.** Every metric names its window and its denominator. ECE is shown with the number of bins. Coverage states held-out outcomes. Drift is a monitor, not a verdict. The Critical band's conservatism is stated in words, not hidden in a footnote.

### 7.6 Design system — `/design` (`pages/design-system.html`, screenshot `06-design-system.png`)

A single long reference page, not an app viewport: ten sections covering colour, type, spacing, state language, components, data display, motion, accessibility, bilingual vocabulary and voice.

**Rules for this page**
- It uses the production tokens and components, never copies. If a token changes, this page changes.
- It is the only page allowed to show every state side by side, because its job is comparison.
- It documents the negative space: what a component must not be used for.
- The risk/meter, RUL band and Signal Spine specimens are live markup, not images.

### 7.7 Cover and gallery — `/` in the mockup set (`pages/index.html`, screenshot `00-cover.png`)

The argument before the screens: the thesis, the seven surfaces, the shared dataset note, and a numbered gallery linking each screen to its HTML and screenshot. It exists to make the set reviewable in one scroll and to state the advisory limit before anyone sees a control-room screen.

### 7.8 Screen-state matrix

Every route must be built in five states. The mockups show the populated state; the build must implement all five.

| State | Command centre | Circuit detail | Queue | Field | Model health |
|---|---|---|---|---|---|
| Loading | KPI skeleton, spine shimmer off (static bars), 180 ms max before spinner | Panel skeletons, RUL placeholder axis | Table skeleton, 8 rows | Cached task or `Loading task…` | Last snapshot + `as of` |
| Empty | `No open alerts in scope` + scope reset | `No telemetry in 30 days` + data-trust explanation | `Nothing matches these filters` + clear filters | `No tasks assigned` | `No evaluation window` |
| Stale | Amber `as of 14:26` chip, values dimmed 20% | Amber provenance banner | Header chip + disabled bulk actions | `Last sync 14:26` in footer | Window label turns amber |
| Partial | Failed panels isolate; spine renders if queue does | Explanation tab failure falls back to Physics | Table renders without block column | Measurements only, confirm disabled | Metrics render, gates marked `unknown` |
| Error | Retry panel, scope preserved | Retry per panel | Retry, filters preserved in URL | Outbox retained, retry on reconnect | Retry, snapshot timestamp kept |

**Rule:** a stale number is more dangerous than no number, so every stale surface says how old it is and what it cannot be used for.

---

## 8. Design tokens and theming

### 8.1 Why tokens are CSS custom properties, not a JS theme object

The product ships two themes (control and field) and must survive 200% zoom, print, and a future high-contrast mode. CSS custom properties give theme switching without a re-render, let SVG inherit colour, and keep the static mockups and the React build on one source of truth. Tailwind v4 is configured to consume the same variables rather than introduce a parallel scale.

### 8.2 Token architecture

Three tiers, strictly one-directional:

1. **Primitive ramp** — raw values (`--ink-900`, `--teal-400`, `--s-4`). Never referenced by a component.
2. **Semantic token** — role (`--bg-panel`, `--text-mid`, `--border-strong`, `--level-critical`). This is what components use.
3. **Component token** — only where a component needs a local degree of freedom (`--spine-node`, `--band-fill`). Must default to a semantic token.

If a component reaches past tier 2 into tier 1, the theme cannot be inverted and the field mode breaks. This is the single most common failure in dark-first design systems, and it is why the field theme is part of the token file from day one rather than a later "light mode" project.

### 8.3 Colour

The base is a surface ramp, not a palette of unrelated swatches. Each step is a real surface in the interface, so a reviewer can point at a colour and name its job.

```css
/* Tier 1 — primitives (excerpt) */
--ink-950: #060C12;  --ink-900: #080F16;  --ink-850: #0B1420;
--ink-800: #0E1822;  --ink-750: #12202C;  --ink-700: #16262F;
--ink-600: #1A2C3A;  --ink-500: #24384A;

--teal-300: #7CF3E4; --teal-400: #38E0CE; --teal-500: #17C6B6;
--teal-600: #0DA294; --teal-700: #0A7F76; --teal-800: #075C56;

--amber-300: #FFE0A3; --amber-400: #F9BE5C; --amber-500: #EDA22E;
--amber-600: #C67F1B;

--red-300: #FFA0A3;  --red-400: #FF6B70;  --red-500: #E8474D;
--red-600: #C3343A;

--ok-400: #6EE7C0;   --ok-500: #46CBA0;   --ok-600: #2FA37E;

/* Tier 2 — semantic */
--bg-app: var(--ink-950);
--bg-chrome: var(--ink-900);
--bg-panel: var(--ink-800);
--bg-raised: var(--ink-750);
--bg-inset: #0A1420;
--bg-hover: rgba(255, 255, 255, 0.035);
--bg-active: rgba(56, 224, 206, 0.09);

--text-hi: #EFF6FB;
--text-mid: #A8BECD;
--text-lo: #7A93A5;
--text-inv: #04121A;

--border: #1A2C3A;
--border-strong: #2A4256;
--border-subtle: rgba(255, 255, 255, 0.06);
--focus-ring: #7CF3E4;

--level-watch: var(--teal-400);
--level-warning: var(--amber-400);
--level-critical: var(--red-400);
--level-nominal: #5E7A8A;
```

**Usage law**

| Token | May be used for | Never used for |
|---|---|---|
| Teal | Live/current state, primary action, nominal, focus | Decorative fills, success on a destructive action, "everything is fine" |
| Amber | Warning level, uncertainty, stale data | Body text, secondary actions, hover |
| Red | Critical level, destructive confirmation, wrong-side risk | Any decorative element, all errors including validation |
| Nominal grey-teal | Nominal state dot, disabled text | Nominal state as colour alone |

Reduced-saturation variants exist for fills (`--red-wash`, `--amber-wash`) so a Critical row can be tinted without becoming a wall of red. Text on a wash always uses the 300-level colour, which is the only variant verified for contrast on the wash.

### 8.4 Type, space, radius, elevation, motion

```css
--font-latin: "Inter", "Segoe UI", system-ui, sans-serif;
--font-deva: "Noto Sans Devanagari", "Nirmala UI", "Mangal", var(--font-latin);
--font-mono: "JetBrains Mono", "Cascadia Mono", ui-monospace, Consolas, monospace;

--fs-display: 34px; --lh-display: 38px;
--fs-h1: 25px;      --lh-h1: 31px;
--fs-h2: 18px;      --lh-h2: 24px;
--fs-h3: 14.5px;    --lh-h3: 20px;
--fs-body: 13.5px;  --lh-body: 20px;
--fs-sm: 12px;      --lh-sm: 17px;
--fs-xs: 11px;      --lh-xs: 15px;
--fs-micro: 10px;   --lh-micro: 13px;

--s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px;
--s6: 24px; --s7: 32px; --s8: 40px; --s9: 48px; --s10: 64px;

--r-xs: 3px; --r-sm: 5px; --r-md: 8px; --r-lg: 12px; --r-xl: 16px;

--dur-1: 90ms; --dur-2: 140ms; --dur-3: 200ms; --dur-4: 280ms;
--ease-out: cubic-bezier(0.22, 0.61, 0.36, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

**Rules.** Spacing is 8-point with a 4 px and 2 px sub-step for dense controls only. Radii are small because the product is an instrument; a 16 px radius on a data table reads as a consumer app. Elevation is one hairline plus ambient shadow; there is no glass, no blur, no glow. Motion durations are short enough to feel like state change rather than animation.

### 8.5 The field theme

The field theme is a semantic remap, not a filter:

```css
.theme-field {
  color-scheme: light;
  --bg-app: #F4F3EE;
  --bg-chrome: #FFFFFF;
  --bg-panel: #FFFFFF;
  --bg-inset: #ECEBE4;
  --bg-hover: rgba(9, 30, 38, 0.05);
  --text-hi: #0C161C;
  --text-mid: #33454F;
  --text-lo: #4E626C;
  --border: #C9CCC6;
  --border-strong: #9AA39F;
  --focus-ring: #06443F;
  --teal-400: #06645E;
  --amber-400: #7A4A00;
  --red-400: #8F1116;
  --touch-min: 56px;
  --r-sm: 6px; --r-md: 10px; --r-lg: 14px;
}
```

Every component that hard-codes `#FFFFFF` or a dark chip background is a bug in this theme. The stylesheet therefore restates chips, level labels and glyph cores under `.theme-field`; the same obligation applies in React, where a component that uses a raw hex value fails review.

**Contrast verification (measured, not asserted)**

| Pair | Ratio | Use |
|---|---|---|
| `#EFF6FB` on `#060C12` | 18.0:1 | Body on app |
| `#A8BECD` on `#0E1822` | 9.3:1 | Secondary on panel |
| `#7A93A5` on `#0E1822` | 5.6:1 | Tertiary labels, 11 px |
| `#38E0CE` on `#060C12` | 11.9:1 | Teal text and links |
| `#0DA294` on `#0E1822` | 5.6:1 | Teal borders/icons |
| `#F9BE5C` on `#0E1822` | 10.7:1 | Warning text |
| `#FF6B70` on `#0E1822` | 6.5:1 | Critical text |
| `#0C161C` on `#FFFFFF` | 18.3:1 | Field body |
| `#06645E` on `#FFFFFF` | 7.0:1 | Field teal |
| `#7A4A00` on `#F4F3EE` | 6.7:1 | Field warning |
| `#8F1116` on `#FFFFFF` | 9.3:1 | Field critical |

The weakest link is tertiary text at 5.6:1, still above the 4.5:1 requirement; it is never used below 11 px, and never for a number that carries a decision.

### 8.6 Theming rules for the build

1. Theme is set on `<html data-theme="control|field">`, not on a component.
2. The field route is the only place the field theme is applied; a user cannot browse the control surface in field theme.
3. `color-scheme` is declared per theme so native controls (date pickers, scrollbars) match.
4. Print forces the light palette and hides the shell.
5. No component may define a colour literal. Lint rule: `color-no-hex` inside `src/components/**` except in `*.stories.tsx` and token files.
6. Token names are reviewed like API names: renaming `--text-lo` is a breaking change and requires a codemod.

---

## 9. Typography and the bilingual system

### 9.1 Typefaces

| Role | Face | Why |
|---|---|---|
| Latin UI | Inter (variable) | Open, high x-height, excellent tabular figures at 11–13 px, neutral without being bland |
| Devanagari | Noto Sans Devanagari (variable) | Companion weight range, correct matra shaping, open licence, ships with Chrome on Android as fallback |
| Data | JetBrains Mono | Distinguishes `0/O`, `1/l/I`, clear at 10 px in dense tables; IDs and telemetry are read character by character |
| Numerals in prose | Inter tabular (`font-variant-numeric: tabular-nums`) | Column alignment in tables and KPI deltas |

All three are self-hosted as `woff2` in the mockups (`design/mockups/assets/fonts/`), with `font-display: swap` and a local fallback stack. The build must subset to Latin + Devanagari, preload only the Latin regular and the Devanagari regular, and self-host rather than call a font CDN: the deployment is behind a railway network and may be air-gapped.

### 9.2 Scale

| Token | Size / line | Weight | Use |
|---|---|---|---|
| `--fs-display` | 34 / 38 | 600 | Page title, one per screen |
| `--fs-h1` | 25 / 31 | 600 | Asset identifier on detail |
| `--fs-h2` | 18 / 24 | 600 | Panel title |
| `--fs-h3` | 14.5 / 20 | 600 | Sub-panel, card title |
| `--fs-body` | 13.5 / 20 | 400 | Default |
| `--fs-sm` | 12 / 17 | 400 | Table body, secondary |
| `--fs-xs` | 11 / 15 | 500 | Labels, chips, captions |
| `--fs-micro` | 10 / 13 | 600 | Eyebrows, axis ticks — never content |

The scale is deliberately compressed. A control room is viewed at 60–100 cm, often on a 1080p wall display; a 16 px body would force scrolling and hide the queue. The field theme overrides body to 16 px and the task title to 24 px, because the viewing distance is 30–50 cm in sunlight.

**Rules.**
- No text below 10 px. 10 px is reserved for axis ticks and eyebrows, never for a value.
- Body copy is capped at 72 characters; explanatory prose at 68–72; table cells do not wrap more than two lines.
- Numbers use tabular figures and a fixed decimal policy: risk as whole percent in tables, one decimal in explanation, RUL in whole days.
- Headings are sentence case. Eyebrows are uppercase with `0.085em` tracking, never more than four words.
- Numerals in Hindi copy stay Latin (`24%`, `9 दिन`), because the source data and SMMS are Latin-numeral systems. Devanagari numerals are available as an option, not the default.

### 9.3 Devanagari rules

Devanagari is not a fallback font applied to a Latin layout. It has different vertical metrics, conjuncts and matras that collide with tight line heights.

- Line height for Devanagari is at least 1.6× the font size (the field theme uses 26 px for 16 px text).
- Never apply `text-transform: uppercase` or positive letter-spacing to Devanagari; both break conjuncts and look wrong.
- Never truncate a Devanagari label with `…`; shorten the copy instead.
- Devanagari sits on the same baseline as Latin but needs 2–4 px more block padding above; test with matras (`ि`, `ी`) and conjuncts (`क्ष`, `ज्ञ`).
- Labels are paired as `English` then `देवनागरी` on a second line, or inline separated by a middle dot with the Devanagari at the same size — never smaller, never greyed to the point of illegibility.
- Font weight: Devanagari at 600 reads heavier than Inter at 600. Use 500 for Devanagari equivalents of Latin 600 headings.

### 9.4 Bilingual strategy

The product is bilingual where it matters, not everywhere.

| Surface | Bilingual? | Rationale |
|---|---|---|
| Field task, confirm, error, safety copy | Yes, always | The technician's working language may be Hindi; safety copy must not depend on English |
| Navigation and page titles | Yes (label pair) | Orientation |
| Domain terms (track circuit, relay room, block) | Yes, once per screen, then English | Prevents a page of duplicated text |
| Model metrics, SHAP labels, asset IDs | No | They are identifiers and data-science vocabulary; translating them creates false fluency |
| Legal/advisory statement | Yes | It is the most important sentence in the product |

Implementation: `i18next` with `en` and `hi` bundles, key namespaced by route (`field.confirm.title`). A `Bilingual` component renders the pair with correct `lang` attributes:

```tsx
<p className="pair">
  <span lang="en">Ballast resistance below dry baseline</span>
  <span lang="hi">गिट्टी प्रतिरोध सूखे आधार से नीचे</span>
</p>
```

`lang` attributes matter for screen-reader pronunciation and for font fallback; a `<span lang="hi">` inside an English page is what tells the browser to use Noto Sans Devanagari with the right shaping.

### 9.5 Voice

The copy is calm, specific and never more certain than the model.

| Instead of | Write |
|---|---|
| "Critical failure imminent" | "Critical · 52% chance within 24 h. Relay margin is 41% of dry." |
| "Asset unhealthy" | "Ballast conductance is 31% above its dry baseline." |
| "AI detected an anomaly" | "The twin and the classifier agree on F1; the survival model puts p10 at 9 days." |
| "Action required" | "Draft a 90-minute ballast clearing for RB-28." |
| "Error 500" | "The queue could not be refreshed. Your filters are safe. Retry, or use the 14:26 snapshot." |
| "Success!" | "Queued. 3 items will sync when the device reconnects." |

Two hard rules: never use "predicts" for a probability without a horizon, and never use "will fail".

---

## 10. Accessibility and inclusive field use

Accessibility is treated as shift safety, not compliance. A supervisor who cannot read a Critical row at 02:40 is an operational defect.

### 10.1 Conformance target

WCAG 2.2 Level AA across both themes, plus the following internal requirements that exceed AA:

| Requirement | Internal standard | Why |
|---|---|---|
| Target size | 44 × 44 px control, 56 × 56 px field | Gloves, vibration, walking |
| Contrast | 7:1 for body, 4.5:1 minimum for any text, 3:1 for UI boundaries | Sunlight and cheap panels |
| Zoom | Usable at 400% zoom / 320 px reflow, no horizontal scroll | Low-vision users and split-screen control desks |
| Motion | `prefers-reduced-motion` removes all transitions; nothing animates for more than 280 ms | Vestibular and attention |
| Live data | No auto-updating number without a visible timestamp and a pause control | Comprehension under pressure |
| Focus | 2 px ring plus 1 px offset, never obscured by sticky chrome | Keyboard-first triage |

### 10.2 Criterion-by-criterion implementation

| WCAG 2.2 criterion | Where it applies | Implementation |
|---|---|---|
| 1.1.1 Non-text content | Level glyphs, sparklines, RUL band, propagation map | Level glyph is decorative when the word is adjacent (`aria-hidden`); charts are `role="img"` with a full-sentence label and a table equivalent |
| 1.3.1 Info and relationships | Tables, explanation tabs, stage rail | Real `<table>` with `<th scope>`; ARIA tablist; ordered list for stages |
| 1.3.2 Meaningful sequence | Detail page | DOM order is reading order: RUL → explanation → signals → mode → cluster → action → record |
| 1.4.1 Use of colour | Every level, block fit, drift state | Shape + word + number; tested in greyscale |
| 1.4.3 Contrast | All text | Measured ratios in §8.5; CI contrast test on token pairs |
| 1.4.4 Resize text | 200% | Rem-based type scale, no fixed-height text containers |
| 1.4.10 Reflow | 320 px | Single-column collapse; table becomes definition list under 720 px |
| 1.4.11 Non-text contrast | Inputs, chips, spine nodes, focus | ≥3:1 against adjacent surface |
| 1.4.12 Text spacing | All prose | No fixed line-height containers; tested with 1.5 line-height, 0.12em letter-spacing |
| 2.1.1 Keyboard | Everything | No pointer-only action; row open, tab switch, drawer, filter, bulk select all keyboard reachable |
| 2.1.2 No keyboard trap | Drawer, palette | `Esc` always closes; focus returns to the invoking control |
| 2.2.2 Pause, stop, hide | IST clock, live counts | Motion removed; updates are announced, not animated |
| 2.3.3 Animation from interactions | Tabs, drawer | Transform/opacity only; reduced-motion instant |
| 2.4.3 Focus order | Queue → drawer | Focus moves into the drawer, `Tab` cycles within it, `Esc` restores the row |
| 2.4.7 Focus visible | All | `:focus-visible` 2 px `--focus-ring` with 1 px offset; never `outline: none` alone |
| 2.4.11 Focus not obscured (AA, 2.2) | Sticky header/footer | Scroll padding equals chrome height; tested at 400% |
| 2.5.7 Dragging movements | RUL band brush (if added) | Drag has a keyboard equivalent (arrow keys move the cursor) |
| 2.5.8 Target size minimum (AA, 2.2) | All controls | 44 px minimum exceeds the 24 px requirement |
| 3.2.6 Consistent help | Footer, errors | Advisory statement and `Contact section control` in the same place on every screen |
| 3.3.2 Labels or instructions | Field measurements | Visible label, unit, and a format hint; no placeholder-as-label |
| 3.3.7 Redundant entry (A, 2.2) | Field confirm | Measurements persist across steps; the user never retypes |
| 3.3.8 Accessible authentication | Not applicable | No cognitive test; SSO with passkey/TOTP supported by the platform |
| 4.1.2 Name, role, value | Custom tabs, chips, glyphs | Native elements first; Radix primitives where a native element cannot carry the role |
| 4.1.3 Status messages | Queue actions, offline sync | `role="status"` polite region; Critical announcements use `assertive` once, never repeated |

### 10.3 Colour independence: the shape system

Four states, four silhouettes, always paired with a word and a number:

| State | Shape | Word | Additional signal |
|---|---|---|---|
| Nominal | 8 px solid dot, grey-teal | `Nominal` | No risk number shown in the spine |
| Watch | 10 px hollow ring, teal | `Watch` | Risk % in teal |
| Warning | 11 px filled triangle, amber | `Warning` | Risk % in amber + `▲` in text where compact |
| Critical | 11 px filled diamond with dark core, red | `Critical` | Risk % in red + `◆` in export/print |

The shapes are distinguishable at 10 px, in greyscale, and by shape alone. Screen readers get the word, never the shape. Exports and printed alert packs use the text token (`◆ Critical`) because SVG glyphs do not survive a photocopier.

### 10.4 Chart accessibility

Every data visualisation has three layers:

1. **Visible:** the chart, with direct labels rather than a legend.
2. **Text alternative:** `aria-label` stating the decision, not the geometry — *"Remaining useful life: 10th percentile 9 days, median 21 days, 90th percentile 38 days. Rolling Block RB-28 occurs in 2 days, inside the 10th percentile."*
3. **Table equivalent:** a `<table>` behind `Show as table`, in the DOM at all times but visually collapsed, so screen readers and print get exact values.

The RUL band's SVG includes `<title>` and `<desc>`; the sparklines are `aria-hidden` with the current value and baseline in adjacent text, because a sparkline alone is not information.

### 10.5 Keyboard model

| Context | Keys | Behaviour |
|---|---|---|
| Global | `Ctrl/⌘ K` | Command palette; `Esc` closes, focus restored |
| Global | `g` then `c` / `a` / `m` | Go to command centre / alerts / models |
| Rail | `Tab`, `Enter` | Standard link order; skip-link to main is first |
| Queue table | `↑` `↓` | Move row focus |
| Queue table | `Enter` | Open triage drawer |
| Queue table | `Space` | Select row for bulk |
| Queue table | `Shift + Space` | Range select |
| Queue table | `/` | Focus filter search |
| Drawer | `Esc` | Close and restore focus to row |
| Tabs | `←` `→` `Home` `End` | Standard tablist behaviour, activation follows focus |
| RUL band | `←` `→` | Move inspection cursor; value announced |
| Field | Large targets, `Enter` on primary | No chorded shortcuts; gloves and one hand |

Shortcuts are documented in the palette footer and are never single-letter without a modifier when focus is in a text field.

### 10.6 Reduced motion and attention

- `prefers-reduced-motion: reduce` sets all durations to `0.01ms`, disables the drawer slide and the tab crossfade, and keeps the state change instantaneous.
- Nothing loops. The only "live" indicator is a static dot whose colour and label change; it does not pulse.
- New Critical alerts do not animate into the queue. They arrive sorted, with an `aria-live` announcement and a count change in the rail. A row that moves under a user's cursor is a hazard.
- The `Update available` banner is static; it never slides in.

### 10.7 Forms and errors

- Labels are visible and persistent; units are part of the label (`Relay current (mA)`).
- Validation happens on blur and on submit, never on every keystroke.
- Errors are stated in text next to the field, summarised at the top of the form for screen readers, and never rely on a red border. GOV.UK's error-summary pattern is the model.
- Numeric inputs use `inputmode="decimal"`, allow comma or dot, and state the accepted range in the hint.
- Destructive confirmation names the object and the consequence: *"Defer ADRA/TC/12T to 18 Jul? The p10 is 9 days; deferral moves the work past the predicted window."*

### 10.8 Testing matrix

| Test | Tool | Gate |
|---|---|---|
| Automated axe | `@axe-core/playwright` on every route, both themes | Zero serious/critical |
| Keyboard-only walkthrough | Manual script, 12 tasks | Every task completable |
| Screen reader | NVDA + Chrome (Windows), VoiceOver + Safari (iPad), TalkBack + Chrome (Android field) | Queue triage, detail explanation, field confirm |
| Zoom / reflow | 400% at 1280 px, 320 px viewport | No horizontal scroll; no clipped text |
| Contrast | Token pair test in CI + manual spot check | All pairs pass the stated ratio |
| Greyscale | Screenshot filter on all seven screens | State still readable |
| Reduced motion | OS setting, all routes | No transitions |
| Sunlight | Field tablet at 100% brightness outdoors | Primary action legible at 50 cm |

### 10.9 Known limitations and mitigations

| Limitation | Mitigation |
|---|---|
| Dense tables at 200% zoom | Table collapses to a card list under 720 px; column priority is defined, not arbitrary |
| SVG propagation map is hard for screen readers | Text list of the same edges is always in the DOM; the map is supplementary |
| Devanagari at 10 px | Never used below 12 px; micro labels stay English |
| Colour-blind users and red/amber | Shape + word; amber and red differ in luminance as well as hue (10.7:1 vs 6.5:1) |
| Field gloves and capacitive screens | 56 px targets, no swipe-only actions, no long-press |

---

## 11. Component library and TypeScript contracts

### 11.1 Library shape

- **Primitives** (Button, Input, Select, Checkbox, Radio, Dialog, Tabs, Tooltip, Popover) come from Radix via shadcn/ui, restyled with tokens. They are vendored into `src/components/ui/` so the design system owns the code.
- **Composites** (Panel, KpiTile, LevelBadge, RiskCell, SignalSpine, RulBand, ExplanationCard, BlockFitRow, AlertTable, StageRail, FieldConfirm) are product components, written once, tested once, documented in Storybook.
- **Patterns** (page headers, filter bars, drawers) are compositions, not components, unless they appear three times.

Rules: one job per component; no component fetches data; no component owns a colour literal; every component accepts `className` and forwards `ref`; every interactive component has a keyboard test.

### 11.2 Domain types (`src/types/domain.ts`)

```ts
export type AlertLevel = "watch" | "warning" | "critical";
export type DisplayLevel = AlertLevel | "nominal";

export type FailureModeCode =
  | "F1"  // low ballast resistance
  | "F2"  // insulated / glued joint
  | "F3"  // rail bond, continuity, rail break
  | "F4"  // metallic bridging at points
  | "F5"  // relay ageing
  | "F6"  // power supply / feed
  | "F7"  // lightning / surge
  | "F8"  // cable fault
  | "F9"  // shunting failure (wrong-side risk)
  | "F10" // stray / traction interference
  | "F11" // maintenance / config error
  | "F12"; // no fault found

export interface RiskCurve {
  h24: number;   // 0..1
  h72: number;
  h7d: number;
  eceZone: number; // expected calibration error for this score's bin
}

export interface Rul {
  p10Days: number;
  medianDays: number;
  p90Days: number;
  coverage: number;   // empirical conformal coverage, e.g. 0.897
  heldOutN: number;
}

export interface ShapContribution {
  feature: string;        // "relay_i_slope_7d"
  label: string;          // "Relay current slope, 7 d"
  value: number;          // log-odds contribution, signed
  direction: "increases" | "decreases";
}

export interface PhysicsClaim {
  headline: string;       // "Effective ballast conductance +31% in 12 days"
  state: Array<{ label: string; value: string; baseline?: string }>;
  falsifier: string;      // "If insulation < 0.5 MΩ the ranking moves to F2"
}

export interface Precedent {
  smmsId: string;         // "SMMS-evt-118"
  assetId: string;
  confirmedMode: FailureModeCode;
  similarity: number;     // 0..1
  daysAgo: number;
  outcome: string;
}

export interface Explanation {
  physics: PhysicsClaim;
  model: {
    shapTop: ShapContribution[];
    calibrationNote: string;
    modeSet: FailureModeCode[];
    modeSetCoverage: number;
    agreement: "high" | "partial" | "low";
  };
  precedents: Precedent[];
  modelVersions: { twin: string; gnn: string; survival: string; classifier: string };
}

export interface Cluster {
  id: string;             // "c-9917"
  label: string;          // "Adra Yard drainage"
  rootCause: string;      // "shared drain blockage"
  memberAssetIds: string[];
  sharedFactors: Array<"weather_cell" | "drain" | "feed" | "cable_route" | "relay_room">;
  predictedCascade?: { assetId: string; fromDay: number; toDay: number };
  alertCount: number;     // alerts before merge
}

export interface BlockWindow {
  id: string;             // "RB-28"
  date: string;           // ISO date
  start: string;          // "02:10"
  end: string;            // "03:40"
  durationMin: number;
  kind: "published" | "special";
}

export type BlockFit = "fits" | "extends" | "special" | "none";

export interface Alert {
  id: string;
  assetId: string;
  assetName: string;
  route: string;
  level: AlertLevel;
  risk: RiskCurve;
  rul: Rul;
  likelyModes: FailureModeCode[];
  modeSetCoverage: number;
  clusterId?: string;
  dataTrust: { score: number; flags: string[] };
  block?: { window: BlockWindow; fit: BlockFit; jobMinutes: number };
  explanation: Explanation;
  proposedAction?: { code: string; label: string; minutes: number };
  ageMinutes: number;
  modelVersions: { twin: string; gnn: string; survival: string; classifier: string };
}

export interface TrackCircuitAsset {
  id: string;             // "ADRA/TC/12T"
  yard: string;
  route: string;
  lengthM: number;
  traction: "DC" | "AC";
  installedOn: string;    // ISO
  codalLifeYears: number;
  relayId: string;
  supplyId: string;
  cableId: string;
  relayRoomId: string;
  weatherCell: string;
  dataTrust: { score: number; flags: string[] };
}
```

### 11.3 Shared primitives

```tsx
type LevelBadgeProps = {
  level: DisplayLevel;
  size?: "sm" | "md";
  withLabel?: boolean;   // default true
  className?: string;
};

type RiskCellProps = {
  value: number;             // 0..1
  horizon: "24h" | "72h" | "7d";
  level: AlertLevel;
  showHorizon?: boolean;     // false inside a column with a header
};

type KpiTileProps = {
  label: string;
  value: string | number;
  unit?: string;
  delta?: { value: string; direction: "up" | "down" | "flat"; sentiment: "good" | "bad" | "neutral" };
  hint?: string;
  href?: string;             // makes the whole tile a link
};

type PanelProps = {
  title: string;
  eyebrow?: string;
  actions?: React.ReactNode;
  footer?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  "aria-labelledby"?: string;
};
```

`LevelBadge` renders shape + word, with the shape `aria-hidden`. It is the only component allowed to map level to colour; every other component reads `level` and composes `LevelBadge`. This prevents the "Critical looks amber on one screen" class of bug.

### 11.4 SignalSpine

```tsx
export type SpineStage = "purvarupa" | "nidana" | "samprapti" | "upasaya";

export type SpineItem = {
  assetId: string;
  route: string;
  lengthM: number;
  likelyMode?: FailureModeCode;
  level: DisplayLevel;
  risk7d?: number;
  href: string;
};

export type SignalSpineProps = {
  items: SpineItem[];
  label?: string;                    // "Section spine"
  stage?: SpineStage;
  max?: number;                      // default 8
  emptyMessage?: string;
  onOpen?: (assetId: string) => void;
};
```

```tsx
<SignalSpine
  label="Section spine"
  items={alerts.map(toSpineItem)}
  onOpen={(id) => navigate(`/assets/${encodeURIComponent(id)}`)}
/>
```

Implementation notes:
- Render as `<ol>` with `<li>`; each item contains one `<a>` with the accessible name `"{assetId}, {route}, {level}, {risk7d}% risk in 7 days"`.
- The node shape is a `<span aria-hidden>` sibling of the text, absolutely positioned on the hairline.
- The risk bar is `aria-hidden`; the number is text. A bar without a number is decoration.
- The hairline fades with a mask only in the control theme; the field theme has no spine (field uses a task list).

### 11.5 RulBand

```tsx
export type RulBandProps = {
  rul: Rul;
  maxDays?: number;              // default 42
  block?: { id: string; inDays: number };
  thresholdDays?: number;        // default 30
  showTable?: boolean;           // renders the collapsed table equivalent
  caption?: string;
};
```

The component computes only geometry. Thresholds and interpretation come from props, because the 30-day line is policy and must be changeable server-side without a release.

**Accessibility:** `<figure>` with `<figcaption>`; `role="img"` on the SVG with a sentence summary; `<table class="sr-only">` always present; direct labels for p10, median, p90; the block marker is a labelled line, not a colour swatch. At 320 px the axis reduces to three ticks — never fewer than p10, median, p90.

### 11.6 ExplanationCard

```tsx
export type ExplanationCardProps = {
  explanation: Explanation;
  defaultTab?: "physics" | "model" | "precedents";
  onPrecedentFeedback?: (smmsId: string, useful: boolean) => void;
  onOpenPrecedent?: (smmsId: string) => void;
};
```

```tsx
<ExplanationCard
  explanation={alert.explanation}
  defaultTab="physics"
  onPrecedentFeedback={(id, useful) => precedentFeedback.mutate({ id, useful })}
/>
```

Behaviour:
- ARIA tablist with `aria-controls`; panels are labelled by their tabs.
- Physics is the default on every route. A user preference to default to Model is not offered: the physics story is the entry point by design.
- SHAP bars are signed around a centre line with the direction in text (`increases risk`), not colour alone.
- The falsifier is rendered in a bordered `notice` block, never as small print.
- Precedent feedback is labelled *"Was this case useful for this asset?"*; it writes to the retrieval index only, and the copy says so.
- If a panel's data is missing, the tab remains and the panel says what is missing and when it will exist. Hiding a tab hides the gap.

### 11.7 BlockFitRow

```tsx
export type BlockFitRowProps = {
  window: BlockWindow;
  title: string;
  assets: string[];
  clusterId?: string;
  minutes: number;
  fit: BlockFit;
  consequenceIfDeferred?: string;
  onDraft?: () => void;
};
```

Fit is computed server-side; the component renders the chip and the plain-language sentence. `fits` is teal, `extends` amber, `special` red, `none` neutral with `No published block`. The word is always present, so the chip survives greyscale and print.

### 11.8 AlertTable

```tsx
export type AlertTableProps = {
  alerts: Alert[];
  selectedIds: Set<string>;
  sort: { key: AlertSortKey; direction: "asc" | "desc" };
  onSortChange: (sort: AlertTableProps["sort"]) => void;
  onSelect: (id: string, options: { range: boolean }) => void;
  onOpen: (id: string) => void;
  isLoading: boolean;
  emptyState?: React.ReactNode;
};
```

Use TanStack Table for column model and sorting, TanStack Virtual for rows above 50. The table is a `<table>` with `role="grid"` only when cell-level navigation is implemented; otherwise a plain table with row-level interaction is more honest and more accessible. The mockups implement row-level interaction, so the build should ship a plain `<table>` and avoid the grid keyboard contract.

### 11.9 FieldConfirm

```tsx
export type FieldConfirmProps = {
  task: FieldTask;
  onQueue: (payload: FieldObservation) => Promise<{ receiptId: string }>;
  onSaveDraft: (payload: Partial<FieldObservation>) => void;
  isOffline: boolean;
  queuedCount: number;
};

export type FieldObservation = {
  clientId: string;             // uuid, idempotency key
  taskId: string;
  assetId: string;
  measurements: Record<string, { value: number; unit: string; capturedAt: string }>;
  finding: "confirmed" | "not_found" | "other";
  notes?: string;
  photoIds?: string[];
  technicianResponse: "confirmed" | "not_found" | "other";
  capturedAt: string;
  appVersion: string;
};
```

The component owns no network logic. `onQueue` is supplied by the outbox layer, so the same component works online and offline and is tested once.

### 11.10 Component quality gates

| Gate | Check |
|---|---|
| Tokens | No hex, no named colour, no raw `px` in component styles except borders and icon sizes |
| A11y | `axe` clean; keyboard test in Storybook play function |
| States | Loading, empty, stale, partial, error stories exist |
| Theming | Rendered in both control and field themes |
| Zoom | Story rendered at 320 px and 400% in visual test |
| Props | No boolean soup; variants are unions, not `isX` flags |
| Docs | One sentence of purpose, one do, one don't |

---

## 12. Data contracts: REST, streaming and offline

### 12.1 Conventions

- JSON over HTTPS; `camelCase` in transport, converted to the domain types above at the client boundary.
- All timestamps ISO 8601 UTC with `Z`; the UI renders IST and always shows the zone once per screen (`as of 14:26 IST`).
- IDs are opaque strings; asset IDs are slash-delimited and must be URL-encoded by the client.
- Every response carries `modelVersions` and `generatedAt`; the UI surfaces both, because a score without a version is not auditable.
- Errors use a single shape (RFC 9457 problem details) with a `traceId`.
- Pagination is cursor-based; the queue is stable under inserts because the cursor encodes the sort key and the snapshot time.

### 12.2 Endpoints

| Method | Path | Purpose | Cache |
|---|---|---|---|
| `GET` | `/v1/alerts` | Paged queue | `private, max-age=15`, ETag |
| `GET` | `/v1/alerts/{id}` | Single alert + explanation | `private, max-age=30`, ETag |
| `POST` | `/v1/alerts/{id}/acknowledge` | Record seen | no-store |
| `POST` | `/v1/alerts/{id}/defer` | Defer with reason | no-store |
| `POST` | `/v1/clusters/{id}/merge` | Merge alerts to cluster | no-store |
| `GET` | `/v1/assets/{assetId}` | Asset record + latest telemetry summary | `private, max-age=60` |
| `GET` | `/v1/assets/{assetId}/explanation` | Three-lens explanation | `private, max-age=30` |
| `GET` | `/v1/blocks?from=&to=` | Published Rolling Blocks | `private, max-age=300` |
| `POST` | `/v1/work-orders/draft` | Create SMMS draft (not submit) | no-store |
| `GET` | `/v1/models/health` | Model assurance snapshot | `private, max-age=300` |
| `GET` | `/v1/search?q=` | Federated search | no-store |
| `POST` | `/v1/field/observations` | Idempotent observation intake | no-store |
| `GET` | `/v1/me` | Role, scope, capabilities | `private, max-age=600` |

**No endpoint accepts an interlocking, signal, route or track-circuit command. The API surface itself enforces the advisory boundary.**

### 12.3 Alert list payload

```json
{
  "generatedAt": "2026-07-14T08:56:12Z",
  "snapshotId": "snap-2026-07-14T08:55Z",
  "nextCursor": "eyJzIjoiMjAyNi0wNy0xNFQwODo1NVoiLCJrIjoiMTIifQ",
  "items": [
    {
      "id": "alr-7f3c",
      "assetId": "ADRA/TC/12T",
      "assetName": "Adra Yard · Down Goods",
      "route": "Down Goods",
      "level": "watch",
      "risk": { "h24": 0.04, "h72": 0.11, "h7d": 0.24, "eceZone": 0.04 },
      "rul": { "p10Days": 9, "medianDays": 21, "p90Days": 38, "coverage": 0.897, "heldOutN": 3180 },
      "likelyModes": ["F1"],
      "modeSetCoverage": 0.9,
      "clusterId": "c-9917",
      "dataTrust": { "score": 0.62, "flags": ["age_vs_signature_mismatch"] },
      "block": {
        "window": { "id": "RB-28", "date": "2026-07-16", "start": "02:10", "end": "03:40", "durationMin": 90, "kind": "published" },
        "fit": "fits",
        "jobMinutes": 90
      },
      "proposedAction": { "code": "ballast_clearing", "label": "Ballast clearing + drain rodding", "minutes": 90 },
      "ageMinutes": 192,
      "modelVersions": { "twin": "0.3.1", "gnn": "0.2.0", "survival": "0.2.4", "classifier": "0.2.0" }
    }
  ]
}
```

The list omits the explanation to keep the payload small; the drawer fetches `/v1/alerts/{id}`. This is a deliberate two-request pattern: a queue of 50 rows with full SHAP payloads would be several hundred kilobytes on a 3G field connection.

### 12.4 Explanation payload

```json
{
  "alertId": "alr-7f3c",
  "physics": {
    "headline": "Effective ballast conductance +31% in 12 days; relay margin 73% of dry",
    "state": [
      { "label": "Relay current", "value": "118 mA", "baseline": "162 mA dry" },
      { "label": "Ballast conductance", "value": "1.31 × dry", "baseline": "1.00" },
      { "label": "Rain, 72 h", "value": "96 mm", "baseline": "median 22 mm" }
    ],
    "falsifier": "If insulation falls below 0.5 MΩ the ranking moves to F2 (joint), not F1."
  },
  "model": {
    "shapTop": [
      { "feature": "relay_i_slope_7d", "label": "Relay current slope, 7 d", "value": -0.41, "direction": "increases" },
      { "feature": "rain_72h", "label": "Rainfall, 72 h", "value": -0.12, "direction": "increases" }
    ],
    "calibrationNote": "Scores in this bin historically over-predict by 2 points; ECE 0.031.",
    "modeSet": ["F1", "F4"],
    "modeSetCoverage": 0.9,
    "agreement": "high"
  },
  "precedents": [
    { "smmsId": "SMMS-evt-118", "assetId": "ADRA/TC/14T", "confirmedMode": "F1", "similarity": 0.88, "daysAgo": 64, "outcome": "Drain rodded; 41 days to next alert" },
    { "smmsId": "SMMS-evt-204", "assetId": "ADRA/TC/09T", "confirmedMode": "F1", "similarity": 0.81, "daysAgo": 148, "outcome": "Ballast cleared; no recurrence in 10 months" },
    { "smmsId": "SMMS-evt-377", "assetId": "BKSC/TC/22T", "confirmedMode": "F4", "similarity": 0.72, "daysAgo": 211, "outcome": "Points bridging; joint replaced" }
  ],
  "modelVersions": { "twin": "0.3.1", "gnn": "0.2.0", "survival": "0.2.4", "classifier": "0.2.0" },
  "generatedAt": "2026-07-14T08:55:00Z"
}
```

### 12.5 Streaming

A single WebSocket per session, `/v1/stream`, carries invalidation events rather than full objects. The client patches its cache by refetching the affected key. This keeps the server simple and guarantees that what the client shows is always a server-computed object, never a client-assembled one.

```ts
export type StreamEvent =
  | { type: "alert.upserted"; alertId: string; level: AlertLevel; assetId: string; snapshotId: string }
  | { type: "alert.closed"; alertId: string; outcome: "confirmed" | "not_found" | "deferred" }
  | { type: "cluster.updated"; clusterId: string }
  | { type: "block.published"; window: BlockWindow }
  | { type: "model.promoted"; model: string; version: string }
  | { type: "heartbeat"; at: string };
```

Rules:
- The client never trusts an event payload as display data; it invalidates and refetches.
- Events are coalesced with a 250 ms trailing debounce per key, and bursts are capped at one refetch per key per second.
- On reconnect, the client refetches the visible window and shows `Live` again; it does not replay missed events.
- The socket carries no PII beyond asset IDs and alert IDs.
- If the socket fails twice, the UI degrades to 30-second polling and says so in the status bar (`Polling · 30 s`), rather than pretending to be live.

### 12.6 Offline sync protocol

The field route is a PWA with an IndexedDB outbox.

```ts
export type OutboxRecord = {
  clientId: string;          // uuid v7, idempotency key
  kind: "observation" | "acknowledge" | "draft";
  payload: unknown;
  createdAt: string;
  attempts: number;
  lastError?: string;
  status: "pending" | "syncing" | "failed" | "synced";
};
```

Protocol:
1. Write to IndexedDB and to the UI in one transaction; the UI never waits for the network.
2. On reconnect, drain in `createdAt` order, one in flight at a time.
3. Send `Idempotency-Key: {clientId}`; the server returns the original receipt on replay.
4. 4xx (except 409) marks `failed` and surfaces a field-level correction task; 5xx and network errors retry with exponential backoff (2 s, 8 s, 30 s, 2 min) and jitter, capped at 10 attempts.
5. 409 returns the server record and the local record; the UI shows a merge task with both values and never auto-resolves.
6. Synced records are kept for 7 days for audit, then purged; failed records are never purged without an explicit user action.
7. Cache is scoped per user and per device, encrypted at rest by the browser profile; a shared tablet is a supported scenario, so sign-out purges the cache.

**Storage budget:** 20 MB for task packs, 5 MB for photos, 1 MB for outbox. Photos are downscaled to 1280 px long edge and 0.7 JPEG quality before storage.

### 12.7 Errors

```json
{
  "type": "https://nidan.example/errors/stale-snapshot",
  "title": "Snapshot expired",
  "status": 409,
  "detail": "The requested snapshot is older than 15 minutes. Refetch the queue.",
  "traceId": "01J2Z9K3V8Q7R6M5N4P3",
  "retryable": true
}
```

Client mapping: `retryable` drives the retry affordance; `traceId` is shown in a copyable chip on error panels and included in support exports; `type` maps to localized copy. No server stack traces, no SQL, no internal hostnames in any payload.

### 12.8 Versioning

- URL versioning (`/v1`), additive changes only within a version.
- Clients send `X-Client-Version` and `X-Client-Build`; the server can require an upgrade for a breaking data change with a 426 and a human sentence.
- Enums are closed; an unknown `level` or `failureMode` must render as `Unknown` with the raw value, never crash the row. The UI is defensive because model output changes faster than the front-end release train.

---

## 13. State, data fetching and mutation

### 13.1 The split

| Kind of state | Where it lives | Examples |
|---|---|---|
| Server state | TanStack Query cache | Alerts, assets, blocks, model health, search |
| URL state | Router search params | Filters, sort, view tab, selected alert, scope |
| Ephemeral UI | Zustand | Drawer open, palette open, density, theme (field only) |
| Form state | React Hook Form + Zod | Field measurements, defer reason, block draft |
| Offline state | IndexedDB + Zustand mirror | Outbox, cached task packs, sync status |

Server data is never copied into Zustand. A single source prevents the "two truths" bug where a table and a KPI disagree after a mutation.

### 13.2 Query keys

```ts
export const qk = {
  me: () => ["me"] as const,
  alerts: (filters: AlertFilters) => ["alerts", "list", filters] as const,
  alert: (id: string) => ["alerts", "detail", id] as const,
  asset: (id: string) => ["assets", id] as const,
  explanation: (id: string) => ["assets", id, "explanation"] as const,
  blocks: (from: string, to: string) => ["blocks", from, to] as const,
  clusters: () => ["clusters"] as const,
  modelHealth: () => ["models", "health"] as const,
  search: (q: string) => ["search", q] as const,
  fieldTasks: () => ["field", "tasks"] as const,
  fieldTask: (id: string) => ["field", "task", id] as const,
};
```

### 13.3 Freshness policy

| Query | `staleTime` | `gcTime` | Refetch |
|---|---|---|---|
| Alert list | 15 s | 5 min | On focus, on socket event |
| Alert detail | 30 s | 10 min | On open, on socket event |
| Asset | 60 s | 30 min | On focus |
| Explanation | 30 s | 10 min | On tab first open |
| Blocks | 5 min | 60 min | On focus, on `block.published` |
| Model health | 5 min | 30 min | Manual only |
| Search | 0 | 2 min | As typed, 250 ms debounce |
| Field tasks | 0 (offline-first) | Persistent | On reconnect |

`refetchOnWindowFocus` is off for the queue while a drawer is open, because reordering the table under a user who is reading is disorienting. It refetches on drawer close.

### 13.4 Socket to cache

```ts
function useAlertStream() {
  const queryClient = useQueryClient();
  useEffect(() => {
    const socket = openStream();
    const pending = new Map<string, number>();

    socket.on("event", (event: StreamEvent) => {
      if (event.type === "heartbeat") return;
      const key = event.type === "alert.upserted" ? `alert:${event.alertId}` : event.type;
      if (pending.has(key)) return;                    // coalesce
      pending.set(key, window.setTimeout(() => {
        pending.delete(key);
        if (event.type === "alert.upserted") {
          queryClient.invalidateQueries({ queryKey: qk.alert(event.alertId) });
        }
        queryClient.invalidateQueries({ queryKey: ["alerts", "list"] });
      }, 250));
    });

    return () => {
      pending.forEach((t) => clearTimeout(t));
      socket.close();
    };
  }, [queryClient]);
}
```

The visible rows are patched via `setQueryData` only for the level and the risk numbers, and only when the snapshot is newer than the cached one. Everything else waits for the refetch. This keeps the queue feeling live without letting the client synthesise an alert.

### 13.5 Mutations

```ts
export function useAcknowledgeAlert() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.post(`/v1/alerts/${id}/acknowledge`),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ["alerts", "list"] });
      const previous = queryClient.getQueriesData({ queryKey: ["alerts", "list"] });
      queryClient.setQueriesData<AlertPage>({ queryKey: ["alerts", "list"] }, (page) =>
        page && { ...page, items: page.items.map((a) => (a.id === id ? { ...a, ack: true } : a)) },
      );
      return { previous };
    },
    onError: (_error, _id, context) => {
      context?.previous.forEach(([key, data]) => queryClient.setQueryData(key, data));
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts", "list"] });
      queryClient.invalidateQueries({ queryKey: qk.me() });
    },
  });
}
```

Rules:
- Optimistic updates only where the server outcome is deterministic and reversible (acknowledge, defer, select). Never for risk, RUL, level or cluster membership.
- Every mutation has a rollback path and an error message that names what did not happen.
- Acknowledge is not "resolve": the copy and the API distinguish seeing from closing.
- Bulk actions send one request per item with a shared `batchId`, so partial failure is visible per row rather than all-or-nothing.

### 13.6 URL as state

The queue's filters, sort and view tab live in the URL:

```
/alerts?level=critical,watch&mode=F1&fit=fits&view=triage&sort=priority:desc&alert=alr-7f3c
```

This makes a shift handover a link, restores state on refresh, and lets the server render the same view for an export. The drawer is a URL, not a boolean, so `Back` closes it.

### 13.7 Zustand stores

```ts
type UiStore = {
  paletteOpen: boolean;
  density: "comfortable" | "compact";
  setPaletteOpen: (open: boolean) => void;
  toggleDensity: () => void;
};

type SyncStore = {
  online: boolean;
  lastSyncAt: string | null;
  queued: number;
  failed: number;
  setOnline: (online: boolean) => void;
  setQueued: (n: number) => void;
};
```

Two small stores, both persisted where appropriate (`density`), neither holding server objects. The outbox store is a mirror of IndexedDB, written by the sync worker, never the other way round.

### 13.8 Field outbox

```ts
export async function queueObservation(payload: FieldObservation) {
  await db.outbox.add({
    clientId: payload.clientId,
    kind: "observation",
    payload,
    createdAt: new Date().toISOString(),
    attempts: 0,
    status: "pending",
  });
  syncStore.getState().setQueued(await db.outbox.where("status").anyOf("pending", "failed").count());
  void flushOutbox();          // fire and forget; the UI has already updated
}
```

The confirm button calls `queueObservation` and then shows the receipt state. It never awaits the network. `flushOutbox` runs on `online`, on app focus, and on a 60-second timer while the page is visible.

### 13.9 Loading and error discipline

- Skeletons match the final layout to prevent shift; no spinner on a page that has a skeleton.
- A failed panel does not blank the page: error boundaries are per panel, with a retry that preserves context.
- Toasts are for confirmation of a user action, never for a new alert. A Critical alert never arrives as a toast; it arrives in the queue and in the count.
- The retry button is the same size and position in every error panel, so muscle memory works under stress.

---

## 14. Technology stack decision record

### 14.1 Decisions at a glance

| Layer | Choice | Why | Rejected |
|---|---|---|---|
| UI runtime | React 19 + TypeScript 5.7 (strict) | Concurrent rendering for a live queue; `useOptimistic` for field and triage; the largest hiring pool for CRIS/OEM teams; React 19's ref-as-prop and Actions simplify the outbox | Vue (smaller ecosystem for Radix-style primitives), Svelte (fewer accessible primitives, harder OEM hand-off), Angular (heavier ceremony for a 7-route product) |
| Build | Vite 6 | Sub-second HMR, static output that can sit behind a railway auth proxy, no server runtime to certify | Next.js (SSR/SEO not needed; adds a Node server to an air-gapped deployment), CRA (unmaintained) |
| Styling | Tailwind CSS v4 + CSS custom properties | Tokens stay in CSS, utilities stay close to markup, v4's `@theme` reads the same variables, zero runtime | CSS-in-JS (runtime cost, theming friction), Sass modules (two token systems) |
| Primitives | Radix UI via shadcn/ui, vendored | WAI-ARIA behaviour, focus management, keyboard support; code lives in the repo so it can be audited | Headless UI (smaller set), MUI (opinionated visuals fight the design language) |
| Server state | TanStack Query v5 | Cache, retries, invalidation, optimistic updates, devtools; the queue is a cache problem, not a global-store problem | Redux Toolkit Query (more boilerplate), SWR (weaker mutation model) |
| Tables | TanStack Table v8 + Virtual v3 | Headless column model, sorting, virtualization at 500+ rows | AG Grid (licence, bundle, visual weight), hand-rolled (re-implements sorting and a11y) |
| UI state | Zustand | Two small stores, no provider, easy to read in a debugger | Context-only (re-render storms), Redux (overkill) |
| Forms | React Hook Form + Zod | Uncontrolled inputs for field performance; one schema shared with the API contract | Formik (slower, maintenance), hand-rolled validation |
| i18n | i18next + react-i18next | Namespaced bundles, `lang` handling, plural rules; Hindi is a first-class locale | Hand-rolled dictionary (no plural/fallback logic) |
| Charts | Hand-authored SVG + d3-scale (math only) | The RUL band, spine, SHAP bars and sparklines are bespoke; a chart library would fight the design and add 80–200 KB | Recharts, Chart.js, ECharts, Highcharts |
| Map | MapLibre GL JS + deck.gl, only if the geographic view ships | Open, offline-capable vector tiles, no licence fee | Google Maps (cost, offline), Leaflet (weaker large-data layers) |
| Offline | Workbox 7 + `idb` | Precached shell, runtime caching, typed IndexedDB wrapper; predictable update flow | Custom service worker (subtle cache bugs), PouchDB (heavier than needed) |
| Tests | Vitest, Testing Library, Playwright, axe-core, MSW | Unit, component, end-to-end, accessibility, network mocking in one toolchain | Jest (slower ESM story), Cypress (parallelism cost) |
| Docs | Storybook 9 | Component states and themes in one place; visual review | Ladle (smaller ecosystem) |
| Package manager | pnpm | Fast, strict, disk-efficient in CI | npm (slower, looser), Yarn Berry (PnP friction with some tooling) |
| Lint/format | ESLint 9 flat config + Prettier | Type-aware rules, import boundaries, no-hex rule | TSLint (dead) |
| Observability | OpenTelemetry web + Sentry | Trace IDs match the API problem details; no PII | GA4 (not appropriate for railway operations data) |

### 14.2 Why React 19 specifically

- **`useOptimistic`** fits acknowledgement and field queueing: the user sees the state change immediately, and the rollback is declarative rather than a manual snapshot.
- **Actions and `useActionState`** give the field form a single pending/error path that works with or without JavaScript-enhanced submission later.
- **Ref as a prop** removes `forwardRef` noise from 30+ primitives and makes the vendored shadcn components easier to audit.
- **Document metadata and stylesheet hoisting** are irrelevant here (no SSR), but the compiler-friendly patterns reduce re-renders in the queue without hand-written memoisation everywhere.
- **Suspense boundaries** per panel let the detail page stream its explanation without blanking the RUL band.

React 19 is used as a client-rendered SPA. Server Components are explicitly not adopted: the deployment is a static bundle behind an existing reverse proxy, and the data is authenticated per user with no SEO surface.

### 14.3 Why not Next.js

1. The product sits behind railway SSO in a controlled network; there is no public crawl surface.
2. The field route must work offline from a cached shell; a server-rendered page adds a failure mode the service worker cannot fix.
3. Certification and deployment are simpler with static artefacts: one bundle, one hash, one rollback.
4. The API is owned by the platform team; a BFF would duplicate it.
5. Route-level code splitting in Vite is sufficient for seven routes.

### 14.4 Tailwind v4 and the token contract

Tailwind v4 is configured to read the CSS variables rather than define a second palette:

```css
@import "tailwindcss";
@import "./tokens.css";

@theme inline {
  --color-app: var(--bg-app);
  --color-panel: var(--bg-panel);
  --color-raised: var(--bg-raised);
  --color-line: var(--border);
  --color-line-strong: var(--border-strong);
  --color-hi: var(--text-hi);
  --color-mid: var(--text-mid);
  --color-lo: var(--text-lo);
  --color-teal: var(--teal-400);
  --color-amber: var(--amber-400);
  --color-red: var(--red-400);
  --color-ok: var(--ok-500);
  --font-sans: var(--font-latin);
  --font-deva: var(--font-deva);
  --font-mono: var(--font-mono);
  --spacing: 4px;              /* 8-point rhythm via multiples */
  --radius-md: var(--r-md);
}
```

Because the utilities resolve to the same variables, switching `data-theme="field"` re-themes every Tailwind class without a rebuild. The alternative — Tailwind's default palette plus `dark:` variants — would create two sources of truth and a field theme that drifts.

**Boundary rule:** utilities are allowed for layout and spacing; component classes are used for anything with three or more properties or a state contract (`.panel`, `.spine`, `.rul`). A 200-character `className` is a component waiting to be extracted.

### 14.5 Charting decision

The four visualisations that carry the product are not generic charts:

| Visual | Why bespoke | Estimated cost |
|---|---|---|
| RUL band | Needs a block marker, threshold line, direct labels and a table equivalent | 180 lines |
| Signal Spine | A list with a hairline and state shapes; no chart library models it | 90 lines |
| SHAP bars | Signed, centred, labelled; the semantics matter more than the axes | 70 lines |
| Sparklines | 54 px, no axes, baseline band, one value | 40 lines + d3-scale |
| Propagation map | A graph with cluster hulls and cascade arrows | 220 lines, or deck.gl if geographic |

Using a chart library for these would add a dependency, a visual language that does not match, and an accessibility layer that still needs replacement. `d3-scale` and `d3-shape` are imported as pure math (about 8 KB) rather than the full `d3` bundle.

### 14.6 Browser and device support

| Target | Support |
|---|---|
| Chrome / Edge 111+ | Full |
| Firefox 121+ | Full |
| Safari 17+ (iPad) | Full, including field PWA |
| Android Chrome 111+, 3 GB RAM | Full; field route tuned for 2 GB |
| IE / legacy Edge | Not supported; upgrade notice |
| 1024 × 768 control desk | Supported with collapsed rail |
| 1280 × 720 wall display | Supported; the queue is the default view |

Support is defined by capability, not user-agent sniffing: `CSS.supports`, `ResizeObserver`, `IndexedDB`, service worker. A device without service worker gets an online-only field route with a clear warning, not a broken one.

---

## 15. Repository structure and engineering conventions

### 15.1 Structure

```
nidan-web/
├─ public/
│  ├─ fonts/                     # subset woff2, self-hosted
│  └─ icons/
├─ src/
│  ├─ app/
│  │  ├─ App.tsx
│  │  ├─ router.tsx              # createBrowserRouter, lazy routes
│  │  ├─ providers.tsx           # QueryClient, theme, i18n, error boundary
│  │  └─ boundaries/             # route + panel error boundaries
│  ├─ components/
│  │  ├─ ui/                     # vendored Radix/shadcn primitives
│  │  ├─ primitives/             # Panel, KpiTile, LevelBadge, RiskCell, Chip
│  │  ├─ data/                   # SignalSpine, RulBand, ShapBars, Sparkline, Graph
│  │  ├─ domain/                 # ExplanationCard, BlockFitRow, StageRail, AssetRecord
│  │  └─ field/                  # FieldConfirm, MeasurementField, OfflineBadge
│  ├─ features/
│  │  ├─ command-centre/
│  │  ├─ alerts/
│  │  ├─ asset-detail/
│  │  ├─ clusters/
│  │  ├─ blocks/
│  │  ├─ models/
│  │  ├─ field/
│  │  └─ search/
│  ├─ lib/
│  │  ├─ api/                    # client, endpoints, problem-details mapping
│  │  ├─ query/                  # qk, hooks, socket bridge
│  │  ├─ offline/                # db, outbox, sync worker
│  │  ├─ format/                 # IST time, risk, RUL, numbers
│  │  ├─ a11y/                   # chart summaries, focus helpers
│  │  └─ analytics/              # typed event names, no PII
│  ├─ stores/                    # ui.ts, sync.ts
│  ├─ i18n/                      # en/, hi/, config.ts
│  ├─ styles/                    # tokens.css, app.css, tailwind entry
│  ├─ types/                     # domain.ts, api.ts, stream.ts
│  └─ test/                      # setup, fixtures, MSW handlers
├─ e2e/                          # Playwright specs + axe scans
├─ .storybook/
├─ eslint.config.js
├─ tailwind.config.ts            # only for content globs; theme lives in CSS
├─ tsconfig.json                 # strict, noUncheckedIndexedAccess
├─ vite.config.ts
└─ package.json
```

Each feature folder:

```
features/alerts/
├─ routes/
│  ├─ AlertQueueRoute.tsx
│  └─ AlertDrawerRoute.tsx
├─ components/                   # feature-only components
├─ hooks/                        # useAlertFilters, useAlertSelection
├─ api.ts                        # query + mutation hooks for this feature
├─ schema.ts                     # Zod schemas shared with forms
├─ filters.ts                    # URL <-> filter object, pure
└─ __tests__/
```

### 15.2 Conventions

| Area | Convention |
|---|---|
| Files | `PascalCase.tsx` for components, `camelCase.ts` for modules, `*.test.ts(x)` colocated |
| Exports | Named exports; default export only for lazy route modules |
| Imports | Absolute from `@/`; no cross-feature imports except through `@/components` or `@/lib` |
| Types | `type` for unions and props, `interface` for extendable objects; no `any`, no non-null assertion without a comment |
| CSS | BEM-ish component classes (`.panel__head`), no nesting deeper than two, no `!important` outside print |
| State | Server data in Query, URL state in router, ephemeral in Zustand, form in RHF |
| Dates | Store UTC, render IST via one formatter; never `toLocaleString()` inline |
| Numbers | One `formatRisk`, `formatRul`, `formatCount` module; no ad-hoc `toFixed` |
| Errors | Throw typed `ApiError`; map problem details to copy in one place |
| Copy | No hard-coded strings in components; `t('alerts.empty.title')` |
| Icons | 20 px grid, 1.5 stroke, currentColor; no filled decorative icons |
| Tests | Behaviour over implementation; query by role and name |

### 15.3 Route table to files

| URL | Route module | Shell |
|---|---|---|
| `/` | `features/command-centre/routes/CommandCentreRoute.tsx` | Control |
| `/alerts` | `features/alerts/routes/AlertQueueRoute.tsx` | Control |
| `/alerts/:alertId` | `features/alerts/routes/AlertDrawerRoute.tsx` (parallel outlet) | Control |
| `/assets/:assetId` | `features/asset-detail/routes/AssetDetailRoute.tsx` | Control |
| `/clusters` | `features/clusters/routes/ClustersRoute.tsx` | Control |
| `/blocks` | `features/blocks/routes/BlocksRoute.tsx` | Control |
| `/models` | `features/models/routes/ModelHealthRoute.tsx` | Control |
| `/field` | `features/field/routes/FieldTasksRoute.tsx` | Field |
| `/field/tasks/:taskId` | `features/field/routes/FieldTaskRoute.tsx` | Field |
| `/design` | `features/design/routes/DesignSystemRoute.tsx` | Control |
| `/search` | palette overlay, no standalone route | — |

Route modules are lazy-loaded. The control shell, tokens and the four primitives are in the initial bundle; the RUL band and the propagation graph are loaded with the detail route.

### 15.4 Testing strategy

| Level | Tool | What it must cover |
|---|---|---|
| Unit | Vitest | Priority sort, block-fit formatting, RUL geometry, URL filter round-trip, outbox retry/backoff |
| Component | Testing Library + Storybook play | Tabs keyboard, row open, bulk select, LevelBadge name, RulBand table equivalent |
| Contract | MSW + schema tests | Every payload parses; unknown enum values degrade |
| E2E | Playwright | Triage a Critical, open a detail, draft SMMS, queue a field observation offline, reconnect and sync |
| A11y | axe in Playwright | All routes, both themes, zero serious |
| Visual | Playwright screenshots | Seven reference screens at 1600 and 1024, diff threshold 0.1% |
| Performance | Lighthouse CI + custom marks | Budgets in §16.1 |

The offline E2E test is the most important: it runs with the browser context offline, queues an observation, reloads, goes online, and asserts the sync receipt and the SMMS draft ID.

### 15.5 CI gates

1. Typecheck (`tsc --noEmit`) and lint (zero warnings).
2. Unit and component tests with coverage floors: 85% lines on `lib/` and `features/*/filters.ts`, 70% overall.
3. Playwright E2E on Chromium; a nightly run on WebKit for the iPad field route.
4. axe scan on seven routes × two themes.
5. Bundle budget: initial JS ≤ 220 KB gzip, route chunks ≤ 90 KB, total CSS ≤ 45 KB.
6. Token lint: no hex outside `styles/tokens.css`.
7. Storybook build and visual diff.
8. Licence check: no GPL, no unlicensed fonts.

### 15.6 Environments and configuration

- `VITE_API_BASE`, `VITE_WS_BASE`, `VITE_MAPS_STYLE_URL`, `VITE_SENTRY_DSN`, `VITE_BUILD_SHA`, `VITE_FEATURE_FLAGS`.
- No secrets in the bundle; auth is a same-site cookie issued by the gateway, with CSRF double-submit on mutations.
- Feature flags are read once at boot and exposed through a typed `flags` object; a flag never changes layout mid-session.
- Three environments: `dev` (MSW by default), `staging` (synthetic division), `prod`.
- Builds are reproducible: pinned pnpm lockfile, `SOURCE_DATE_EPOCH`, build SHA shown in the status bar tooltip.

### 15.7 Definition of done for a screen

- Five states implemented (loading, empty, stale, partial, error) and in Storybook.
- Keyboard path documented and tested; axe clean.
- Works at 320 px and 400% zoom; both themes if the route is reachable in field mode.
- Copy reviewed for vocabulary and for the advisory limit.
- No colour literals; tokens only.
- Analytics events fire once per intent, with no PII.
- Screenshot added to the visual suite.
- A section engineer can complete the screen's primary job without a tooltip.

---

## 16. Performance, resilience and field constraints

### 16.1 Budgets

| Metric | Control desktop | Field tablet |
|---|---|---|
| LCP | ≤ 2.0 s on 4G, cold cache | ≤ 3.0 s on 3G, warm cache |
| INP | ≤ 200 ms | ≤ 300 ms |
| CLS | ≤ 0.05 | ≤ 0.05 |
| Initial JS | ≤ 220 KB gzip | ≤ 220 KB gzip |
| Route chunk | ≤ 90 KB gzip | ≤ 90 KB gzip |
| CSS | ≤ 45 KB gzip | ≤ 45 KB gzip |
| Fonts | ≤ 120 KB, 2 preloaded faces | ≤ 120 KB |
| Queue render | 500 rows virtualized, ≤ 16 ms per scroll frame | 100 rows, ≤ 16 ms |
| Socket update | ≤ 4 DOM updates/s under burst | Same |

### 16.2 How the budget is met

- **Route splitting** at the router; the detail route's chart code is a separate chunk.
- **No chart library**; `d3-scale` only.
- **Font subsetting** to Latin + Devanagari, with `unicode-range` so a Hindi label fetches the Devanagari face only when present.
- **Virtualization** above 50 rows; the queue keeps a fixed row height so the scrollbar does not jump.
- **Memoised selectors** for derived rows; the priority sort is computed server-side and only re-sorted client-side for column sorts.
- **Streaming coalescing** at 250 ms; a burst of 40 events causes at most two refetches.
- **Deferred panels** on the detail page: signals and precedents load after the RUL band and explanation.
- **Image discipline**: no raster imagery in the UI; the propagation map is SVG; the field camera uses downscaled thumbnails.

### 16.3 Rendering the propagation graph

The graph has 1,284 nodes at division scale and 40–60 visible after filtering. Two modes:

- **Schematic (default):** hand-laid SVG with fixed positions from the track layout, no physics simulation at runtime. Deterministic, printable, and readable at a glance. The mockup uses this mode.
- **Geographic (optional):** MapLibre with deck.gl ScatterplotLayer and ArcLayer, only when a division asks for it. Tiles are self-hosted for offline.

A force simulation is explicitly rejected: the layout would change between sessions, which destroys the operator's spatial memory of where 12T sits relative to the yard.

### 16.4 Low-end Android field devices

| Constraint | Measure |
|---|---|
| 2 GB RAM, 4-core A53 | Budget test on a throttled profile; no chart code on the field route |
| 3G / intermittent | Offline-first; task packs prefetched at shift start |
| Sunlight | Light theme, 7:1 body contrast, 2 px borders, no thin hairlines for state |
| Gloves | 56 px targets, no swipe-only, no long-press, no hover-only |
| Battery | No animation loops, no polling while backgrounded, sync on wake |
| Storage | 20 MB cache cap with LRU eviction; photos capped at 5 MB total |
| Shared device | Sign-out purges cache and outbox is per-user |

### 16.5 Resilience matrix

| Failure | Detection | UI behaviour | Recovery |
|---|---|---|---|
| WebSocket down | `onclose`, two failed retries | Status bar `Polling · 30 s`; values unchanged | Auto-reconnect with jitter; full refetch on success |
| API 5xx | Problem details | Panel error with trace ID; other panels keep working | Retry button; exponential backoff on queries |
| Snapshot stale > 15 min | `snapshotId` age | Amber `as of` chip; destructive actions disabled | Refetch on focus |
| SMMS unavailable | Health endpoint | Draft button becomes `SMMS unavailable · retry`; draft can be exported as PDF | Queue draft locally, submit later |
| Clock skew | Server `Date` vs local | Always render server time; label IST | Ignore local clock for data age |
| Model version changed mid-session | `modelVersions` mismatch | Inline notice on explanation: `Scores updated at 14:26 · twin 0.3.2` | Refetch alert |
| Offline during field confirm | `navigator.onLine`, sync failure | Outbox badge, queued state, no error dialog | Background drain on reconnect |
| IndexedDB full | `QuotaExceededError` | Prompt to sync or discard cached photos; never silently drop observations | Explicit user choice |
| Auth expiry | 401 | Modal re-auth, form state preserved | Resume the same route |
| Corrupt cache | Schema version mismatch | Clear cache, keep outbox | Reload |

### 16.6 Security and data handling

- No PII in analytics. Events carry asset ID, alert level, route and timing; never names, phone numbers or free text.
- Free-text technician notes stay in the API and SMMS sync; they are not sent to Sentry or the analytics sink.
- CSP: `default-src 'self'`; no third-party scripts; `connect-src` limited to the API, WebSocket and Sentry ingest.
- The UI never caches a response with `Cache-Control: no-store`; the service worker excludes auth and problem-detail responses.
- Session logout clears Query cache, IndexedDB caches and the outbox only after an explicit warning if items are pending.
- Exports are watermarked with user, role, scope and timestamp; the advisory statement is on every page of the PDF.

### 16.7 Observability

| Signal | Instrumentation | Use |
|---|---|---|
| Web vitals | `web-vitals` → OTel | Budget regression by route and device class |
| API latency | Fetch instrumentation with route tag | Separate p95 for queue vs detail |
| Socket health | Connect/disconnect/retry counts | Detect a flapping gateway |
| Offline sync | Queued, synced, failed, conflict counts | Field reliability |
| Interaction events | `triage.open`, `explanation.tab`, `smms.draft`, `field.queue` | Adoption and friction, no PII |
| Errors | Sentry with `traceId` | Correlate with API logs |

A dashboard of these metrics is itself reviewed monthly alongside model health, because a front end that is slow at 02:40 is a model that does not get used.

---

## 17. Benchmark: what to borrow and what to avoid

Sixteen references across railway products, industrial data platforms, monitoring tools and public design systems. The point is not admiration; each entry yields a specific borrow and a specific avoid.

### 17.1 Railway and industrial products

| Product | What it does | Borrow | Avoid |
|---|---|---|---|
| **Siemens Railigent X** | Integrates train and signalling data with RUL and fleet applications, with a developer portal for the ecosystem | Asset-centric application framing; versioned model/application separation; a clear split between data ingestion and decision apps | A catalogue of dozens of apps as the home screen; our operator needs one ranked queue, not a marketplace |
| **Alstom HealthHub** | Monitors rolling stock, track, catenary and signalling, and converts alerts into maintenance work | The alert→work-order bridge as the product's end, not an afterthought; condition coverage across asset classes | Generic "health score" as the primary object; it hides the failure mode and cannot be falsified |
| **Thales TIRIS Points Predict** | Anomaly detection, fault classification and remaining asset life for points, deployed on Network Rail Anglia | Naming the physical asset class in the product, not just "asset"; showing remaining life as the decision variable | Treating anomaly detection as diagnosis; a score without a mode is not actionable |
| **Network Rail — AI and remote condition monitoring** | Predicts failures up to a year ahead and monitors remote assets to target maintenance | Long-horizon prediction paired with a short-horizon action; the honesty that a prediction is a planning input | A research-dashboard aesthetic; operators need a work list, not a demonstration of the model |
| **Hitachi Rail HMAX** | Remote monitoring at scale (2,000+ trains, 200,000 systems), automatic work-order generation, 200+ monitoring sites | Operational scale as a design constraint from day one; automatic drafting with a human gate | A wall of fleet dashboards; scale should make the queue sharper, not the interface busier |
| **Palantir Foundry Ontology** | Objects, links and actions as a shared semantic layer over data | The object/link/action model as the backbone of the UI: asset, alert, cluster, block, action. It maps directly to our types | Exposing the ontology as an exploration tool to operators; the semantic layer is infrastructure, not an interface |

**Synthesis for NIDAN.** The railway products agree on three things: condition data is only useful when it ends in work, remaining life is the number operators act on, and remote monitoring only pays off if the queue is trustworthy. They diverge on the primary object — app catalogue, health score, or work order. NIDAN takes the work order as the end and the failure mode as the primary object, with the model health page as the trust layer that the others mostly keep internal.

### 17.2 Monitoring and data products

| Product | What it does | Borrow | Avoid |
|---|---|---|---|
| **Datadog monitors** | Configurable alert conditions with thresholds, evaluation windows and multi-alert grouping | Explicit evaluation windows and persistence ("3 evaluations") stated in the UI; grouping by a shared dimension (our cluster) | Alert fatigue as a normal condition; a monitor list longer than a shift can absorb |
| **Grafana dashboards** | Composable panels over time-series data | Direct labelling, consistent axis treatment, the panel as a reusable unit | Dashboard-first information architecture; a wall of panels with no ranked action |
| **Grafana panel visualisations** | A mature catalogue of visual options | Choosing the visual by the question; a table view for exact values | Gauges, donuts and 3D effects for operational risk; they imply limits and controls that do not exist |

### 17.3 Design systems

| System | What it contributes | Borrow | Avoid |
|---|---|---|---|
| **IBM Carbon 2x Grid** | A disciplined 2 px/8 px grid with responsive column rules | The grid as a layout contract, not a suggestion; consistent gutters across breakpoints | Carbon's full component aesthetic; it is an enterprise language, not a control-room one |
| **Material 3 typography** | A role-based type scale (display, headline, body, label) | Naming type by role, not by size; a small number of roles used consistently | Expressive type and large radii; wrong for dense operational data |
| **Atlassian spacing** | A space scale with documented application rules | Spacing tokens with stated jobs ("inside a control", "between sections") | Generous consumer spacing at the cost of scan density |
| **Shopify Polaris layout** | Clear page/container/card composition rules | The page header → primary action → content hierarchy; one primary action per page | Card-everything; operational data needs tables and a spine, not a feed of cards |
| **GitHub Primer foundations** | Practical, dense, accessible product patterns | Dense tables, subdued chrome, colour used semantically and sparingly | GitHub's information density without its navigation model; density needs a spine to be scannable |
| **GOV.UK error summary** | A single, linked error summary above the form | Error summary that links to fields, plain language, no blame | The full GOV.UK visual language; it is optimised for public services, not 24×7 operations |
| **USWDS spacing units** | A spacing token system with a clear naming and conversion story | Token names that encode the value, so a reviewer can reason about rhythm | Multiple concurrent spacing systems in one product |
| **Vercel Geist** | A tight, modern type and colour system for technical products | Restrained neutral palette, excellent mono pairing, confidence in small type | The monochrome minimalism as a whole; railway state needs a strong semantic colour layer |
| **Radix accessibility primitives** | WAI-ARIA behaviour underneath custom visuals | Using behaviour libraries and owning the visuals; keyboard and focus correctness by default | Assuming the primitive makes the whole page accessible; labels, order and announcements are still ours |
| **WCAG 2.2** | The conformance baseline | Target size, focus not obscured, redundant entry, accessible authentication | Treating AA as the ceiling; field use demands more |

### 17.4 What the benchmark changes in this design

1. **The work order is the destination.** Alstom and Hitachi both end in maintenance execution; NIDAN puts the Rolling Block fit on the same row as the risk, not in a separate planning module.
2. **The failure mode is the primary object.** Thales shows remaining life; NIDAN shows remaining life *and* the mode, because the mode determines the crew and the material.
3. **Persistence is visible.** Datadog's evaluation windows become explicit copy ("Watch requires three evaluations"), which prevents the "why did this alert disappear?" conversation.
4. **The model health page is user-facing.** None of the railway products put calibration and coverage in front of the supervisor; for an advisory system asking for trust, that is the missing layer.
5. **Density needs a spine.** Primer and Carbon prove dense tables can be readable; the Signal Spine is what makes density scannable in a control room.
6. **Error handling is a design pattern.** GOV.UK's summary shapes the field form and every failed panel.
7. **Behaviour is not visual.** Radix, Carbon and GOV.UK all separate the two; this build owns visuals and borrows behaviour.
8. **No dashboard home.** Grafana and Datadog are excellent at exploration; NIDAN's home is a decision, so the queue and spine lead and the charts are subordinate.

---

## 18. Delivery roadmap, instrumentation and risks

### 18.1 Shape of the delivery

Twenty-four weeks to a supervised pilot in one division, with a usable queue by week six. The sequence is chosen so that the product can be shown to a section engineer early and so that the riskiest integration — SMMS drafting and offline field capture — is not left to the end.

| Phase | Weeks | Scope | Exit criteria |
|---|---|---|---|
| 0. Foundation | 0–2 | Tokens, both themes, shell, router, API client, MSW fixtures, seven static screens ported to React shell | Token lint and axe pass on an empty shell; visual parity with the mockups for chrome and one panel |
| 1. Triage | 3–6 | Command centre, alert queue, filters, saved views, bulk acknowledge/defer, drawer | A section engineer triages a 50-row queue with the keyboard; INP ≤ 200 ms; five states per screen |
| 2. Explanation | 7–10 | Circuit detail, RUL band, three-lens explanation, signals, failure modes, cluster, recommended action | Every alert opens to a falsifier in one click; RUL table equivalent and screen-reader summary verified |
| 3. Field | 11–14 | Field PWA, task packs, outbox, 56 px targets, bilingual copy, SMMS draft, offline E2E | Offline queue → reload → reconnect → receipt, on a 3G throttled profile and a real low-end tablet |
| 4. Assurance | 15–18 | Model health, clusters route, Rolling Block planner, search palette | CRIS/RDSO reviewer can trace a score to version, calibration and coverage without asking for help |
| 5. Hardening | 19–22 | Performance, accessibility audit, pen-test fixes, print/export, error states, load test | Budgets met; zero serious axe issues; a11y sign-off; pilot runbook |
| 6. Pilot | 23–24 | Adra division, 20 users, shadow mode, weekly review | Three weeks of use with no safety incident; false-positive rate measured and accepted |

### 18.2 The cut line

If the programme is compressed to twelve weeks, ship phases 0–3 and defer clusters, blocks planner and model health to a second release. Do **not** cut: the falsifier, the RUL interval, the field offline path, the advisory statement, or the five states. Those are the product's credibility, not its polish.

### 18.3 Instrumentation

Events are typed, reviewed like API changes, and carry no personal data.

| Event | Fired when | Properties |
|---|---|---|
| `queue.view` | Queue mounted or filter changed | `level[]`, `mode[]`, `fit`, `cluster`, `savedView`, `resultCount` |
| `triage.open` | Drawer opened | `alertId`, `assetId`, `level`, `rank`, `source` (`spine`/`table`/`palette`) |
| `explanation.tab` | Lens changed | `alertId`, `tab`, `dwellMs` |
| `explanation.falsifier_copy` | Falsifier copied | `alertId`, `mode` |
| `rul.table_open` | Table equivalent opened | `alertId` |
| `block.fit_view` | Block row expanded | `windowId`, `fit`, `minutes` |
| `smms.draft_created` | Draft created | `alertId`, `mode`, `minutes`, `windowId`, `result` |
| `defer.submitted` | Deferral confirmed | `alertId`, `level`, `reasonCode`, `reviewDays` |
| `field.task_open` | Field task opened | `taskId`, `assetId`, `online` |
| `field.measurement_entered` | Measurement blurred and valid | `taskId`, `field`, `hasUnit` (no value) |
| `field.observation_queued` | Confirm pressed | `taskId`, `finding`, `queuedCount`, `online` |
| `field.sync` | Outbox drained | `queued`, `synced`, `failed`, `conflicts`, `durationMs` |
| `offline.entered` / `offline.exited` | Connectivity change | `route` |
| `model.health_view` | Model health opened | `role`, `tab` |
| `search.performed` | Palette query settled | `queryLength`, `resultTypes`, `selected` |

Forbidden in telemetry: technician name, free-text notes, phone number, GPS coordinates, photo content, SMMS free text.

### 18.4 Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| False positives erode trust in the first month | High | High | Ship with calibration and data trust visible; start in shadow mode; review every Critical with the SSE; publish the false-positive rate monthly |
| Low data trust makes scores unusable in some sections | Medium | High | Data-trust score on every alert; a reconcile task generated when trust < 0.6; no suppression, so the gap is visible |
| Field adoption fails because the app is slow or fiddly | Medium | High | 56 px targets, offline-first, three steps, pilot on the actual tablet model before build freeze |
| SMMS integration slips | Medium | Medium | Draft export as PDF/CSV fallback; the UI never blocks on SMMS; integration status is visible |
| Alert volume exceeds shift capacity | Medium | High | Cluster merging, saved views, bulk defer, and a queue-capacity indicator; threshold tuning is a governed action |
| Scope creeps toward control | Low | Critical | The advisory boundary is in the design system, the API and the review checklist; any control affordance is a release blocker |
| Hindi copy is machine-translated | Medium | Medium | Native reviewer for field copy; glossary locked; bilingual review is a gate |
| Dense tables fail at 200% zoom | Medium | Medium | Card collapse under 720 px; tested in CI; column priority defined |
| Low-end tablets cannot run the field route | Medium | High | Field route excludes chart code; budget test on a 2 GB device; native wrapper as fallback if the PWA fails |
| Model version changes mid-shift confuse users | Low | Medium | Version chip on explanation; update notice; no silent swap of the score under an open drawer |
| Auth/session expiry loses field work | Medium | Medium | Outbox survives session expiry; re-auth modal preserves state; sign-out warns on pending items |
| Accessibility audit finds systemic issues late | Low | Medium | axe in CI from week 1; manual screen-reader test each phase; a11y is a phase gate |
| Export pack leaks more than intended | Low | High | Watermark, role-scoped fields, advisory statement on every page, no PII unless required |

### 18.5 Open decisions

These need a named owner before phase 1 ends. They are product and governance decisions, not design preferences.

1. **Authentication and hosting.** Railway SSO through an existing gateway, or a NIDAN-issued account? This determines session handling, cache-clearing and the re-auth modal. Owner: platform/CRIS.
2. **SMMS integration mode.** Direct API, file exchange, or draft-only export for the pilot. The UI is designed for draft-only, but the field copy and the sync error paths change. Owner: SMMS integration lead.
3. **Threshold governance.** Who signs a change to the Watch/Warning/Critical policy, and how is the change announced in the UI? The design assumes a versioned policy object with an effective date. Owner: RDSO/operations.
4. **Hindi scope for release 1.** Field-only bilingual, or all navigation too? The mockups assume field-first. Owner: operations/training.
5. **Geographic view.** Ship the schematic propagation graph only, or add MapLibre for divisions that ask? Adding it costs a tile pipeline and offline storage. Owner: product.
6. **Tablet procurement.** Which device and Android version are the field baseline? The 56 px and 3G budgets assume a 10-inch, 2 GB device. Owner: division/IT.
7. **Photo policy.** Are ballast photos stored in SMMS, NIDAN, or both? Retention and access rules follow. Owner: operations/legal.
8. **Critical alert after hours.** Does a Critical page anyone, or does it wait for the shift? The UI currently assumes no paging; that is a process decision with union and safety implications. Owner: divisional control.
9. **Role mapping.** Which railway designation maps to `section engineer` and who can defer a Critical? Owner: HR/operations.
10. **Model version visibility.** Show all four model versions to every role, or only to CRIS/RDSO? The mockups show them in the footer for all. Owner: model governance.
11. **Data retention in the browser.** How long may a shared tablet keep an outbox and cached task packs? Default 7 days for synced records. Owner: security.
12. **Print/export format.** PDF alert pack, CSV, or both, and which fields are permitted off-network? Owner: security/operations.

Each of these has a default documented here so the build can proceed; the decision changes a configuration or a copy block, not the architecture. That is deliberate — a front end that must be re-architected by a governance decision is a front end that will miss the pilot.

---

## 19. References

All URLs were accessed in July 2026. Product claims are limited to what the cited page states; no capability is attributed to a product beyond its published description.

### Railway and industrial products

1. Siemens. *Railigent X — digital services for rail.* https://www.siemens.com/global/en/products/mobility/rail-solutions/services/digital-services/railigent.html
2. Siemens Developer Portal. *Railigent X overview.* https://developer.siemens.com/railigent-x/overview.html
3. Alstom. *The future of services is digital — HealthHub.* https://www.alstom.com/stories/future-services-digital-healthhub
4. Alstom. *HealthHub: an intelligent way to improve maintenance* (press release, 2023). https://www.alstom.com/press-releases-news/2023/2/healthhub-intelligent-way-improve-maintenance
5. Thales. *TIRIS Points Predict: smart maintenance for rail networks.* https://www.thalesgroup.com/en/united-kingdom/news/tiristm-points-predict-smart-maintenance-system-rail-networks
6. Thales. *Switching dates with data.* https://www.thalesgroup.com/en/united-kingdom/news/switching-dates-data
7. Network Rail. *Insight: using AI to run a reliable railway.* https://www.networkrail.co.uk/industry-and-commercial/insight-using-ai-to-run-a-reliable-railway
8. Network Rail Consulting. *Remote condition monitoring.* https://www.networkrailconsulting.com/service/remote-condition-monitoring/
9. Hitachi Rail. *Digital asset management.* https://www.hitachirail.com/products-and-solutions/digital-asset-management
10. Hitachi Rail. *HMAX for signalling.* https://www.hitachirail.com/products-and-solutions/digital-asset-management/hmax-for-signalling
11. Palantir. *Foundry Ontology overview.* https://palantir.com/docs/foundry/ontology/overview
12. Palantir. *Ontology applications.* https://palantir.com/docs/foundry/ontology/applications/
13. Datadog. *Monitor configuration.* https://docs.datadoghq.com/monitors/configuration
14. Datadog. *Monitor quality.* https://docs.datadoghq.com/monitors/quality
15. Grafana. *Dashboards.* https://grafana.com/docs/grafana/latest/dashboards
16. Grafana. *Panel overview.* https://grafana.com/docs/grafana/latest/visualizations/panels-visualizations/panel-overview

### Design systems

17. IBM. *Carbon Design System — 2x Grid.* https://www.carbondesignsystem.com/building-blocks/foundations/2x-grid
18. Google. *Material 3 — Typography.* https://m3.material.io/styles/typography
19. Atlassian. *Design System — Spacing.* https://atlassian.design/foundations/spacing
20. GOV.UK. *Design System — Error summary.* https://design-system.service.gov.uk/components/error-summary
21. U.S. Web Design System. *Spacing units.* https://designsystem.digital.gov/design-tokens/spacing-units/
22. Shopify. *Polaris — Layout and structure.* https://polaris.shopify.com/components/layout-and-structure
23. GitHub. *Primer — Getting started with foundations.* https://primer.style/product/getting-started/foundations
24. Vercel. *Geist — Introduction.* https://vercel.com/geist/introduction
25. Vercel. *Geist font.* https://vercel.com/font
26. Radix UI. *Primitives — Accessibility overview.* https://www.radix-ui.com/primitives/docs/overview/accessibility

### Standards and accessibility

27. W3C. *Web Content Accessibility Guidelines (WCAG) 2.2.* https://www.w3.org/TR/WCAG22/Overview.html
28. W3C WAI. *Understanding SC 2.5.8: Target Size (Minimum).* https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum
29. W3C WAI. *Understanding SC 1.4.3: Contrast (Minimum).* https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum
30. web.dev. *Core Web Vitals.* https://web.dev/articles/vitals

### Stack and platform

31. React. *React 19.* https://react.dev/blog/2024/12/05/react-19
32. Tailwind CSS. *Tailwind CSS v4.0.* https://tailwindcss.com/blog/tailwindcss-v4
33. shadcn/ui. *Documentation.* https://ui.shadcn.com/docs
34. TanStack Query. *React overview (v5).* https://tanstack.com/query/v5/docs/framework/react/overview
35. TanStack Table. *Virtualization guide.* https://tanstack.com/table/latest/docs/framework/react/guide/virtualization
36. Zustand. *Introduction.* https://zustand.docs.pmnd.rs/getting-started/introduction
37. MapLibre. *MapLibre GL JS documentation.* https://maplibre.org/maplibre-gl-js/docs/
38. deck.gl. *Documentation.* https://deck.gl/docs

### Internal sources

39. *NIDAN — Predictive Failure Propagation Engine for Indian Railway Track Circuits*, programme dossier (`docs/Research/Debdatta-Complete-Research.md`, with section splits `docs/Research/p1.md`–`p7.md`). Authoritative for the physics twin, failure-mode taxonomy F1–F12, alert policy, RUL method, SMMS payloads, cluster `c-9917`, the ADRA/TC/12T asset record and the Ayurvedic diagnostic mapping. Local file, not a public URL.
40. NIDAN mockup set, `design/mockups/` in this repository — the visual contract for this document. Screenshots in `design/mockups/screenshots/`.

---

*End of specification.*
