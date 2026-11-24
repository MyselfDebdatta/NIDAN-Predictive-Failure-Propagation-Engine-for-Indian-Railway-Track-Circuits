# NIDAN — Mockup UI Planning

Seven static screens for the NIDAN predictive failure propagation engine, all in `pages/`. No build step, no framework, no network dependency: open `pages/index.html` in a browser and use the gallery, or open any screen directly.

| File | Screen |
|---|---|
| `pages/index.html` | Cover and screen index |
| `pages/command-center.html` | Division command centre |
| `pages/circuit-detail.html` | Circuit detail, RUL band and explanation |
| `pages/alert-queue.html` | Alert queue and triage |
| `pages/field-tablet.html` | Field confirmation (light, offline-first theme) |
| `pages/model-health.html` | Model health and trust |
| `pages/design-system.html` | Tokens, components, accessibility, vocabulary |

Shared assets: `assets/tokens.css` (design tokens, both themes), `assets/app.css` (components and patterns), `assets/app.js` (shell, tabs, sparklines, clock), `assets/fonts/` (self-hosted woff2), `assets/brand/` (the final NIDAN UI lockups, sourced from `../brand/logo/`). Captured screenshots: `screenshots/`.

The header lockup uses the real brand asset: `nidan-logo-ui-dark.svg` on dark screens and `nidan-logo-ui.svg` on the light field screen, with a separate Devanagari line at UI size. The full brand kit and rules live in [`../brand/Logo-and-Brand-Guidelines.md`](../brand/Logo-and-Brand-Guidelines.md).

Screenshots are captured at 1600 px desktop (1024 px tablet, 2× for the field screen) with headless Chrome:

```powershell
powershell -ExecutionPolicy Bypass -File assets/render.ps1          # all pages
powershell -ExecutionPolicy Bypass -File assets/render.ps1 detail   # one page
```

The implementation specification is [`../../docs/Frontend-Complete-Research-Implementation.md`](../../docs/Frontend-Complete-Research-Implementation.md). NIDAN is advisory and non-vital: no mockup contains a control affordance for interlocking, signals, routes or track circuits.
