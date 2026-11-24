-- NIDAN backbone — initial schema (PostgreSQL 16)
--
-- Rules this schema enforces:
--   1. Predictions and assessments are append-only. A past level is never mutated;
--      every number a screen shows traces to a snapshot, a model run and a policy version.
--   2. Levels cannot contradict the published policy (the CHECK constraints below).
--   3. The only write path is workflow (acknowledge, defer, field observation, draft order).
--      There is no table, function or role that can command interlocking, signals,
--      routes, points or a track circuit.
--
-- Run order: 0001_init.sql, then seed.sql (generated from the front-end fixtures).

begin;

-- ------------------------------------------------------------------ enums

create type alert_level       as enum ('watch', 'warning', 'critical');
create type alert_status      as enum ('open', 'acknowledged', 'deferred', 'closed');
create type block_kind        as enum ('published', 'draft');
create type block_fit         as enum ('fits', 'extends', 'special', 'none');
create type circuit_type      as enum ('DC', 'AC');
create type user_role         as enum ('operator', 'maintainer', 'dste', 'service', 'admin');
create type job_status        as enum ('planned', 'drafted', 'done', 'cancelled');
create type field_finding     as enum ('confirmed', 'not-found', 'something-else');
create type work_order_status as enum ('draft', 'submitted', 'approved', 'rejected');
create type task_status       as enum ('planned', 'in-progress', 'submitted', 'closed');

-- ------------------------------------------------------------------ reference data

create table division (
  id   text primary key,
  name text not null
);

create table weather_cell (
  id    text primary key,
  label text,
  lat   numeric(8, 5),
  lon   numeric(8, 5)
);

create table relay_room (
  id          text primary key,
  division_id text not null references division (id)
);

create table app_user (
  id           uuid primary key default gen_random_uuid(),
  display_name text not null,
  role         user_role not null,
  division_id  text references division (id),
  active       boolean not null default true,
  created_at   timestamptz not null default now()
);

create table asset (
  id              text primary key,
  division_id     text not null references division (id),
  name            text not null,
  route           text not null,
  circuit_type    circuit_type not null,
  length_m        integer not null check (length_m > 0),
  installed_on    date,
  codal_life_years integer check (codal_life_years > 0),
  relay_model     text,
  supply_id       text,
  cable_id        text,
  relay_room_id   text references relay_room (id),
  weather_cell_id text references weather_cell (id),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now()
);

-- Provenance is kept beside the record, not inside it: an operator must be able to
-- tell a telemetry value from an SMMS register value.
create table asset_record_source (
  asset_id   text primary key references asset (id) on delete cascade,
  provenance text not null,
  fetched_at timestamptz not null default now()
);

-- ------------------------------------------------------------------ telemetry

create table signal_catalog (
  key         text primary key,
  label       text not null,
  unit        text not null,
  baseline    numeric,
  normal_band text
);

create table telemetry_reading (
  asset_id    text not null references asset (id) on delete cascade,
  signal_key  text not null references signal_catalog (key),
  observed_at timestamptz not null,
  value       numeric not null,
  -- 0 = measured, 1 = interpolated, 2 = suspect (logger gap, stuck value)
  quality     smallint not null default 0 check (quality between 0 and 2),
  source      text not null default 'logger',
  ingested_at timestamptz not null default now(),
  primary key (asset_id, signal_key, observed_at)
);

create index telemetry_recent_idx on telemetry_reading (asset_id, signal_key, observed_at desc);

-- ------------------------------------------------------------------ model lineage

create table model_registry (
  id          uuid primary key default gen_random_uuid(),
  name        text not null,
  version     text not null,
  trained_on  date not null,
  window_from date,
  window_to   date,
  owner       text not null,
  state       text not null default 'active' check (state in ('active', 'shadow', 'retired')),
  metrics     jsonb not null default '{}'::jsonb,
  promoted_at timestamptz,
  unique (name, version)
);

create table model_run (
  id              uuid primary key default gen_random_uuid(),
  started_at      timestamptz not null,
  finished_at     timestamptz,
  input_watermark timestamptz,
  code_version    text,
  params          jsonb not null default '{}'::jsonb,
  status          text not null default 'succeeded' check (status in ('running', 'succeeded', 'failed'))
);

