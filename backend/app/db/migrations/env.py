"""
Alembic environment for the Global Intelligence backend.

The DB URL is built dynamically from ``app.core.config.settings`` so
that secrets stay in environment variables and are never committed.
We run migrations synchronously over a psycopg2-compatible URL
derived from the asyncpg URL used by the app at runtime.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import settings
from app.db.base import Base  # noqa: F401 — registers all models

# Alembic Config object.
config = context.config

# Configure logging from alembic.ini if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _sync_database_url() -> str:
    """Return a sync DB URL suitable for Alembic.

    The runtime app uses asyncpg, but Alembic's migration runner is
    synchronous. We rewrite the driver portion of the URL.
    """
    url = settings.SQLALCHEMY_DATABASE_URI
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database."""
    url = _sync_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    cfg_section = config.get_section(config.config_ini_section) or {}
    cfg_section["sqlalchemy.url"] = _sync_database_url()
    connectable = engine_from_config(
        cfg_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
