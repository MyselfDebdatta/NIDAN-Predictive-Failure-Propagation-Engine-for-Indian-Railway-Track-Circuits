# NIDAN — Lovable Front-End Build Prompt

**File to paste into Lovable:** this entire document is the prompt. It is self-sufficient: you do not need to open any other file to build the product, but the paths at the end point to the full specification and brand kit if they are available in your environment.

| | |
|---|---|
| Deliverable | A production-grade, responsive, day/night front end for NIDAN |
| Input specification | `Frontend-Complete-Research-Implementation.md` (19 sections) |
| Visual reference | `design/mockups/pages/*.html` and `design/mockups/screenshots/*.png` |
| Brand kit | `design/brand/Logo-and-Brand-Guidelines.md`, `design/brand/logo/*.svg` |
| Status | Front-end only. Backend, models and integrations come later. |

---

## 0. How to use this prompt

1. Paste this document (or attach it) as the first message to Lovable.
2. Ask Lovable to build the whole app in one pass, then iterate screen by screen using the acceptance checklist in §18.
3. If the environment cannot install a package from §2, implement the equivalent locally with the same public API and record the substitution in `README.md`. **Do not silently downgrade the design or the behaviour.**

---

## 1. Mission

Build the front end of **NIDAN — Predictive Failure Propagation Engine for Indian Railway Track Circuits**.

NIDAN listens to track-circuit telemetry and produces a ranked, explainable, advisory hypothesis about what is degrading, how fast, and which already-published Rolling Block window can absorb the fix. The front end must make a section engineer's decision at 02:40 legible, defensible and fast — on a wall display, a laptop, a phone or a field tablet.

The product must feel like a **modern, premium railway control instrument**, not a generic SaaS dashboard and not a government portal. It should be visually distinctive: deep navy/ink authority, precise typography, one confident teal signal, generous calm space, and data that is obviously real. Clean, uncluttered, attractive, modern — every pixel earns its place.

**Non-vital boundary (absolute):** NIDAN is advisory. There is no write path to interlocking, signals, routes, points, block instruments or track circuits. Do not render any control affordance — not even a disabled one. No "Set route", "Operate points", "Apply to interlocking", no lock icon implying a permission that could be granted. The absence of control is a feature; make it feel deliberate.

---

## 2. Stack and bootstrap

Use exactly this stack unless the environment blocks it:

| Layer | Choice |
|---|---|
| UI | **React 19 + TypeScript (strict)** |
| Build | **Vite 6** (static output, no SSR, no Node server to deploy) |
| Styling | **Tailwind CSS v4** with `@theme inline` mapped to CSS custom properties |
| Primitives | **Radix UI via shadcn/ui**, vendored under `src/components/ui/` |
| Server state | **TanStack Query v5** |
| Table | **TanStack Table v8 + Virtual v3** (virtualize above 50 rows) |
| UI state | **Zustand** (two small stores only) |
| Forms | **React Hook Form + Zod** |
| i18n | **i18next + react-i18next** (`en`, `hi`) |
| Charts | **Hand-authored SVG** + `d3-scale`/`d3-shape` for math only — no chart library |
| Offline | **Workbox 7 + idb** for the field route |
| Tests | Vitest, Testing Library, Playwright, axe-core, MSW |

Fallbacks if unavailable: React 18 + `useState` optimistic updates; Tailwind v3 configured with `colors: { ...: 'var(--token)' }`; headless primitives hand-written with the same ARIA behaviour; plain `<table>` with row-level interaction. Keep the same component names and props so a later upgrade is mechanical.

Never use: a chart library, a component kit with its own visual language (MUI, Ant, Bootstrap), CSS-in-JS, a backend framework, a server runtime, stock photography, emoji icons.

---

## 3. Source of truth and brand assets

- **Specification:** `Frontend-Complete-Research-Implementation.md` — domain, roles, token names, payloads, accessibility, routes, benchmarks. Follow it wherever this prompt is silent.
- **Mockups:** `design/mockups/pages/index.html` (gallery), `command-center.html`, `circuit-detail.html`, `alert-queue.html`, `field-tablet.html`, `model-health.html`, `design-system.html`; screenshots in `design/mockups/screenshots/`. Use these as structural and data references, **not as a visual ceiling** — deliver a cleaner, more polished production interpretation with the same information hierarchy.
- **Brand:** `design/brand/Logo-and-Brand-Guidelines.md`. Copy `design/brand/logo/nidan-logo-ui.svg` (ui header), `nidan-logo-primary.svg` (light), `nidan-logo-primary-dark.svg` (dark) and `nidan-favicon.svg` into `public/brand/` if present. Never rebuild the wordmark by hand. If the SVGs are unavailable, use this inline signal mark in a 20×20 viewBox as the fallback:

