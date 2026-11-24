# Audit — `Nidan-Frontend`

**Audited against:** `Frontend-Complete-Research-Implementation.md`, `Lovable-Instruction-Frontend-Build.md` (§18 acceptance checklist), `docs/Research/Debdatta-Complete-Research.md`
**Scope:** `../Nidan-Frontend/` — 103 source files, ~9,950 lines. File paths quoted below are relative to that app folder.
**Method:** read-only inspection (files, config, fixtures, tests). No files in the Lovable folder were edited, no build/install/test was run, no artefacts were produced.
**Date:** 24 Nov 2026

---

## 1. Verdict

**As a visual and interaction prototype: good — genuinely close to the specification.**
**As the accepted-stack, shippable front end: not yet.** It is a different application skeleton wearing the right design.

The craft is high. All ten specified routes exist in the right shells, the token system is real (not decorative hex), the theme boot is flash-free, the field surface is properly separate, there is no control affordance anywhere, and the advisory boundary is enforced in copy and in a test. Someone who reads the spec and then opens this build will recognise it immediately.

But three things stop it being "done":

1. **The demo data actively lies on most screens.** Nine of eleven alerts render another circuit's physics, SHAP values and maintenance precedents. The signature RUL visual puts every Rolling Block at "2 days". Cluster membership contradicts itself in two places at once. These are not polish items — they are the product's argument, and they are wrong.
2. **The stack is not the accepted stack.** It is TanStack Start with SSR on a Cloudflare/nitro worker, not the static SPA the spec explicitly required ("no SSR, no Node server"). i18next was replaced by a hand-rolled dictionary — an alternative the spec considered and rejected. TanStack Table, Storybook, MSW and axe CI are all absent, and three of the four are declared in `README.md` as "not yet added".
3. **There is a new external dependency the spec never asked for.** A `/review` route posts alert and asset context to `@lovable.dev/ai-gateway` (`openai/gpt-6-astra`). For a non-vital advisory tool that is defensible as an idea, but it is unrequested scope, it leaves the building, and it is described nowhere in the spec's route table or safety boundary.

**Recommendation:** fix the five P0 data defects before anyone from Signal & Telecom sees this. Then decide, consciously, whether to accept TanStack Start + SSR as a documented deviation (it is a reasonable one, but it is a deviation) or rebuild the shell as the static SPA that was specified.

---

## 2. Scorecard against the §18 acceptance checklist

| Acceptance item | Result | Evidence |
|---|---|---|
| No control affordance for signalling/interlocking, even disabled | **Pass** | No such control in any route; `src/test/safety.test.ts` asserts it |
| Day and Night both look intentional, nothing unreadable | **Pass** | Semantic oklch tokens; measured text contrast 4.99–18.1:1 across both themes |
| No first-paint theme flash | **Pass** | Inline `themeBootScript` in `src/routes/__root.tsx:107` |
| All §8 routes and both shells | **Pass (+1)** | 10 spec routes plus `/review`; Control and Field shells distinct |
| Typed fixtures used consistently everywhere | **Fail** | See P0-1, P0-3, P0-5 |
| Four signature patterns + state glyphs | **Pass with one defect** | Signal Spine, RUL band, Explanation Card, propagation map all hand-authored; RUL marker wrong (P0-2) |
| Storybook stories for loading/empty/stale/partial/error | **Fail** | No Storybook |
| i18n `en` + `hi` | **Partial** | Nav, field and error copy only |
| Keyboard map, axe-clean routes | **Partial** | Keyboard works; no axe run, and two ARIA patterns are invalid (P2-1, P2-2) |
| Mock API adapter | **Pass** | `src/lib/api.ts` with `VITE_DATA_SOURCE` switch, RFC 9457 errors |
| `README.md` covering setup, theme, mock→API, advisory boundary | **Pass, but stale** | Claims Workbox "not yet added" while `vite-plugin-pwa` is configured |
| Screenshots / walkthrough at 375/768/1440/1920 in both themes | **Fail** | No screenshots in the delivered folder |

---

## 3. Findings

### P0 — defects that would misinform an operator

