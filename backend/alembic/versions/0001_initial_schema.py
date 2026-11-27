"""Initial schema — baseline for 0001_init.sql.

This revision is used only to stamp an already-initialised database (created
by 0001_init.sql + seed.sql via Docker Compose) as being at migration head.
Run `alembic stamp 0001` after running the SQL scripts manually or via Docker.

Revision ID: 0001
Revises:
Create Date: 2026-11-27
"""

from __future__ import annotations

from alembic import op  # noqa: F401

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    """Baseline: schema already applied via 0001_init.sql.

    This revision is a no-op when stamping an already-initialised database.
    For a fresh database (without docker-compose), run:

        psql $DATABASE_URL -f backend/db/0001_init.sql
        psql $DATABASE_URL -f backend/db/seed.sql
        alembic stamp 0001

    Future schema changes should create a new revision that calls
    op.execute() with the required DDL.
    """


def downgrade() -> None:
    """Baseline: cannot downgrade past the initial schema."""
    raise RuntimeError(
        "Cannot downgrade past the initial schema revision. Drop and recreate the database instead."
    )