```html
<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7"
     stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
  <path d="M1.5 11h2.6L6 4.6l2.6 11L11 9.4l1.3 3.2h4.4"/>
</svg>
```

Brand palette: Ink `#0A121A`, Navy `#0B2545`, Signal Teal `#0E8F86` (graphics on light), Bright Teal `#2DD4BF` (signal on dark), Deep Teal `#0B6B63` (small teal text on light), Gold `#C8922F` (caution/precedent, never decoration), Paper `#F7FAFC`, Slate `#5B7288`. The brand never uses red; the **product** uses red for Critical only. Do not recolor the signal green, add gradients to the mark, or add a descriptor to the primary lockup.

---

## 4. Design system: two themes, one set of names

The app has **two complete, equally polished themes** — Night (default control room) and Day (light, modern, friendly). Both use identical semantic variable names; only the values change. The user can switch at any time and their choice persists.

Write `src/styles/tokens.css` with these two blocks (extend with the full ramp from the spec, but these values are the contract):

```css
:root,
[data-theme="night"] {
  color-scheme: dark;
  --bg-app: #060C12;
  --bg-chrome: #080F16;
  --bg-panel: #0E1822;
  --bg-raised: #12202C;
  --bg-inset: #0A1420;
  --bg-hover: rgba(255, 255, 255, 0.035);
  --bg-active: rgba(56, 224, 206, 0.09);
  --border: #1A2C3A;
  --border-strong: #2A4256;
  --border-subtle: rgba(255, 255, 255, 0.06);
  --text-hi: #EFF6FB;
  --text-mid: #A8BECD;
  --text-lo: #7A93A5;
  --accent: #38E0CE;
  --accent-text: #7CF3E4;
  --accent-wash: rgba(56, 224, 206, 0.10);
  --warning: #F9BE5C;
  --warning-wash: rgba(249, 190, 92, 0.10);
  --critical: #FF6B70;
  --critical-wash: rgba(255, 107, 112, 0.10);
  --ok: #46CBA0;
  --focus-ring: #7CF3E4;
  --shadow-1: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-2: 0 8px 24px -12px rgba(0, 0, 0, 0.7);
}

[data-theme="day"] {
  color-scheme: light;
  --bg-app: #F7FAFC;
  --bg-chrome: #FFFFFF;
  --bg-panel: #FFFFFF;
  --bg-raised: #F2F6F9;
  --bg-inset: #EDF2F6;
  --bg-hover: rgba(11, 37, 69, 0.04);
  --bg-active: rgba(11, 107, 99, 0.08);
  --border: #DCE5EC;
  --border-strong: #AFC0CE;
  --border-subtle: rgba(11, 37, 69, 0.08);
  --text-hi: #0B2545;
  --text-mid: #33454F;
  --text-lo: #5B7288;
  --accent: #0E8F86;
  --accent-text: #0B6B63;
  --accent-wash: rgba(14, 143, 134, 0.09);
  --warning: #7A4A00;
  --warning-wash: rgba(200, 146, 47, 0.12);
  --critical: #B4232A;
  --critical-wash: rgba(180, 35, 42, 0.08);
  --ok: #0F7A57;
  --focus-ring: #0B6B63;
  --shadow-1: 0 1px 2px rgba(11, 37, 69, 0.06);
  --shadow-2: 0 12px 32px -18px rgba(11, 37, 69, 0.30);
}
```

Shared scale (same in both themes):

```css
--font-sans: "Inter", "Segoe UI", system-ui, sans-serif;
--font-display: "Archivo", "Inter", sans-serif;
--font-deva: "Noto Sans Devanagari", "Nirmala UI", sans-serif;
--font-mono: "JetBrains Mono", ui-monospace, Consolas, monospace;

--fs-display: 34px; --lh-display: 38px;
--fs-h1: 25px;      --lh-h1: 31px;
--fs-h2: 18px;      --lh-h2: 24px;
--fs-h3: 14.5px;    --lh-h3: 20px;
--fs-body: 13.5px;  --lh-body: 20px;
--fs-sm: 12px;      --lh-sm: 17px;
--fs-xs: 11px;      --lh-xs: 15px;

--s1: 4px; --s2: 8px; --s3: 12px; --s4: 16px; --s5: 20px;
--s6: 24px; --s7: 32px; --s8: 40px; --s9: 48px;

--r-xs: 3px; --r-sm: 5px; --r-md: 8px; --r-lg: 12px;

--dur-1: 90ms; --dur-2: 140ms; --dur-3: 200ms;
--ease-out: cubic-bezier(0.22, 0.61, 0.36, 1);
--max-content: 1560px;
```

**Rules**