-- A published picture of the network at one instant. Screens render a snapshot, never "now".
create table snapshot (
  id           uuid primary key default gen_random_uuid(),
  as_of        timestamptz not null unique,
  week         smallint not null,
  label        text not null,
  published_at timestamptz not null default now()
);

-- ------------------------------------------------------------------ rolling block

create table block_window (
  id           text primary key,
  division_id  text not null references division (id),
  service_date date not null,
  starts_at    time not null,
  ends_at      time not null,
  duration_min integer not null check (duration_min > 0),
  kind         block_kind not null,
  check (ends_at > starts_at)
);

create table block_job (
  id              text primary key,
  title           text not null,
  block_window_id text references block_window (id),
  duration_min    integer not null check (duration_min > 0),
  fit             block_fit not null,
  crew            text not null,
  status          job_status not null default 'planned'
);

create table block_job_asset (
  job_id   text not null references block_job (id) on delete cascade,
  asset_id text not null references asset (id),
  primary key (job_id, asset_id)
);

-- ------------------------------------------------------------------ clusters

create table cluster (
  id                     text primary key,
  title                  text not null,
  state                  text not null check (state in ('open', 'monitoring', 'closed')),
  summary                text not null,
  weather_cell_id        text references weather_cell (id),
  saved_block_hours      numeric(4, 2) not null default 0 check (saved_block_hours >= 0),
  predicted_cascade_asset text references asset (id),
  cascade_min_days       integer,
  cascade_max_days       integer,
  shared_edges           jsonb not null default '[]'::jsonb,
  decisions              jsonb not null default '[]'::jsonb,
  opened_at              timestamptz not null default now(),
  closed_at              timestamptz,
  check (predicted_cascade_asset is null or (cascade_min_days is not null and cascade_max_days is not null))
);

-- ------------------------------------------------------------------ assessments

create table risk_assessment (
  id                  uuid primary key default gen_random_uuid(),
  asset_id            text not null references asset (id),
  snapshot_id         uuid not null references snapshot (id),
  model_run_id        uuid references model_run (id),
  policy_version      text not null,
  level               alert_level not null,
  policy_rank         integer not null check (policy_rank > 0),
  persistence         integer not null check (persistence >= 0),
  h24                 numeric(5, 4) not null check (h24 between 0 and 1),
  h72                 numeric(5, 4) not null check (h72 between 0 and 1),
  h7d                 numeric(5, 4) not null check (h7d between 0 and 1),
  ece_zone            numeric(5, 4) not null check (ece_zone between 0 and 1),
  p10_days            integer not null check (p10_days >= 0),
  median_days         integer not null check (median_days >= p10_days),
  p90_days            integer not null check (p90_days >= median_days),
  rul_coverage        numeric(5, 4) not null check (rul_coverage between 0 and 1),
  held_out_n          integer not null check (held_out_n >= 0),
  likely_modes        text[] not null check (cardinality(likely_modes) between 1 and 3),
  mode_probability    numeric(5, 4) not null check (mode_probability between 0 and 1),
  mode_set_coverage   numeric(5, 4) not null check (mode_set_coverage between 0 and 1),
  data_trust_score    numeric(5, 4) not null check (data_trust_score between 0 and 1),
  data_trust_flags    text[] not null default '{}',
  block_window_id     text references block_window (id),
  block_fit           block_fit,
  block_minutes       integer check (block_minutes > 0),
  cluster_root        boolean not null default false,
  explanation         jsonb not null,
  ranking             jsonb not null,
  model_versions      jsonb not null,
  computed_at         timestamptz not null,
  -- The policy from the specification, enforced by the database as well as the code.
  constraint critical_rule check (level <> 'critical' or h24 > 0.5 or cluster_root),
  constraint warning_rule  check (level <> 'warning' or h72 > 0.3),
  constraint block_pairing check ((block_window_id is null) = (block_fit is null))
);

create index assessment_asset_idx on risk_assessment (asset_id, computed_at desc);
create index assessment_snapshot_idx on risk_assessment (snapshot_id);