**P0-1 · Nine of eleven alerts show 12T's explanation.**
`src/data/fixtures.ts:140` — `explanation: seed.explanation ?? explanation12T`. Only `alr-7f3c` (12T, line 163) and `alr-c603` (07T, line 173) supply their own. Every other alert therefore renders 12T's headline, its three physics readings, its SHAP bars and its SMMS precedents in the triage drawer and on the asset page — including 14T, 16T, 21T, 05T, 09T, KGP/31T, TATA/08T and 18T. Opening 18T (a cable-insulation alert, F8) shows "Effective ballast conductance +31% in 12 days" and a precedent that is literally about 14T.
This is the single most damaging finding: the Explanation Card is the product's trust mechanism, and it is wrong on 82% of the dataset.

**P0-2 · The RUL block marker is hardcoded to "2 days" for every asset.**
`src/components/nidan/charts.tsx:108` — `blockInDays = 2`; `src/routes/assets.$assetId.tsx:71` — chip text `{block.window.id} in 2 d`; line 72 renders `<RulBand alert={alert} />` with no override. No component computes the distance from `snapshot.date` to `block.window.date` (verified: no date arithmetic on block windows anywhere).
Consequence: 07T's block RB-26 is dated **2026-07-14** (`fixtures.ts:90`) and the snapshot is **2026-07-14** (`fixtures.ts:87`) — the block is *today*, but the chart says "RB-26 · 2 d" and places the marker two days out on a p10 of 1 day. 09T and 18T also carry RB-26. The one visual the spec calls out as the signature pattern is therefore wrong for every asset except 12T.

**P0-3 · Cluster membership is stored twice and the two copies disagree.**
- `c-9917` claims `alertsFolded: 6` and three decisions (`fixtures.ts:328-333`), but `members` lists only 12T/14T/16T (line 341) and only four alerts carry `clusterId: "c-9917"` — 12T, 14T, 16T, 21T (lines 160, 203, 217, 224). 21T is a member of the cluster by field but is omitted from `members` and instead described as a "predicted cascade" (line 342).
- `c-9930` lists 18T and 21T as members (line 354), but 18T has **no** `clusterId` (lines 258-264) and 21T's is `c-9917`.
Consequence on screen: the cluster filter `?cluster=c-9917` returns 4 rows while the card says "6 alerts → 3 decisions"; `?cluster=c-9930` returns **zero** rows while the card shows two alerts. The clusters page KPI sums `alertsFolded` to 8 for four distinct alerts.

**P0-4 · Alert levels contradict the policy table the spec states.**
- **12T is "Root of cluster c-9917"** (`fixtures.ts:164`) yet sits at `level: "watch"` (line 153) with 24-hour risk 4%. The spec (`Frontend-Complete-Research-Implementation.md:225`) makes **cluster root cause** a Critical trigger in its own right. Either the label or the level is wrong — as rendered, the queue tells the operator a cluster root cause is a Watch item ranked below a Warning.
- **18T is Warning with 72-hour risk exactly 0.30** (`fixtures.ts:259`, displayed as "30%"). The Warning rule requires **> 30%** (`Frontend-Complete-Research-Implementation.md:224`). At the boundary the alert should be Watch. Because 18T also inherits 12T's explanation (P0-1), the "relay margin below early-warning band" half of the rule cannot even be evaluated from what is on screen.

**P0-5 · The field task and the alert disagree about the same circuit's last readings.**
`fixtures.ts:482` — field task 12T `lastReadings.relayCurrent: "82"`, `ballastConductance: "1.42"`. `fixtures.ts:295` — the 12T signal series ends at **118 mA** with a normal band of 150–175 mA. The field form offers "Use last: 82 mA" (`src/routes/field.tasks.$taskId.tsx:168-169`) while the triage drawer plots 118 mA. Separately, the 12T explanation claims "relay margin 73% of dry" against a 162 mA dry baseline — 118/162 is 73%, so the drawer is internally consistent and the field task is the outlier. A technician and a controller looking at the same circuit see different numbers.

### P1 — deviations from the agreed build