- Components use semantic variables only. No raw hex, no named colour, no colour-specific class per theme. A component that hard-codes `#FFF` will break Day or Night and fails review.
- Day mode must not be an inverted dark theme: lighter surfaces, navy type, fine borders, soft shadows, and the same information density. Night mode uses hairlines and no glow.
- Measured contrast floors: Night `#EFF6FB/#060C12` 18:1, `#A8BECD/#0E1822` 9.3:1, teal 11.9:1, amber 10.7:1, red 6.5:1. Day navy-on-paper 14.7:1, deep teal 6.4:1, slate 4.8:1, critical 6.5:1. Never put `#0E8F86` text on paper (3.97:1) — it is for graphics; use `#0B6B63` for text.
- Colour is never the sole carrier of state (see §11).
- Use 8-point spacing, a 12-column grid with 20 px gutters, small radii, one soft elevation. No glassmorphism, no neon glow, no large consumer radii, no gradients on UI surfaces.

---

## 5. Typography and bilingual detail

- **Archivo 600** for display/brand; **Inter** for UI; **JetBrains Mono** for IDs, telemetry, risk numbers and RUL values; **Noto Sans Devanagari** for Hindi. Self-host or use a reliable font CDN; include a system fallback stack.
- Numbers use `font-variant-numeric: tabular-nums`. Risk is whole percent in tables, one decimal in prose; RUL is whole days. Never `toFixed` ad hoc — one `formatRisk`, `formatRul`, `formatCount` module.
- Headings are sentence case. Uppercase eyebrows use `0.085em` tracking and at most four words. Nothing below 10 px; 10 px only for axis ticks.
- Devanagari: line height ≥1.6×, no `text-transform`, no tracking, no truncation, pair with English at the same visual size, set `lang="hi"` so shaping is correct. Devanagari numerals stay Latin (`24%`, `9 दिन`).
- Bilingual coverage: field tasks, confirmations, errors, safety copy and navigation labels. Model metrics, SHAP labels and IDs stay English.

---

## 6. Responsiveness — non-negotiable

The website must behave correctly on **every phone, tablet, laptop, desktop, monitor and window size**, in both portrait and landscape, at any width and height. Treat responsiveness as a primary feature, not a media-query afterthought.

| Width | Behaviour |
|---|---|
| 320–479 px | Compact phone: single column, 2-up KPIs, bottom tab bar, full-screen drawers, tables become cards, topbar 56 px |
| 480–767 px | Large phone: single column, larger type, 2-up panels, cards for tables |
| 768–1023 px | Tablet: 2-column panels, rail collapses to icons or bottom bar, tables keep 4 priority columns |
| 1024–1279 px | Small laptop: icon rail + 8/12-col content; hide tertiary table columns |
| 1280–1599 px | Desktop: full rail, 12-col grid, full table |
| ≥1600 px | Wall display: content centred at `max-width: 1560px`, fluid gutters, no stretched tables |

Rules:

1. `html, body { overflow-x: hidden }` is not a fix — design so nothing overflows in the first place. Test at 320 px, 375 px, 768 px, 1024 px, 1440 px, 1920 px and 2560 px.
2. Use `min-height: 100dvh`, not fixed viewport heights. Short windows (e.g. 1280×600) must scroll internally where appropriate, never clip a primary action.
3. Mobile navigation: persistent **bottom tab bar** with five destinations (Home, Alerts, Asset, Models, Field) plus a `More` sheet for the rest. On narrow landscape phones the bar moves to the side. Active tab is shape + word + colour.
4. Panels stack in DOM reading order; no side-by-side squeeze. KPI tiles: 4-up desktop, 2-up phone.
5. Dense queue table: priority columns first (level, asset, risk 24 h, RUL p10). Under 720 px render each row as a card with the same fields and the same accessible name. Never hide the level word, the risk or the RUL.
6. Drawer/triage becomes a full-screen sheet on phones with a sticky close and primary action; at desktop it is a right-side panel over the queue.
7. Touch targets: **44 px minimum** everywhere, **56 px on the field route**. No hover-only actions, no swipe-only gestures, no long-press requirements.
8. Support 200% text zoom and 400% reflow: no clipped text, no horizontal scroll, focus never hidden under sticky chrome.
9. Theme toggle, search and primary action remain reachable on every breakpoint. Test one-handed phone use.
10. Keep it uncluttered: one primary action per screen; secondary data behind tabs, drawers or `Show more`. Whitespace is a design element, especially in Day mode.

---

## 7. Theme switching

- A `ThemeToggle` in the topbar (desktop) and in the mobile menu/header (phone) with explicit **Day / Night** options and an icon, not a colour-only switch.
- Initial theme: saved choice if present, else `prefers-color-scheme`, else Night.
- Persist to `localStorage` under `nidan-theme`. Apply `data-theme` to `<html>` **before first paint** with a tiny inline script in `index.html` to avoid a flash of the wrong theme.
- Both themes share every layout, chart and component; switching must not remount routes or clear filters.
- Honour `prefers-reduced-motion` in both themes.
- The field route (`/field/*`) always uses its own warm high-contrast light surface for sunlight, regardless of the user's Day/Night preference; say so in its footer.

