"""Alembic environment configuration for NIDAN.

Reads DATABASE_URL from pydantic-settings (Settings.database_url) so a single
source of truth governs all connection strings.  The URL is rewritten to use
the synchronous psycopg3 driver (postgresql+psycopg) which Alembic requires.
"""

from __future__ import annotations

import re
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Resolve database URL from NIDAN Settings (or env override)
# ---------------------------------------------------------------------------


def _get_sync_url() -> str:
    """Return a synchronous psycopg3 URL derived from Settings.database_url."""
    from app.config import get_settings

    url = get_settings().database_url
    # asyncpg URL → psycopg3 sync URL
    # postgresql+asyncpg://  → postgresql+psycopg://
    # postgresql://           → postgresql+psycopg://
    url = re.sub(r"^postgresql(\+asyncpg)?://", "postgresql+psycopg://", url)
    return url


# ---------------------------------------------------------------------------
# No SQLAlchemy metadata (we use raw SQL migrations)
# ---------------------------------------------------------------------------
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no active DB connection needed)."""
    url = config.get_main_option("sqlalchemy.url") or _get_sync_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with an active DB connection."""
    url = _get_sync_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
