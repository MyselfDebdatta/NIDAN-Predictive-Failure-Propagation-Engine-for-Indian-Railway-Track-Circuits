# Contributing to NIDAN — Team GitHub Workflow

To keep development organized across our 6–7 member team and avoid merge conflicts or broken builds, all contributors follow the **Individual Pull Request (PR) Workflow**.

---

## 1. Protected `main` Branch

- `main` is **protected** and must always remain stable and production-ready.
- **Nobody pushes code directly to `main`.**
- All changes enter `main` only through reviewed, CI-verified Pull Requests.

---

## 2. Individual Contributor / Feature Branch Workflow

Each contributor or workstream owns **one dedicated feature branch** and **one dedicated Pull Request** targeting `main`:

| Stream / Area | Branch Naming | Scope |
|---|---|---|
| Physics / Track Circuit Modeling | `feature/physics` | Signal/electrical physics & propagation models |
| AI / ML Forecasting | `feature/ai` | Predictive failure & clustering models |
| Backend & Database | `feature/backend` | `backend/` — PostgreSQL schema, seed data, FastAPI API |
| Frontend App | `feature/frontend` | `Nidan-Frontend/` — React 19 + TanStack Start UI |
| Brand & UI Design | `feature/design` | `design/` — brand assets, mockups, screenshots |
| Research & Documentation | `feature/docs` | `docs/` — research dossiers, specs, audit docs |

### Step-by-Step Workflow

1. **Create a feature branch from latest `main`:**
   ```bash
   git fetch origin
   git checkout -b feature/<your-stream> origin/main
   ```
2. **Open one Pull Request to `main` (mark as Draft while WIP):**
   - Open your PR early as a **Draft PR** so the team has visibility into your workstream.
   - Complete the checklist in [`.github/pull_request_template.md`](./pull_request_template.md).
3. **Keep updating your same branch & PR:**
   - Commit and push incremental updates to your existing branch — **do not open a new PR for every update.**
   ```bash
   git add <files>
   git commit -m "feat(<scope>): concise description"
   git push
   ```
4. **Team Review & Automated CI Checks:**
   - Automated CI (`frontend-ci`, `backend-ci`) runs on every PR push.
   - Everyone reviews open PRs, leaves constructive feedback, and the PR author addresses review comments in the same PR.
5. **Merge approved PRs one by one:**
   - Once CI passes, conversations are resolved, and approval is granted, PRs are merged into `main` **one by one**.
6. **Sync other open feature branches after each merge:**
   - Whenever a PR is merged into `main`, update your open feature branch from `origin/main` to catch conflicts early:
   ```bash
   git fetch origin
   git rebase origin/main   # or: git merge origin/main
   git push --force-with-lease   # if rebased (never force-push to main)
   ```

---

## 3. Verification Before Marking Ready for Review

- **Frontend (`Nidan-Frontend/`):**
  ```bash
  cd Nidan-Frontend
  bun install --frozen-lockfile
  bunx tsc --noEmit
  bun run lint
  bunx vitest run
  bun run build
  ```
- **Backend (`backend/`):**
  - Run linter (`ruff check`) and test suite (`pytest`) when backend code is present.
- **Safety & Advisory Boundary:**
  - NIDAN is strictly **advisory and non-vital**. Never introduce write paths or UI controls targeting interlocking, signals, routes, points, or track circuits (`Nidan-Frontend/src/test/safety.test.ts` guards this boundary).
- **Hygiene:**
  - Never commit `.env` secrets, `.venv/` / `venv/`, `__pycache__/`, `node_modules/`, `.output/`, `.wrangler/`, or local database artifacts.
