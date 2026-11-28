# NIDAN — Predictive Failure Propagation Engine

Advisory, non-vital, explainable failure forecasting for Indian Railway track circuits.

NIDAN watches the telemetry a track circuit already produces — relay current, ballast
conductance, cable insulation, feed voltage, occupancy timing — and turns it into ranked,
explainable early warnings *before* a circuit fails. It never touches interlocking, signals,
routes, points or the track circuit itself: the technician stays the decision-maker.

This repository holds five things:

| Folder | What it is |
|---|---|
| `Nidan-Frontend/` | The working front end: React 19 + TypeScript + TanStack Start, the app you run. |
| `backend/` | The advisory FastAPI REST/WebSocket API, PostgreSQL and fixture-backed in-memory repositories, database schema and seed pipeline, and API/safety/seed-integrity tests. |
| `docs/` | The product research, the implementation specification, the build brief and the front-end audit. |
| `design/mockups/` | The static, offline prototype that fixed the visual argument for the seven screens. |
| `design/brand/` | The NIDAN visual identity: logo system, palette, typography and brand sheets. |

## Repository map

```
.
├─ README.md                                        this file
├─ docs/
│  ├─ Frontend-Complete-Research-Implementation.md  product + front-end specification (the contract)
│  ├─ AI-ML-Implementation-Spec.md                  engine behind the backend contract
│  ├─ Lovable-Instruction-Frontend-Build.md         build brief for the generated front end
│  ├─ Lovable-Frontend-Audit.md                     audit of the generated app against the spec
│  ├─ Exhibition-Registration-Form-Answers.md       exhibition form answers, research-backed
│  └─ Research/
│     ├─ Debdatta-Complete-Research.md              source research dossier
│     └─ p1.md … p7.md                              chapter splits
├─ backend/
│  ├─ app/                                          FastAPI application and domain services
│  ├─ db/                                           SQL schema, fixtures, seed SQL and seed generator
│  ├─ tests/                                        API, safety-invariant and seed-integrity tests (13)
│  ├─ pyproject.toml                                Python package and test configuration
│  ├─ docker-compose.yml / Dockerfile               local backend and container setup
│  └─ Backend-Architecture-Implementation.md        backend architecture
├─ design/
│  ├─ mockups/                                      static prototype (start at pages/index.html)
│  │  ├─ Mockup-UI-Planning.md
│  │  ├─ pages/            7 screens
│  │  ├─ assets/           tokens, components, fonts, lockups, screenshot script
│  │  └─ screenshots/      7 captured PNGs
│  └─ brand/                                        visual identity
│     ├─ Logo-and-Brand-Guidelines.md                rules, geometry, palette, file manifest
│     ├─ brand-sheet.html / .png                    full visual identity document
│     ├─ contact-sheet.html / .png                  real-size legibility check
│     ├─ logo/             21 final SVG assets
│     ├─ png/              26 transparent raster exports
│     ├─ fonts/            self-hosted WOFF2 faces
│     └─ tools/            source + regeneration scripts
└─ Nidan-Frontend/                                    the shipping front end
   ├─ src/routes/          file routes (Control shell, Field shell for /field*)
   ├─ src/components/      primitives, domain components, hand-authored SVG charts
   ├─ src/data/            typed demo fixtures (single source of truth)
   ├─ src/lib/             data adapter, queries, policy, outbox, formatters
   ├─ src/styles/          semantic Day/Night tokens, self-hosted fonts
   ├─ src/test/            policy, safety-boundary, fixture-integrity, theme, routing
   └─ README.md            how to run it, screens, themes, mock → API
```

## The app

```bash
cd Nidan-Frontend
bun install
bun run dev        # http://localhost:8080
bunx vitest run    # policy, safety boundary, fixture integrity, theme, routing
bunx tsc --noEmit  # type check
```

Full detail — screens, themes, the mock → API adapter, offline outbox and the
documented stack deviations — is in
[`Nidan-Frontend/README.md`](Nidan-Frontend/README.md).

## The backend

The FastAPI backend requires Python 3.12+.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API documentation is available at `http://127.0.0.1:8000/docs`.

From the repository root, first change into `backend/`; run both commands there:

```bash
cd backend
python -m pytest -q
python -m ruff check .
```

By default, the backend can use fixture-backed in-memory repositories. PostgreSQL and Redis
connections are configured through application settings when those integrations are enabled.
The backend is advisory and non-vital: it exposes no interlocking, signalling, routing,
points or track-circuit command path.

## Entry points

| To see… | Open |
|---|---|
| The working app | [`Nidan-Frontend/`](Nidan-Frontend/) — run it as above |
| The product argument and seven screens (static) | [`design/mockups/pages/index.html`](design/mockups/pages/index.html) |
| The implementation specification | [`docs/Frontend-Complete-Research-Implementation.md`](docs/Frontend-Complete-Research-Implementation.md) |
| The AI/ML engine specification | [`docs/AI-ML-Implementation-Spec.md`](docs/AI-ML-Implementation-Spec.md) |
| The front-end audit and fix log | [`docs/Lovable-Frontend-Audit.md`](docs/Lovable-Frontend-Audit.md) |
| The logo and brand guidelines | [`design/brand/Logo-and-Brand-Guidelines.md`](design/brand/Logo-and-Brand-Guidelines.md) |
| Exhibition registration answers | [`docs/Exhibition-Registration-Form-Answers.md`](docs/Exhibition-Registration-Form-Answers.md) |
| The visual identity sheet | [`design/brand/brand-sheet.html`](design/brand/brand-sheet.html) |
| The primary logo | [`design/brand/logo/nidan-logo-primary.svg`](design/brand/logo/nidan-logo-primary.svg) |

The mockups and brand sheets are static and offline: no build step or network connection is
required to view them. The app needs the install step above.

## Regenerating design assets

From the repository root (requires `fontTools` and `uharfbuzz`, and the source TTFs in
`%TEMP%\nidan-fonts`):

```
python design\brand\tools\build_assets.py
python design\brand\tools\layers.py
python design\brand\tools\rasterize.py
python design\brand\tools\fullshot.py design\brand\brand-sheet.html design\brand\brand-sheet.png 1440 1
```

Mockup screenshots:

```
powershell -ExecutionPolicy Bypass -File design\mockups\assets\render.ps1
```

## Boundary

NIDAN is advisory and non-vital. No screen, document or brand asset contains a write path to
interlocking, signals, routes, points or track circuits — and no UI affordance for one, not
even a disabled one. Ranking, levels and cluster membership are server outputs; the browser
only sorts and filters them. `src/test/safety.test.ts` guards this boundary.

## Contributing & GitHub Workflow

`main` is a protected branch. All changes go through individual feature branches (e.g., `feature/frontend`, `feature/backend`, `feature/physics`, `feature/ai`, `feature/design`, `feature/docs`) and dedicated Pull Requests targeting `main`. See [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) for the full team PR workflow.
