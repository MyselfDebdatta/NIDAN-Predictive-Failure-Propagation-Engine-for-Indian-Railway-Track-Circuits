# NIDAN build roadmap

## Front end (this repository)

- [x] Semantic Day/Night tokens, flash-free theme and language start-up, responsive Control and Field shells, theme + language toggles, command palette.
- [x] Typed railway fixtures with a single source of truth: per-alert explanations, cluster membership derived from `alert.clusterId`, policy-consistent levels, and field readings that match the signal series. Enforced by `src/test/fixtures.test.ts`.
- [x] Mock/API adapter used across every screen.
- [x] Command centre, alert queue + triage drawer, circuit detail, common-cause clusters, Rolling Block planner.
- [x] Field task list and confirmation (offline outbox), model health, design reference.
- [x] Rolling Block offsets computed from the snapshot date (`src/lib/blocks.ts`), not hard-coded; "today"/"tomorrow" wording and an explicit "already outside p10" state.
- [x] AI evidence review: operator supplies alert + circuit context, the model drafts an evidence summary and a non-vital checklist through the platform AI gateway, with a visible data-egress notice.
- [x] Workbox service worker (`vite-plugin-pwa`): hashed assets precached, field pages and field data network-first, so the field app opens offline and the outbox drains on reconnect.
- [x] Self-hosted fonts (`public/fonts/`), no CDN dependency, precached for offline field use.
- [x] Route metadata, safety-boundary test, responsive widths (320–2560) in both themes, policy tests, fixture and block tests, README.
- [x] Accessibility: valid tablist/tabpanel with roving tabindex and arrow keys on the queue views, no `aria-selected` on table rows, `<html lang>` set before paint, 44 px field targets.
- [ ] Automated browser accessibility tests: axe sweep over the Control-room and Field screens, keyboard walkthrough, theme contrast, wired into CI.
- [ ] Later (needs backend): Storybook stories, MSW handlers, live `/v1/stream` invalidation.
