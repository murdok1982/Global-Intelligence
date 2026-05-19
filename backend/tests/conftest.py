"""
Shared pytest fixtures.

The fixtures here favour SQLite-in-memory for fast unit tests of the
audit chain and the MFA module. Tests that depend on Postgres RLS
features (``test_rls.py``) are skipped automatically when no
``TEST_DATABASE_URL`` pointing at a real Postgres is configured.
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path

# Make the backend package importable when pytest runs from any cwd.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

# Provide deterministic env defaults BEFORE app imports happen.
os.environ.setdefault("ENV", "test")
os.environ.setdefault("STATE_GRADE_MODE", "false")
os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("REFRESH_SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("MFA_ENCRYPTION_KEY", secrets.token_hex(32))
os.environ.setdefault("MFA_CHALLENGE_SECRET", secrets.token_hex(32))
os.environ.setdefault("POSTGRES_PASSWORD", "test")

import uuid as _uuid  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.dialects.postgresql import UUID as PG_UUID  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402


# Teach SQLAlchemy how to render postgresql.UUID on SQLite and how to
# round-trip the values. The default behaviour stores the UUID as
# numeric, which mis-decodes on read.
@compiles(PG_UUID, "sqlite")
def _sqlite_uuid_compile(element, compiler, **kw):  # noqa: D401
    return "CHAR(36)"


def _install_sqlite_uuid_processors() -> None:
    """Force PG UUID columns to use string serialization on SQLite."""

    def _bind_processor(self, dialect):  # noqa: ANN001
        def process(value):
            if value is None:
                return None
            if isinstance(value, _uuid.UUID):
                return str(value)
            return str(_uuid.UUID(str(value)))

        return process

    def _result_processor(self, dialect, coltype):  # noqa: ANN001
        def process(value):
            if value is None:
                return None
            if isinstance(value, _uuid.UUID):
                return value
            try:
                return _uuid.UUID(str(value))
            except Exception:
                return None

        return process

    # Patch only when on SQLite by checking dialect at call time.
    _original_bind = PG_UUID.bind_processor
    _original_result = PG_UUID.result_processor

    def bind_processor(self, dialect):  # noqa: ANN001
        if dialect.name == "sqlite":
            return _bind_processor(self, dialect)
        return _original_bind(self, dialect)

    def result_processor(self, dialect, coltype):  # noqa: ANN001
        if dialect.name == "sqlite":
            return _result_processor(self, dialect, coltype)
        return _original_result(self, dialect, coltype)

    PG_UUID.bind_processor = bind_processor
    PG_UUID.result_processor = result_processor


_install_sqlite_uuid_processors()


from app.db.base import Base  # noqa: E402


@pytest.fixture(scope="session")
def event_loop_policy():  # pragma: no cover - asyncio default
    import asyncio

    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture
async def sqlite_engine():
    """In-memory async SQLite engine for fast unit tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(sqlite_engine):
    """Async session bound to the in-memory SQLite engine."""
    session_factory = async_sessionmaker(
        bind=sqlite_engine, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session
