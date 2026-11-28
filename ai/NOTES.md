# NIDAN AI/ML Gap Analysis & Technical Notes

## 1. Gap Analysis (Against `origin/main` at `770bee2`)

### Frozen Contract & Backend State
- **API & Pydantic Models (`backend/app/models/`)**: Already implements `Alert`, `RiskScores` (`h24`, `h72`, `h7d`, `eceZone`), `Rul` (`p10Days`, `medianDays`, `p90Days`, `coverage`, `heldOutN`), `Explanation` (`physics`, `model`, `precedents`), `RankingInputs`, `DataTrust`, `ModelVersions`, and `ModelHealth`.
- **Ingest Contract (`backend/app/routes/ingest.py`)**: Exposes `POST /v1/ingest/telemetry` (canonical/CCSP/RDPMS, max 5000 samples per batch) and `POST /v1/ingest/model-run` (`ModelRunPublishRequest` -> `ModelRunPublishResponse`), enforcing `h24 <= h72 <= h7d`, `p10Days <= medianDays <= p90Days`, `critical_rule` (`h24 > 0.5 or clusterRoot`), `warning_rule` (`h72 > 0.3`), `block_pairing`, and `F1..F12` mode regex.
- **Database & Idempotency (`backend/db/0001_init.sql`, `backend/app/services/postgres_repo.py`)**: Enforces append-only `risk_assessment`, `alert_event`, and `audit_log` triggers, unique `snapshot.as_of`, and idempotency on `(snapshot_id, code_version, params_hash)`. Failed publishes record a `model_run` with `status='failed'`.
- **Frontend (`Nidan-Frontend/src/lib/api.ts`)**: Frozen REST + WS contract; switches between demo fixtures and live API via `VITE_DATA_SOURCE=api`.

### Gaps Filled by `ai/` (`nidan-ai`)
1. **Bench (`nidan_ai.bench`)**: No field telemetry dataset exists publicly; `NIDAN-Bench` (`nidan-bench/0.1`) provides a seeded, domain-randomised transmission-line generator with F1–F12 injectors, 12 canonical scenarios, and a SHA-256 manifest.
2. **Physics Twin (`nidan_ai.physics`)**: Implements the uniform lossy DC transmission line (`line.py`) and a 3-state Unscented Kalman Filter (`twin.py`) over `[log G_b, log r_eff, log feed_scale]` with Mahalanobis innovation gating.
3. **Canonical Ingestion & Features (`nidan_ai.data`)**: Strict UTC enforcement (rejects naive timestamps), leakage-safe windowing ending at `as_of`, Theil-Sen slopes, flicker rate, timing percentiles, step detector, and exact reuse of `backend/app/ingestion/qc.py` trust penalties and closed-set flags.
4. **Model Portfolio (`nidan_ai.models`)**:
   - **T1 (`anomaly.py`)**: Weather-conditioned context baseline, two-sided CUSUM/EWMA, deterministic NumPy autoencoder, Isolation Forest, persistence counter.
   - **T2 (`classifier.py`, `conformal.py`)**: Weighted `HistGradientBoostingClassifier` over first-release modes (`F1`, `F3`, `F5`, `F6`, `F12`), Mondrian/split conformal prediction sets, deterministic signed feature attributions.
   - **T3 (`graph.py`)**: Division-level heterogeneous graph (`weather_cell`, `shared_asset`, `route_dependency`, `work_history`), CPU graph-propagation risk model with explicit no-graph, Hawkes, and Bayesian-network ablations + station-level bootstrap CIs, plus deterministic common-cause clustering.
   - **T4 (`survival.py`, `conformal.py`)**: Right-censored Cox-Weibull survival with division frailty, log-time conformal RUL intervals, per-zone isotonic calibration with 3-point monotone projection.
   - **T5 (`dual_detection.py`)**: Track-circuit vs axle-counter discrepancy detector (explicitly `off` when axle-counter stream is unavailable).
5. **Explainer, Policy & Worker (`nidan_ai.explain`, `nidan_ai.policy`, `nidan_ai.worker`, `nidan_ai.eval`)**: Templated physics + model narratives with mandatory falsifiers, real-only SMMS precedent retrieval, deterministic policy levels/ranking, atomic `httpx` publisher with bounded backoff, model card/calibration SVG/metrics reporting, and `ai-ci` workflow.

---

## 2. Physics Twin Identifiability Note (Phase A1)

With terminal-only measurements (feed-end voltage $V_s$ and relay-end current $I_r$), a uniform transmission line with unknown distributed ballast conductance $G_b = 1/R_b$ and lumped series rail/bond resistance $r_{\text{eff}}$ is **not uniquely separable** from a single steady-state current sample: an increase in series resistance and a decrease in ballast resistance both reduce relay current.

NIDAN addresses this explicitly (spec §7.3):
1. **Effective parameterisation**: The UKF estimates *effective* ballast conductance $G_b$ (and reports *effective* $r_{\text{eff}}$ and supply scale), never claiming a unique physical soil or joint decomposition.
2. **Design priors**: Initial states and process-noise covariances are anchored to design parameters (`length_km`, `rail_ohm_km`, `dry_ballast_ohm_km`, `feed_v`, `source_ohm`, `relay_ohm`) from asset master data.
3. **Uncertainty propagation**: Posterior covariance $P$ (delta-method $\sigma(G_b) \approx G_b \sqrt{P_{00}}$) and single-snapshot inversion sensitivity (`invert_ballast_with_uncertainty`) are emitted into feature vectors and assessment narratives.
4. **Honest language**: Explanations always state *"effective ballast conductance"* and include a falsifier specifying a field measurement (e.g., 0.5 Ω shunt test or drop-away timing check) that would disprove the hypothesis. Full separation requires a second mid-line voltage tap or AC/AF phase-of-impedance telemetry.
