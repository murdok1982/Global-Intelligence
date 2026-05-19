"""
RLS integration test — requires a real PostgreSQL instance.

Set ``TEST_DATABASE_URL`` to an asyncpg URL that points at an empty
test database with the migrations applied. The test is otherwise
skipped, so the rest of the suite still passes on developer laptops
without Postgres.
"""

from __future__ import annotations

import os

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import text


_DB_URL = os.environ.get("TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not _DB_URL,
    reason="TEST_DATABASE_URL not set — RLS tests require a real Postgres",
)


@pytest_asyncio.fixture
async def pg_session():
    engine = create_async_engine(_DB_URL, future=True)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_public_clearance_cannot_see_confidential_rows(pg_session):
    """A session with clearance=PUBLIC must not see a CONFIDENTIAL row."""
    # Use the helper function installed by migration 0001 to push
    # clearance into the Postgres session.
    await pg_session.execute(
        text("SELECT app.set_user_context(:c, NULL)").bindparams(c=0)
    )
    rows = (
        await pg_session.execute(
            text(
                "SELECT id FROM intelligence_items WHERE classification = 2"
            )
        )
    ).fetchall()
    assert rows == []