---

## 8. Routes and shells

Two shells: **Control** (topbar + left rail + main + statusbar) and **Field** (single topbar + sticky action footer, no rail).

| Route | Screen | Shell |
|---|---|---|
| `/` | Command centre | Control |
| `/alerts` | Alert queue | Control |
| `/alerts/:alertId` | Triage drawer over queue | Control |
| `/assets/:assetId` | Circuit detail | Control |
| `/clusters` | Common-cause clusters | Control |
| `/blocks` | Rolling Block planner | Control |
| `/models` | Model health & trust | Control |
| `/field` | Field task list | Field |
| `/field/tasks/:taskId` | Field confirmation | Field |
| `/design` | Design system reference | Control |

The topbar carries: brand, scope breadcrumb (`SER / ADRA / ADRA YARD`), an `Advisory · non-vital` chip, search (`Ctrl/⌘ K`), theme toggle, language toggle and role. The statusbar carries: advisory statement, SMMS state, model versions, IST clock. Rail groups: **Operate** (command centre, alert queue with count, circuit detail, common cause), **Assure** (model health, field app), **Reference** (design system, cover/gallery).

Use a global command palette for `Ctrl/⌘ K`: search assets, alerts, clusters and SMMS IDs; keyboard navigable; `Esc` closes and restores focus; it only navigates, never executes a command.

---

## 9. Screens to build

Build all seven. Each must look like a real product screen with realistic data — no lorem ipsum, no placeholder charts, no empty states as the default.

### 9.1 Command centre `/`

- Header: eyebrow `SER / ADRA / ADRA YARD`, title **"Adra division, next 7 days"**, scope chips, `Export pack` and `Refresh`.
- Four KPI tiles: Open alerts **11**, Critical this shift **1**, Cluster-adjusted work **5**, Rolling Block fit **78%**. Include small trend deltas.
- **Signal Spine** (left, 5 cols): ordered line of 8 assets with state shapes, IDs, risk 7 d and links.
- **Propagation map** (right, 7 cols): schematic SVG showing `12T → 14T → 16T` inside cluster `c-9917` and a predicted cascade to `21T` in 6–11 days. It is schematic, not a geographic map; deterministic layout.
- **Common cause** panel: `c-9917` drain/weather cell, 6 alerts folded into 3 decisions, estimated 2.1 block-hours saved.
- **Priority queue**: 8 rows with level, asset, route, mode, risk, RUL, block fit, one action each.
- **Rolling Block · week 29**: seven-day strip with jobs fitted into published windows; RB-28 on 16 Jul 02:10–03:40.
- One primary action per view. Do not add a chart wall.

### 9.2 Circuit detail `/assets/ADRA%2FTC%2F12T`

