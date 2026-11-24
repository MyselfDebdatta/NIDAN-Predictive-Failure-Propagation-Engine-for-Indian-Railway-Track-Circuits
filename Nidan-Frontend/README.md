# NIDAN — front end

Predictive Failure Propagation Engine for Indian Railway track circuits. **Advisory and non-vital**: there is no write path to interlocking, signals, routes, points, block instruments or track circuits, and no UI affordance for one — not even a disabled one.

## Screens

| Route | Screen | Shell |
|---|---|---|
| `/` | Command centre | Control |
| `/alerts` | Alert queue (filters, views and drawer live in the URL) | Control |
| `/alerts/:alertId` | Triage drawer over the queue | Control |
| `/assets/:assetId` | Circuit detail (e.g. `/assets/ADRA%2FTC%2F12T`) | Control |
| `/clusters` | Common-cause clusters | Control |
| `/blocks` | Rolling Block planner | Control |
| `/models` | Model health & trust | Control |
| `/review` | AI evidence review — the only page that calls a model | Control |
| `/field` | Field task list | Field |
| `/field/tasks/:taskId` | Field confirmation | Field |
| `/design` | Design system reference | Control |

## Setup

```bash
bun install
bun run dev      # http://localhost:8080
bun run build    # production build (TanStack Start + Workbox service worker)
bunx vitest run  # policy, safety boundary, fixtures, blocks, theme, routing
bunx tsc --noEmit
bunx eslint .
```

## Stack

| Layer | Used here |
|---|---|
| Framework | React 19 + TypeScript + Vite 8, **TanStack Start** with SSR (file routes, `__root.tsx` shell switch) |
| Styling | Tailwind CSS v4 (`@theme inline` over semantic tokens), Radix primitives, shadcn-style components |
| Data | TanStack Query options in `src/lib/queries.ts`, dehydrated through `@tanstack/react-router-ssr-query` |
| Client state | Zustand (`src/stores/ui.ts`, `src/stores/sync.ts`) |
| Forms | React Hook Form + Zod |
| Charts | Hand-authored SVG components in `src/components/nidan/charts.tsx` (no chart library) |
| Offline | `vite-plugin-pwa` + Workbox (precache + network-first field pages) and an IndexedDB outbox (`idb`) |
| i18n | Typed local bundles (`en`, `hi`) in `src/i18n/strings.ts` |
| Tests | Vitest + Testing Library; `@playwright/test` and `axe-core` available for browser a11y checks |

## Themes

- Tokens live in `src/styles/tokens.css` (`[data-theme="night"]`, `[data-theme="day"]`) and are mapped to Tailwind v4 utilities in `src/styles.css` (`@theme inline`). Components use semantic tokens only.
- The Day / Night toggle (top bar, phone "More" sheet, and inside the triage drawer) writes `localStorage["nidan-theme"]`.
- First paint: an inline script in `src/routes/__root.tsx` applies the saved choice, else `prefers-color-scheme`, else Night, before any CSS paints — no flash.
- Language is applied after hydration (the server cannot know a saved choice), and `<html lang>` is updated in the same effect as the bundle, so the attribute always matches the language actually on screen.
- Switching theme only flips `data-theme` on `<html>`; routes, filters and open drawers are not remounted.
- The field route always uses its own warm, high-contrast light surface (`.field-surface`) for sunlight, independent of the Control-room theme.
- Fonts are self-hosted from `public/fonts/` (`src/styles/fonts.css`) and precached by the service worker; the app loads no font from a CDN, so the field route works with no route to the public internet.

## Mock → API

All data goes through `src/lib/api.ts`. `VITE_DATA_SOURCE=mock` (default) returns the typed fixtures in `src/data/fixtures.ts`; `VITE_DATA_SOURCE=api` with `VITE_API_BASE_URL` calls the `/v1/*` endpoints. Components never fetch directly — they read TanStack Query options from `src/lib/queries.ts`. Errors surface as RFC 9457 problem details with a `traceId`.

The fixtures are a single source of truth: every alert owns its explanation, cluster membership is derived from `alert.clusterId` (never stored twice), levels satisfy the published policy thresholds, and the field task's "last reading" equals the last point of the signal series. `src/test/fixtures.test.ts` enforces all four.

Field observations are written to IndexedDB first (`src/lib/outbox.ts`, UUID idempotency key) and synced in the background; the code path is identical online and offline.

## AI evidence review and data egress

`/review` is the only screen that sends anything outside the device. On submit it posts the selected alert, its circuit context and the operator's notes through the Lovable AI gateway to a hosted model (`src/lib/review.server.ts`); the model returns an evidence summary and a draft checklist. The route states this in a visible notice before the form, and again under the submit button.

- Nothing is persisted by NIDAN and nothing is written to SMMS or applied to equipment.
- `LOVABLE_API_KEY` stays server-side and is never shipped to the browser.
- Every other screen works with this route unused; if a deployment's data policy forbids external processing, the page can be removed without touching the rest of the app.

## Documented deviations from the specification

The accepted stack in `docs/Frontend-Complete-Research-Implementation.md` is honoured except where the Lovable hosting contract or a deliberate engineering call requires otherwise. Each deviation is small, local and reversible.

| Specified | Used | Why |
|---|---|---|
| Vite 6 static SPA | TanStack Start (React 19, Vite 8) with SSR | The Lovable platform requires TanStack Start and its SSR entry; the build still needs no separately managed Node server. |
| TanStack Table + Virtual | Hand-written semantic `<table>` with a roving-tabindex row model | ≤ 50 rows in scope; same props surface, so it can be swapped mechanically. |
| i18next + react-i18next | Typed local bundles in `src/i18n/strings.ts` (`en`, `hi`) with `useT()` | Small fixed vocabulary; keys move to i18next unchanged if the vocabulary grows. |
| d3-scale / d3-shape | Inline linear scales in the SVG chart components | Only linear scales were needed. |
| Storybook, MSW | Not added | Planned with the backend integration; component states are exercised on `/design`. |

Workbox 7 (`vite-plugin-pwa`), React Hook Form + Zod, Zustand and `idb` are used as specified. Playwright and axe-core are installed for browser-level accessibility checks.

## Repository layout

```
src/
├─ routes/        file routes; __root.tsx selects the Control or Field shell
├─ components/
│  ├─ nidan/      primitives, domain components, hand-authored SVG charts
│  └─ ui/         shadcn-style Radix wrappers
├─ data/          typed demo fixtures (single source of truth)
├─ lib/           api adapter, queries, policy, blocks, formatters, outbox, theme, sw-register
├─ stores/        Zustand UI and sync stores
├─ i18n/          typed en/hi bundles and the language boot script
├─ styles/        tokens, fonts, base and component layers
└─ test/          policy, safety boundary, fixtures, blocks, theme, routing
```