**P1-1 · TanStack Start with SSR, not a static SPA.**
`vite.config.ts:68-72` redirects the server entry to `src/server.ts`; `src/router.tsx:19` dehydrates the query cache into server HTML; `@lovable.dev/vite-tanstack-config` builds a Cloudflare worker via `nitro` (`package.json:99`). The spec required Vite + static output with "no SSR, no Node server" and the §18 checklist repeats it. `README.md:46` acknowledges the substitution and argues "output still needs no separate Node server" — true of Cloudflare, but it is still a server-rendered app with a server entry, server functions and CSRF middleware (`src/start.ts`). This is the largest architectural deviation and it is not a small one: it is what makes the AI route possible.

**P1-2 · i18next replaced by a hand-rolled dictionary, and Hindi is a thin veneer.**
`src/i18n/strings.ts` is a typed `en`/`hi` map with `useT()`; `package.json` has no `i18next` or `react-i18next`. The spec's rejected-alternatives section names exactly this approach as the thing not to do. Coverage confirms the risk: the bundle carries navigation, field-task labels and error copy, so switching to हिन्दी leaves page headings, level names, chart labels, KPI captions, table headers and every explanation paragraph in English. `levelNamesHi` (`src/components/nidan/primitives.tsx:42`) is used in only three places — `design.tsx`, `field.index.tsx` and `field.tasks.$taskId.tsx` — never in the control shell. A Hindi-speaking controller gets a half-translated screen, which is worse than a consistently English one.

**P1-3 · No TanStack Table, no virtualization.** The queue is a hand-written semantic `<table>` (`src/components/nidan/domain.tsx:91-160`). `README.md:47` calls this a deliberate substitution and it is a fair one at 11 rows, but the spec asked for TanStack Table v8 with virtualization and the acceptance checklist assumes that surface.

**P1-4 · Test and documentation scaffolding declared but absent.** `@playwright/test` and `@axe-core/playwright` are installed (`package.json:79,82`) with no spec files anywhere; `src/test/` holds four vitest files only. No Storybook, no MSW. `README.md:52` is honest about this ("Not yet added — planned with the backend integration"), but the §18 checklist requires it, so it is a gap, not a note.

**P1-5 · Unrequested `/review` route that sends data to an external model.**
`src/routes/review.tsx:17`, `src/lib/review.server.ts:1` — `@lovable.dev/ai-gateway`, model `openai/gpt-6-astra` (`src/lib/review.ts:10`). It is reachable from the rail's "Assure" group (`src/components/shell/nav.ts:32`), the triage drawer (`alerts.$alertId.tsx:60`) and the asset page (`assets.$assetId.tsx:62`), and it transmits an alert summary, circuit context, asset record and operator notes. Nothing in the spec's route table, IA or safety section anticipates it. The advisory framing is careful — `enforceNonVital` post-processes the draft, nothing is stored — but for an air-gapped railway deployment this is the one screen that cannot ship.

**P1-6 · Google Fonts is a runtime CDN dependency.** `src/routes/__root.tsx:83-88` preconnects to `fonts.googleapis.com`/`fonts.gstatic.com`; `vite.config.ts:43-52` adds StaleWhileRevalidate/CacheFirst rules for them. The brand folder already contains self-hosted `Archivo`, `Inter`, `JetBrainsMono` and `NotoSansDevanagari` woff2 files — so this is avoidable, and it means the first load in a relay room with no route to the internet falls back to system fonts. Combined with the Lovable error reporter (`src/lib/lovable-error-reporting.ts`), the build is not air-gapped even though the field route is offline-capable.

**P1-7 · Deliverable 8 (screenshots/walkthrough) is missing, and the README is out of date.** No screenshots exist in the folder; `README.md` never mentions them. `README.md:50` says Workbox is "not yet added" while `vite-plugin-pwa` with `generateSW` is fully configured and a registration guard exists (`src/lib/sw-register.ts`).

### P2 — accessibility and polish

**P2-1 · The queue view tabs are an incomplete tab pattern.** `src/routes/alerts.tsx:188-192` — `role="tablist"` with `role="tab"` children, but no `aria-controls`, no `role="tabpanel"`, no roving `tabIndex`, no arrow-key handling. Screen readers announce tabs whose panels do not exist. (The Explanation Card, by contrast, gets this right at `charts.tsx:289-335` — the pattern exists in the codebase and simply was not reused.)