Reading order (this is the product's diagnostic spine):

1. Header: `ADRA/TC/12T`, `Adra Yard · Down Goods`, Watch chip, data trust 0.62, back to queue.
2. Four-stage rail: **Pūrvarūpa → Nidāna → Samprāpti → Upaśaya** (early signs, cause, course, response) with the current stage marked. Always paired with English.
3. **RUL band**: SVG with p10 **9 d**, median **21 d**, p90 **38 d**, 30-day threshold line, RB-28 marker at day 2 (inside p10), conformal coverage 0.897 from 3,180 held-out outcomes. Direct labels, no legend. Include a `Show as table` equivalent.
4. **Three-lens Explanation Card** (tabs, Physics default): Physics = ballast conductance +31% in 12 days, relay margin 73% of dry, explicit falsifier; Model = signed SHAP (`relay_i_slope_7d −0.41` log-odds, `rain_72h −0.12`), conformal set `{F1, F4}` at 0.90, calibration note; Precedents = SMMS-evt-118/204/377 with similarity and outcome.
5. **Signals**: four sparklines with dry baselines — relay current, ballast conductance, feed voltage, cable insulation.
6. **Likely failure mode**: F1 at 0.71, conformal set `{F1, F4}`, exclusions F2 joint and F5 relay.
7. **Cluster c-9917**: members 12T, 14T, 16T; shared weather cell `wx-20.30N-85.83E` and drain; predicted 21T cascade.
8. **Recommended action**: ballast clearing + drain rodding, 90 min, inside RB-28; consequence of deferral stated.
9. **Asset record**: 420 m, DC, installed 01 Mar 2009, codal life 15 y, relay `XYZ/RLY/TR12`, supply `XYZ/IPS/1`, cable `XYZ/CBL/N2`, relay room `XYZ/RR/1`, data trust flags `age_vs_signature_mismatch`, provenance.

Primary action: `Draft SMMS entry` — creates a draft only, never submits work.

### 9.3 Alert queue `/alerts`

Header, four KPIs (Open 11, Critical 1, Watch 7, Median age 3.2 h), filter bar (level, mode, route, cluster, block fit, data trust, saved view, search), view tabs (Triage, By cluster, By block, Deferred), bulk bar, dense table with 10 rows, side drawer.

Columns: level (shape + word), asset, route, likely mode, risk 24 h / 72 h, RUL p10, cluster, block fit, age. Sort by policy rank, not alphabet. Selected row opens the triage drawer with a full explanation and a persistent **"Why this order"** panel that names the ranking inputs in words: calibrated risk × consequence × exposure, discounted by data trust, block fit as tie-breaker. Bulk defer of a Critical row is impossible; any defer needs a reason and review date.

### 9.4 Field confirmation `/field/tasks/:taskId`

Different instrument, not a shrunken desktop: warm paper ground, white cards, 2 px borders, 56 px targets, 16–18 px body, 24 px task title, no rail, sticky footer.

Task: `ADRA/TC/12T`, block RB-28 02:10–03:40, Watch, one-line hypothesis + falsifier. Three steps: (1) measurements (relay current 82 mA, ballast conductance 1.42×, cable insulation 0.6 MΩ, numeric keypad, camera placeholder); (2) finding — `Confirmed` / `Not found` / `Something else` as large choices; (3) confirm summary with SMMS draft fields and a single `Queue offline` action. Show last sync time, `3 queued offline`, offline dot, `EN | हिं` toggle, and the bilingual advisory footer. Data is written locally first and syncs in the background; never block the UI on the network.

### 9.5 Model health `/models`

Four KPIs (ECE 0.031, coverage 0.897, 5 active models, 1 drift monitor amber). Panels: reliability diagram (SVG, diagonal + bins), calibration by level (predicted/observed/n, lead time, the deliberate conservatism of the Critical band), registry strip (twin 0.3.1, GNN 0.2.0, survival 0.2.4, classifier 0.2.0), performance by F1–F6, drift monitors (PSI with thresholds), data trust (0.62; low-trust assets are shown, never suppressed), promotion gates (calibration, coverage, subgroup parity, shadow period) with a signature line. No promote/rollback control — this page is evidence for a review, not the review.

### 9.6 Design system `/design`

A long reference page rendered from the same tokens and components: colour ramp, type specimens, spacing/grid, state language, components, data display, motion, accessibility, bilingual vocabulary, voice do/don't. It is the only page allowed to show all states side by side.

### 9.7 Cover / gallery `/` in the prototype

Not part of the app routes: the static prototype's `index.html` is a thesis + numbered screen index. In the React build, use `/design` and the rail for reference; do not ship a marketing landing page as the app home. The app home is the command centre.

---

## 10. Signature patterns (build once, reuse everywhere)

### 10.1 Signal Spine

Ordered `<ol>` with a vertical hairline; each node encodes state by **shape**: hollow ring = Watch, filled triangle = Warning, diamond with dark core = Critical, solid dot = Nominal. ID in mono, route, risk % and a supplementary bar. The whole row is a link; the shape is `aria-hidden` because the state word is present. Max 8 rows on the command centre. Fade the line at the bottom. This is what makes density scannable — do not replace it with a donut or a heat map.

### 10.2 Three-lens Explanation Card

ARIA tablist with Physics / Model / Precedents, Physics always default. Tabs use `←/→`, `Home/End`, focus follows selection. SHAP is signed around a centre line with direction in text ("increases risk"), not colour alone. The falsifier is in a bordered notice block, not small print. Precedent feedback writes to a retrieval index only — say so. If data is missing, keep the tab and state what is missing.

### 10.3 RUL band

`<figure>` with an SVG band: p10–p90 shaded, median tick, 30-day threshold, block marker, direct labels, plus an always-present table equivalent behind `Show as table`. `role="img"` with a sentence summary: *"Remaining useful life: p10 9 days, median 21 days, p90 38 days. RB-28 is in 2 days, inside the 10th percentile."* At 320 px reduce to three ticks, never fewer.

### 10.4 Rolling Block fit row

Date/window, job title, assets, duration and a fit chip: `fits` (teal), `+20 min` (amber), `Special` (red), `No published block` (neutral). The word always accompanies the colour. No casual "Request block" button — a draft opens with details pre-filled and requires SSE confirmation.

### 10.5 Anti-patterns

No donut charts of failure modes, no gauges for risk, no pulsing Critical rows, no gradient health maps, no sparkline without a baseline, no "confidence %" without calibration, no faux "health score" that hides the failure mode.

---

## 11. State language and vocabulary

Four states, four shapes, always shape + word + number:

| State | Shape | Word | Colour |
|---|---|---|---|
| Nominal | solid 8 px dot | Nominal | muted grey-teal |
| Watch | hollow 10 px ring | Watch | teal |
| Warning | filled 11 px triangle | Warning | amber |
| Critical | filled diamond with dark core | Critical | red |

Alert policy is rendered, never computed in the browser: Watch = 7-day risk >20% or RUL p10 <30 d (persist 3 evaluations); Warning = 72 h risk >30% with relay margin in early-warning band; Critical = 24 h risk >50% with high confidence or cluster root cause. Show "3 evaluations" style persistence in the copy.

Use correct Indian Railways vocabulary: **track circuit** (not sensor/loop), **relay room**, **block / Rolling Block** (not outage), **failure mode F1–F12**, **Watch/Warning/Critical**, **remaining useful life**, **acknowledge** (not approve), **data trust**, **SSE (Sig)**, **Adra division, South Eastern Railway**. Bilingual pairs: ट्रैक सर्किट, रिले कक्ष, ब्लॉक, विफलता प्रकार, निगरानी/चेतावनी/गंभीर, शेष उपयोगी आयु, बैलास्ट प्रतिरोध.

Failure modes F1 low ballast resistance · F2 insulated/glued joint · F3 rail bond/continuity/break · F4 metallic bridging at points · F5 relay ageing · F6 power supply/feed · F7 lightning/surge · F8 cable fault · F9 shunting failure (wrong-side risk) · F10 stray/traction interference · F11 maintenance/config error · F12 no-fault-found.

Ayurvedic spine (UX motif, not a medical claim): Pūrvarūpa = drift/Watch; Nidāna = physics twin + explanation; Samprāpti = graph + survival/RUL; Upaśaya = Rolling Block intervention. Always paired with English; never a puzzle to decode.

---

## 12. Mock data (use exactly this scenario everywhere)

Create `src/data/fixtures.ts` with typed fixtures. Every screen uses the same assets and timestamps so inconsistencies are obvious.

```ts
export type AlertLevel = "watch" | "warning" | "critical";
export type FailureModeCode = "F1" | "F2" | "F3" | "F4" | "F5" | "F6" | "F7" | "F8" | "F9" | "F10" | "F11" | "F12";

export interface Alert {
  id: string;
  assetId: string;       // "ADRA/TC/12T"
  assetName: string;     // "Adra Yard · Down Goods"
  route: string;         // "Down Goods"
  level: AlertLevel;
  risk: { h24: number; h72: number; h7d: number; eceZone: number };
  rul: { p10Days: number; medianDays: number; p90Days: number; coverage: number; heldOutN: number };
  likelyModes: FailureModeCode[];
  modeSetCoverage: number;
  clusterId?: string;
  dataTrust: { score: number; flags: string[] };
  block?: { window: BlockWindow; fit: "fits" | "extends" | "special" | "none"; minutes: number };
  explanation: Explanation;
  ageMinutes: number;
  modelVersions: { twin: string; gnn: string; survival: string; classifier: string };
}

export const alert12T: Alert = {
  id: "alr-7f3c",
  assetId: "ADRA/TC/12T",
  assetName: "Adra Yard · Down Goods",
  route: "Down Goods",
  level: "watch",
  risk: { h24: 0.04, h72: 0.11, h7d: 0.24, eceZone: 0.04 },
  rul: { p10Days: 9, medianDays: 21, p90Days: 38, coverage: 0.897, heldOutN: 3180 },
  likelyModes: ["F1"],
  modeSetCoverage: 0.90,
  clusterId: "c-9917",
  dataTrust: { score: 0.62, flags: ["age_vs_signature_mismatch"] },
  block: {
    window: { id: "RB-28", date: "2026-07-16", start: "02:10", end: "03:40", durationMin: 90, kind: "published" },
    fit: "fits",
    minutes: 90,
  },
  explanation: {
    physics: {
      headline: "Effective ballast conductance +31% in 12 days; relay margin 73% of dry",
      state: [
        { label: "Relay current", value: "118 mA", baseline: "162 mA dry" },
        { label: "Ballast conductance", value: "1.31 × dry", baseline: "1.00" },
        { label: "Rain, 72 h", value: "96 mm", baseline: "median 22 mm" },
      ],
      falsifier: "If insulation falls below 0.5 MΩ the ranking moves to F2 (joint), not F1.",
    },
    model: {
      shapTop: [
        { feature: "relay_i_slope_7d", label: "Relay current slope, 7 d", value: -0.41 },
        { feature: "rain_72h", label: "Rainfall, 72 h", value: -0.12 },
      ],
      calibrationNote: "Scores in this bin historically over-predict by 2 points; ECE 0.031.",
      modeSet: ["F1", "F4"],
      modeSetCoverage: 0.9,
      agreement: "high",
    },
    precedents: [
      { smmsId: "SMMS-evt-118", assetId: "ADRA/TC/14T", confirmedMode: "F1", similarity: 0.88, daysAgo: 64,
        outcome: "Drain rodded; 41 days to next alert" },
      { smmsId: "SMMS-evt-204", assetId: "ADRA/TC/09T", confirmedMode: "F1", similarity: 0.81, daysAgo: 148,
        outcome: "Ballast cleared; no recurrence in 10 months" },
      { smmsId: "SMMS-evt-377", assetId: "BKSC/TC/22T", confirmedMode: "F4", similarity: 0.72, daysAgo: 211,
        outcome: "Points bridging; joint replaced" },
    ],
  },
  ageMinutes: 192,
  modelVersions: { twin: "0.3.1", gnn: "0.2.0", survival: "0.2.4", classifier: "0.2.0" },
};
```

Add realistic siblings: `ADRA/TC/14T` (Warning, F1, 34% / 72 h, cluster c-9917), `ADRA/TC/16T` (Watch, F4, 27% / 7 d), `ADRA/TC/21T` (Watch, predicted cascade, 22% / 7 d), plus other divisions for filters. Include one Critical row for the queue: `ADRA/TC/07T`, F9 shunting failure (wrong-side risk), 52% / 24 h, level Critical, `special` block fit. Asset record for 12T: 420 m, DC, installed 2009-03-01, codal life 15 y, relay `XYZ/RLY/TR12`, supply `XYZ/IPS/1`, cable `XYZ/CBL/N2`, relay room `XYZ/RR/1`, weather cell `wx-20.30N-85.83E`.

Show a `Demo data` chip in the statusbar. Never claim these are live readings.

---

## 13. Repository and component structure

```
src/
├─ app/            App.tsx, router.tsx, providers.tsx, error boundaries
├─ components/
│  ├─ ui/          vendored Radix/shadcn primitives
│  ├─ primitives/  Panel, KpiTile, LevelBadge, RiskCell, Chip, StageRail
│  ├─ data/        SignalSpine, RulBand, ShapBars, Sparkline, PropagationMap
│  ├─ domain/      ExplanationCard, BlockFitRow, AssetRecord, QueueTable, TriageDrawer
│  └─ field/       FieldConfirm, MeasurementField, OfflineBadge
├─ features/       command-centre, alerts, asset-detail, clusters, blocks, models, field, search
├─ lib/            api, query keys, formatters, a11y, analytics, offline
├─ stores/         ui.ts, sync.ts
├─ i18n/           en/, hi/, config.ts
├─ styles/         tokens.css, app.css
├─ types/          domain.ts, api.ts, stream.ts
└─ data/           fixtures.ts
```

Rules: one job per component; no component fetches data; no colour literal in components; `className` and `ref` forwarded; URL holds filters, sort, view and open drawer; Zustand holds only drawer/palette/density and sync state; server data lives only in TanStack Query. Every route has loading, empty, stale, partial and error states.

---

## 14. Interactions and states

- Loading skeletons match final geometry; no spinner where a skeleton exists. Rail count is live; queue rows do not reorder while a drawer is open.
- Stale data (>15 min) gets an amber `as of 14:26 IST` chip and disables destructive bulk actions; never show an old number without its age.
- Partial failure isolates panels behind error boundaries; a failed Explanation tab does not blank the RUL band. Retry button is in the same place in every error panel and preserves filters.
- Every mutation is reversible: acknowledge and defer are optimistic with rollback. Never optimistically change risk, RUL, level or cluster membership.
- `Acknowledge` means "seen", not "resolved". Alerts close only through a technician outcome or an explicit, attributed SSE decision.
- Bulk actions state their count, cap at 50 rows, and preview cluster merges before commit.
- Toasts confirm user actions only; a Critical alert never arrives as a toast.

---

## 15. Accessibility

Target **WCAG 2.2 AA** in both themes, with these stricter internal rules: 44 px controls (56 px field), 7:1 body contrast, 400% reflow, no motion beyond 280 ms and none under `prefers-reduced-motion`, no live-updating number without a timestamp and pause control.

- Real `<table>` with `<th scope>`; under 720 px a definition-list card view with the same accessible names.
- ARIA tablist for explanations; dialog focus trap and `Esc`; focus returns to the invoking row.
- Level glyphs are `aria-hidden` when the word is present; charts are `role="img"` with sentence summaries and a table equivalent.
- Visible 2 px focus ring with 1 px offset; never `outline: none` alone. `lang="hi"` on Hindi spans.
- Keyboard map: `/` focuses search, `↑/↓` move rows, `Enter` opens, `Space` selects, `Shift+Space` range-selects, `Esc` closes, `Ctrl/⌘ K` palette. No single-letter shortcut while typing.
- Error summary links to fields; labels are visible and persistent; validation on blur/submit, never per keystroke.
- Test with axe in CI, keyboard-only, NVDA/VoiceOver/TalkBack, greyscale screenshots and 400% zoom.

---

## 16. Motion

Short and purposeful: 90/140/200 ms, opacity and ≤4 px translate only, ease-out. Panels crossfade; drawer slides 12 px; tab indicator moves. Nothing loops, nothing pulses, no auto-playing carousels. `prefers-reduced-motion: reduce` collapses all durations to near zero. Motion explains a change of state; it never decorates.

---

## 17. Backend/ML seam (build now, wire later)

Create a typed API client with a **mock adapter** that currently returns fixtures. Switching `VITE_DATA_SOURCE=mock|api` must swap the adapter without touching components.

Endpoints to mirror: `GET /v1/alerts`, `GET /v1/alerts/{id}`, `GET /v1/assets/{id}`, `GET /v1/assets/{id}/explanation`, `GET /v1/blocks`, `GET /v1/models/health`, `POST /v1/alerts/{id}/acknowledge`, `POST /v1/alerts/{id}/defer`, `POST /v1/work-orders/draft`, `POST /v1/field/observations`.

A WebSocket `/v1/stream` later sends invalidation events (`alert.upserted`, `alert.closed`, `cluster.updated`, `block.published`, `model.promoted`, `heartbeat`). The client must treat events as invalidation signals and refetch; never assemble display objects from events. Coalesce bursts at 250 ms; degrade to 30 s polling if reconnects fail. Field observations queue in IndexedDB with a UUID idempotency key and drain on reconnect. Errors use RFC 9457 problem details with `traceId`, shown in a copyable chip.

**The API surface has no interlocking/signal/route/track-circuit command endpoint. Keep it that way.**

---

## 18. Deliverables and acceptance criteria

Deliver:

1. All routes from §8, all seven screens from §9, both control and field shells.
2. `tokens.css` with both themes, Tailwind mapping, and a `ThemeToggle` with persistence and no first-paint flash.
3. Four signature patterns from §10 and the state glyph system from §11.
4. Typed fixtures from §12 used consistently across every screen.
5. Component library from §13 with Storybook stories for loading/empty/stale/partial/error.
6. i18n bundles `en` + `hi`, keyboard map, axe-clean routes, mock API adapter.
7. `README.md` explaining setup, theme switching, mock-to-api switch, and the advisory boundary.
8. Screenshots or a recorded walkthrough at 375 px, 768 px, 1440 px and 1920 px in **both** themes.

Acceptance checklist — every item must be true:

- [ ] No control affordance for signalling/interlocking anywhere, even disabled.
- [ ] Day and Night both look intentional and beautiful; no unreadable state in either.
- [ ] No horizontal overflow at 320, 375, 768, 1024, 1440, 1920, 2560 px; landscape phones work.
- [ ] Tables become readable cards below 720 px; bottom tab bar on phones; drawers become sheets.
- [ ] Every primary action reachable by keyboard and thumb; 44/56 px targets.
- [ ] State is shape + word + colour everywhere; greyscale screenshots remain readable.
- [ ] RUL band always shows p10/median/p90, the block marker and a table equivalent.
- [ ] Explanation card defaults to Physics and always exposes a falsifier.
- [ ] No raw hex outside token files; no chart library; no lorem ipsum; no stock imagery.
- [ ] `prefers-reduced-motion` honoured; axe reports zero serious/critical issues.
- [ ] Switching theme does not reset route, filters or open drawer.
- [ ] The site feels like a unique, modern, clean, professional railway instrument — not a generic template.

---

## 19. Explicitly do not

- Do not build a marketing landing page as the app home; the command centre is home.
- Do not add a dark-mode-only aesthetic or a light mode that is just inverted dark.
- Do not add gradients, glass blur, neon glow, huge radii, emoji, illustrations or hero photos.
- Do not cram every metric onto one screen; disclose progressively.
- Do not invent sources, statistics, product capabilities or live data. Label demo data as demo.
- Do not translate model metrics into pseudo-Hindi; identifiers stay as identifiers.
- Do not add a settings page for alert thresholds; they are governed, versioned and signed.
- Do not implement "resolve all", "auto-close", "apply to interlocking", or any command path.
- Do not ship a screen that only works at 1440 px.

---

## 20. Start here

Your first response should confirm the plan in five lines, then implement in this order:

1. Bootstrap Vite + React + TS + Tailwind, write both theme token blocks, shell and theme toggle.
2. Types + fixtures + API mock adapter.
3. Primitives and the four signature patterns.
4. Command centre → alert queue → circuit detail → field confirmation → model health → design system.
5. Responsive pass at every breakpoint in both themes, accessibility pass, then screenshots and README.

Build it as if a section engineer will use it tonight. Clean, calm, precise, responsive, beautiful — and always advisory.
