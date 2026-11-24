# NIDAN — Repository Agent Guidelines

This repository uses a **protected `main` branch** and an **Individual Pull Request (PR) Workflow** for a 6–7 member team. Every agent working in this repository **must** read and follow these rules before doing any Git or GitHub activity.

## Mandatory Reading Before Any Git / GitHub Work

1. [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md) — full Individual PR Workflow rules (branching, single Draft/Ready PR per stream, incremental pushes, reviews, one-by-one merges, syncing from `origin/main`).
2. [`.github/pull_request_template.md`](.github/pull_request_template.md) — required PR structure and checklist.
3. [`README.md`](README.md) — repository layout and safety boundary.
4. Area-specific guides when touching a module:
   - Frontend (`Nidan-Frontend/`): [`Nidan-Frontend/AGENTS.md`](Nidan-Frontend/AGENTS.md), [`Nidan-Frontend/README.md`](Nidan-Frontend/README.md), [`docs/Frontend-Complete-Research-Implementation.md`](docs/Frontend-Complete-Research-Implementation.md)
   - Design (`design/`): [`design/brand/Logo-and-Brand-Guidelines.md`](design/brand/Logo-and-Brand-Guidelines.md), [`design/mockups/Mockup-UI-Planning.md`](design/mockups/Mockup-UI-Planning.md)
   - Research / Physics / AI (`docs/`): [`docs/Research/Debdatta-Complete-Research.md`](docs/Research/Debdatta-Complete-Research.md)

## Non-Negotiable GitHub Rules

- **Never push or force-push directly to `main`.** Always work on a dedicated `feature/<stream>` branch created from `origin/main`.
- **One branch and one PR per contributor / stream** (e.g., `feature/physics`, `feature/ai`, `feature/backend`, `feature/frontend`, `feature/design`, `feature/docs`). Open as a **Draft PR** first if WIP, and push all subsequent updates to that same branch & PR—never create duplicate PRs for updates.
- **Keep your branch synced with `origin/main`:** Whenever another PR merges into `main`, run `git fetch origin` and merge/rebase `origin/main` into your feature branch (if using a Lovable-connected branch, merge rather than force-pushing/rewriting published history).
- **Pass CI before requesting review or marking Ready:** Both `frontend-ci` and `backend-ci` in [`.github/workflows/ci.yml`](.github/workflows/ci.yml) must pass.
- **Advisory / Non-Vital Safety Boundary:** Never add write paths or UI controls targeting interlocking, signals, routes, points, or track circuits (`Nidan-Frontend/src/test/safety.test.ts` guards this).
- **No secrets or build artifacts:** Never commit `.env`, `.venv/`, `venv/`, `__pycache__/`, `node_modules/`, `.output/`, `.wrangler/`, or `*.sqlite*`.