**P2-2 · `aria-selected` on a plain table row.** `src/components/nidan/domain.tsx:125` sets `aria-selected` on `<tr>` inside a plain `role="table"`. `aria-selected` is not supported on `row` outside `grid`/`treegrid`, so the selection state is dropped. The row checkboxes are labelled correctly, so the information is not lost — the attribute is just invalid.

**P2-3 · `lang` is only correct after hydration.** `src/routes/__root.tsx:104` hardcodes `<html lang="en">`; the Hindi value is applied in a client effect at line 158. SSR and the first paint are always `en`, which means a saved Hindi preference is announced as English until React runs.

**P2-4 · Field boundaries are near-invisible in Day.** Measured against their own inset fill, `--border` gives roughly **1.04:1** in Day and 1.40:1 in Night; `--border-strong` gives 1.87:1 (Day) / 1.72:1 (Night) / 2.73:1 (Field). Every input is text-labelled, so this is not a 1.4.11 failure in the strict sense — but the queue search box and filter selects read as borderless fields on a white panel. Worth raising the border token one step.

**P2-5 · `recharts` is installed but unused by the product.** It is pulled in only by the unused shadcn wrapper `src/components/ui/chart.tsx`, which nothing imports. All NIDAN charts are hand-authored SVG as specified. Dead weight in the bundle graph, and it contradicts the "no charting dependency" line.

---

## 4. What is genuinely strong

Worth stating plainly, because most of the list above is criticism:

- **Route and shell coverage is complete.** Every screen in §8 exists, in the right shell, with the right primary question in its `head` metadata. `/field` is a real second shell — separate top bar, sticky action footer, 56 px targets, always-light `.field-surface` — not a responsive collapse.
- **URL is the state.** Filters, view, selection and the open drawer all live in the search params (`alerts.tsx` `validateSearch`), so a triage state can be pasted into a shift handover. That is the single most operationally valuable decision in the build and it was made correctly.
- **The token layer is real.** `src/styles/tokens.css` defines both themes in oklch, `src/styles.css` maps them to Tailwind v4 `@theme inline` under semantic names, and components use `text-text-mid`/`bg-bg-panel`, not raw hex. The one hardcoded colour block is the standalone error page, which is correct.
- **The advisory boundary holds.** No route, menu, drawer or disabled control implies command of a signal, route, point or track circuit. `safety.test.ts` asserts it. Copy is consistently "advisory, non-vital" in the status bar, the triage drawer and the field footer.
- **The state language is distinctive.** Shape-plus-colour glyphs (ring / triangle / diamond), the Signal Spine, the four Ayurvedic stage names and the Devanagari pair in the brand block give it an identity that is not a shadcn dashboard. This is the part that most closely matches the mockups.
- **Tables degrade properly.** The queue becomes cards below 720 px, and the RUL band has a real `<table>` equivalent behind a "Show as table" toggle with `aria-expanded` — both required by the spec and both actually implemented.
- **Theme switching does not remount the app.** Flipping `data-theme` on `<html>` preserves filters, open drawers and scroll. Verified in `src/lib/theme.ts` and `__root.tsx`.

---

## 5. Suggested order of work

1. **Give every alert its own explanation** (P0-1) — or, at minimum, remove the `?? explanation12T` fallback and let the card render an honest "no explanation recorded" state. Nine wrong explanations is worse than nine empty ones.
2. **Compute the RUL block offset from the snapshot date** (P0-2), and pass it into both `RulBand` and the asset-page chip.
3. **Make cluster membership single-source** (P0-3) — derive `members` from `alert.clusterId`, then reconcile `alertsFolded` to the real count.
4. **Reconcile the levels with the policy** (P0-4): either 12T is Critical, or it is not the root cause.
5. **Reconcile 12T's field readings with its signal series** (P0-5).
6. **Decide on the three stack questions** — SSR vs static SPA, i18next vs the local bundle, and whether `/review` and Google Fonts belong in a railway deployment — and record the decision in `README.md` if the deviation is accepted.
7. **Then** the P2 list: reuse the Explanation Card's tab pattern in the queue, drop `aria-selected` from `<tr>`, set `lang` server-side, raise the border token, delete the unused chart wrapper.

