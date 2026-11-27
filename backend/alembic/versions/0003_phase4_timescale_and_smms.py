"""Phase 4: Read-only SMMS precedent table and conditional TimescaleDB hypertable.

Adds:
  1. smms_precedent table for read-only CRIS SMMS historical failure precedents
     surfaced in federated search and explanation retrieval.
  2. Conditional TimescaleDB hypertable conversion on telemetry_reading when the
     timescaledb extension is available on the PostgreSQL server (safe no-op on
     vanilla PostgreSQL 16 in CI/local Docker).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Create smms_precedent and conditionally enable TimescaleDB hypertable."""
    op.execute(
        """
        create table if not exists smms_precedent (
          id              text primary key,
          asset_id        text,
          division_id     text references division (id),
          failure_mode    text,
          confirmed_cause text not null,
          occurred_on     date,
          summary         text not null default '',
          provenance      text not null default 'CRIS SMMS export',
          synced_at       timestamptz not null default now()
        );
        """
    )
    op.execute(
        """
        create index if not exists smms_precedent_division_idx
          on smms_precedent (division_id, occurred_on desc);
        """
    )
    op.execute(
        """
        create index if not exists telemetry_observed_at_idx
          on telemetry_reading (observed_at desc, asset_id);
        """
    )
    op.execute(
        """
        do $$
        begin
          if exists (select 1 from pg_available_extensions where name = 'timescaledb') then
            create extension if not exists timescaledb;
            perform create_hypertable(
              'telemetry_reading',
              'observed_at',
              if_not_exists => true,
              migrate_data => true
            );
          end if;
        end
        $$;
        """
    )


def downgrade() -> None:
    """Drop Phase 4 smms_precedent table and telemetry_observed_at_idx."""
    op.execute("drop index if exists telemetry_observed_at_idx;")
    op.execute("drop index if exists smms_precedent_division_idx;")
    op.execute("drop table if exists smms_precedent;")
