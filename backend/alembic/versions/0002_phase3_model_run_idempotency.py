"""Phase 3: model_run idempotency columns and unique index.

Adds snapshot_id, params_hash, dataset_hash, and error_detail to model_run,
and enforces idempotency on (snapshot_id, code_version, params_hash) for
succeeded runs per docs/AI-ML-Implementation-Spec.md §3.2.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Add model_run lineage/idempotency columns and unique succeeded-run index."""
    op.execute(
        """
        alter table model_run
          add column if not exists snapshot_id uuid references snapshot (id),
          add column if not exists params_hash text,
          add column if not exists dataset_hash text,
          add column if not exists error_detail text;
        """
    )
    op.execute(
        """
        create unique index if not exists model_run_idempotent_idx
          on model_run (snapshot_id, code_version, params_hash)
          where status = 'succeeded'
            and snapshot_id is not null
            and params_hash is not null;
        """
    )


def downgrade() -> None:
    """Revert Phase 3 model_run columns and idempotency index."""
    op.execute("drop index if exists model_run_idempotent_idx;")
    op.execute(
        """
        alter table model_run
          drop column if exists error_detail,
          drop column if exists dataset_hash,
          drop column if exists params_hash,
          drop column if exists snapshot_id;
        """
    )