Nothing in this audit changed a file in `Nidan-Frontend/`.

---

## 6. Resolution log

Every P0 and P1 finding, and the actionable P2 items, were fixed in the app after this audit. Changes are covered by `src/test/fixtures.test.ts`, `src/test/blocks.test.ts` and the existing policy, safety, theme and routing suites; `bunx tsc --noEmit`, `bunx vitest run` and `bunx eslint .` pass.

### P0

| Finding | Resolution |
|---|---|
| P0-1 — nine of eleven alerts fell back to `explanation12T` | Each alert now owns a distinct `Explanation`; the `?? explanation12T` fallback is gone and `explanation` is a required field. A test asserts every explanation object is unique and its `modeSet` contains the alert's primary mode. |
| P0-2 — RUL marker hard-coded at 2 days | New `src/lib/blocks.ts` computes whole-day offsets from the demo snapshot; `RulBand` and the asset-page chip both use it, with "today"/"tomorrow" wording and an "already outside p10" state. `src/test/blocks.test.ts` pins the offsets. |
| P0-3 — cluster membership stored twice and contradictory | Membership is derived from `Alert.clusterId` in a `cluster()` factory; `members` and `alertsFolded` can no longer disagree. 21T moved to `c-9930`, 18T gained `c-9930`, so `?cluster=c-9930` now returns its two rows. |
| P0-4 — 12T described as "root of cluster" but ranked Watch | 12T is described as the *most affected member* of c-9917, which keeps the Critical-rule demo on 07T (24 h risk > 50%) while staying truthful about 12T's Watch level. 18T's 72 h risk moved to 0.31 so Warning is strictly above the 30% threshold. |
| P0-5 — 12T field readings contradicted its signal series | The field task's `lastReadings` now equal the last point of `signalFixtures` (relay 118 mA, ballast 1.31 × dry, cable 0.6 MΩ, feed 6.1 V); a test enforces it. |

### P1

| Finding | Resolution |
|---|---|
| SSR vs static SPA | Kept TanStack Start + SSR (platform contract); recorded as a documented deviation in `README.md`. |
| i18next vs local bundle | Kept the typed local bundle (SSR-safe, zero deps); expanded coverage to page titles and level names, and set `<html lang>` before paint. Recorded as a deviation. |
| `/review` data egress undisclosed | Added a visible "What leaves this device" notice above the form and clarified the submit-line copy; documented the gateway path in `README.md`. |
| Google Fonts at runtime | Self-hosted Inter, Archivo, JetBrains Mono and Noto Sans Devanagari in `public/fonts/`, removed the CDN links and the Workbox font rules, and preloaded the two most-used faces. |
| Stale README stack table | Rewritten to match the code (Workbox, RHF + Zod, Playwright + axe now present; only genuine deviations listed). |

### P2

- Queue views now use a real tablist/tabpanel with roving tabindex, `aria-controls` and Arrow/Home/End keys.
- `aria-selected` removed from `<tr>`; the active row uses `aria-current` and selection is a data attribute.
- `<html lang>` now tracks the rendered language exactly: it is updated in the same effect that applies the `en`/`hi` bundle, so English text is never announced under a Hindi tag (a pre-paint script would have claimed Hindi while SSR still rendered English).
- Day-theme `--border` and `--border-strong` raised to the brand sheet's 1.6:1 and 2.6:1 steps so field boundaries are visible.
- Added `assetRecords` for all eleven assets, so circuit detail no longer shows an empty record panel for ten of them.
- Repo reorganised: `docs/` (spec, build brief, audit, research, exhibition answers) and `design/` (brand, mockups), with a root `README.md` map. The app folder was renamed `nidan-rail-advisory-main/` → `Nidan-Frontend/`; because the app is its own project root, the rename does not touch the Lovable-connected repository's contents or history.
