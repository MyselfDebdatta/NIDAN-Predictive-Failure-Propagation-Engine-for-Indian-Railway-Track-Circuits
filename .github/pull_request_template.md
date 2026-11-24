## Workstream / Branch
<!-- e.g. feature/physics, feature/ai, feature/backend, feature/frontend, feature/design, feature/docs -->
- Stream: 
- Status: [ ] Draft (WIP) / [ ] Ready for Review

## Summary
<!-- Describe what this PR adds or changes and why -->

## Verification
- [ ] Branched from latest `main` and synced with `origin/main`
- [ ] Pushing updates to my single dedicated branch & PR (not creating duplicate PRs)
- [ ] Frontend checks pass (`bunx tsc --noEmit`, `bun run lint`, `bunx vitest run`, `bun run build`) if `Nidan-Frontend/` changed
- [ ] Backend checks pass (`ruff`, `pytest`) if `backend/` changed
- [ ] Preserves NIDAN's advisory, non-vital safety boundary (no interlocking/signal/point/route write paths)
- [ ] No secrets (`.env`), virtualenvs (`.venv/`), `node_modules/`, or build artifacts committed
