# NIDAN AI/ML Engine (`nidan-ai`)

Advisory, non-vital physics-twin and machine-learning scoring engine for Indian Railway track circuits.

> **Safety boundary:** `nidan-ai` reads telemetry and emits advisory risk assessments only. It holds no write path, credential, or API route to Electronic Interlocking, signals, routes, points, axle counters, or track-circuit hardware. The only outbound writes permitted are `POST /v1/ingest/telemetry` and `POST /v1/ingest/model-run`.
>
> **Bench-only disclaimer:** Metrics reported from `NIDAN-Bench` (`nidan-bench/0.1`) are simulation properties labelled by bench version, seed, split, and model version — never claims of field accuracy.

## Installation (Python 3.12+)

Install the frozen backend contract package first, then `nidan-ai`:

```bash
pip install -e backend
pip install -e "ai[dev]"
```

Optional graph extra (`torch`) for scale-out GraphSAGE experiments (not required for CPU POC or CI):

```bash
pip install -e "ai[dev,graph]"
```

## Quickstart

Dry-run offline scoring (zero network calls, validates every row against `backend/app/models`):

```bash
python -m nidan_ai.worker.run --scenario monsoon-60d --seed 42 --dry-run --out ai/reports/monsoon-60d.json
```

Publish telemetry batches + atomic `model_run` against a running backend (`AUTH_MODE=dev` or bearer token):

```bash
python -m nidan_ai.worker.run --scenario monsoon-60d --seed 42 --publish
```

Shadow-mode assurance and promotion (spec A13/A15). `--shadow` records one observation in a
local JSON registry (default `artifacts/registry.json`) without publishing anything.
`--promote-check` evaluates all seven promotion gates and promotes only after a >= 28-day
shadow window with calibration, coverage, subgroup parity, drift, safety and contract gates
green; a later gate failure rolls the pointer back to the previous active version.

```bash
python -m nidan_ai.worker.run --scenario monsoon-60d --seed 42 --shadow
python -m nidan_ai.worker.run --scenario monsoon-60d --seed 42 --promote-check
```

Read-only database input (`--source db`) requires `NIDAN_AI_READONLY_DATABASE_URL` (or
`NIDAN_AI_DATABASE_URL` / `DATABASE_URL`) and `--as-of`; the loader issues SELECTs only.

A CPU-only container image is provided at `ai/Dockerfile` (installs the frozen backend
contract first). Build from the repository root:

```bash
docker build -f ai/Dockerfile -t nidan-ai .
docker run --rm nidan-ai --scenario monsoon-60d --seed 42 --dry-run
```

## Verification

```bash
ruff format --check ai
ruff check ai
pytest ai/tests -m "not slow and not integration"
```