-- ------------------------------------------------------------------ alerts

create table alert (
  id                     text primary key,
  asset_id               text not null references asset (id),
  cluster_id             text references cluster (id),
  opened_at              timestamptz not null,
  status                 alert_status not null default 'open',
  current_assessment_id  uuid references risk_assessment (id),
  deferral_reason        text,
  deferral_review_date   date,
  created_at             timestamptz not null default now(),
  constraint deferral_complete check ((status <> 'deferred') or (deferral_reason is not null and deferral_review_date is not null))
);

create index alert_status_idx on alert (status, opened_at desc);
create index alert_cluster_idx on alert (cluster_id);
create index alert_asset_idx on alert (asset_id);

-- Append-only lifecycle trail. This is the audit evidence for "who saw what, when".
create table alert_event (
  id         bigserial primary key,
  alert_id   text not null references alert (id),
  kind       text not null check (kind in ('opened', 'acknowledged', 'deferred', 'undeferred', 'closed', 'reassessed', 'note')),
  at         timestamptz not null default now(),
  actor_id   uuid references app_user (id),
  payload    jsonb not null default '{}'::jsonb
);

create index alert_event_alert_idx on alert_event (alert_id, at desc);

-- ------------------------------------------------------------------ field work

create table field_task (
  id              text primary key,
  asset_id        text not null references asset (id),
  block_window_id text references block_window (id),
  title           text not null,
  title_hi        text,
  hypothesis      text not null,
  hypothesis_hi   text,
  falsifier       text not null,
  falsifier_hi    text,
  service_date    date not null,
  starts_at       time not null,
  ends_at         time not null,
  level           alert_level not null,
  status          task_status not null default 'planned',
  check (ends_at > starts_at)
);

create table field_observation (
  id              uuid primary key default gen_random_uuid(),
  task_id         text not null references field_task (id),
  asset_id        text not null references asset (id),
  idempotency_key text not null unique,
  finding         field_finding not null,
  measurements    jsonb not null default '{}'::jsonb,
  note            text not null default '',
  device_id       text,
  created_at      timestamptz not null default now(),
  synced_at       timestamptz
);

create index observation_task_idx on field_observation (task_id, created_at desc);

-- A draft only. Submission and approval happen outside NIDAN; nothing here writes to SMMS.
create table work_order_draft (
  id              uuid primary key default gen_random_uuid(),
  alert_id        text not null references alert (id),
  action          text not null,
  block_window_id text references block_window (id),
  status          work_order_status not null default 'draft',
  smms_reference  text,
  created_by      uuid references app_user (id),
  created_at      timestamptz not null default now(),
  constraint smms_only_when_submitted check ((smms_reference is null) or (status <> 'draft'))
);

-- ------------------------------------------------------------------ reporting artefacts

create table model_health_snapshot (
  id      uuid primary key default gen_random_uuid(),
  as_of   timestamptz not null,
  payload jsonb not null,
  created_at timestamptz not null default now()
);

-- ------------------------------------------------------------------ generic audit

create table audit_log (
  id          bigserial primary key,
  at          timestamptz not null default now(),
  actor_id    uuid references app_user (id),
  actor_role  user_role,
  action      text not null,
  entity_type text not null,
  entity_id   text not null,
  before      jsonb,
  after       jsonb,
  request_id  text
);

create index audit_entity_idx on audit_log (entity_type, entity_id, at desc);

-- ------------------------------------------------------------------ immutability

create function nidan_reject_mutation() returns trigger
language plpgsql as $$
begin
  raise exception '% is append-only; insert a new row instead of %', tg_table_name, lower(tg_op)
    using errcode = 'restrict_violation';
end;
$$;

create trigger risk_assessment_immutable
  before update or delete on risk_assessment
  for each row execute function nidan_reject_mutation();

create trigger alert_event_immutable
  before update or delete on alert_event
  for each row execute function nidan_reject_mutation();

create trigger audit_log_immutable
  before update or delete on audit_log
  for each row execute function nidan_reject_mutation();

create trigger field_observation_immutable
  before delete on field_observation
  for each row execute function nidan_reject_mutation();

commit;
