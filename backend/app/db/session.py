"""
Async SQLAlchemy session + state-grade session context.

Every request must establish the caller's clearance / org_id in the
PostgreSQL session so that Row Level Security policies can filter
rows correctly.

The :func:`get_db_with_context` dependency yields a session that has
already called ``app.set_user_context`` with the authenticated user's
clearance and org_id. Callers that need a raw session (system jobs,
migrations, anonymous endpoints) keep using :func:`get_db`.
"""

from __future__ import annotations

from typing import AsyncGenerator, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    pool_pre_ping=True,
    echo=False,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a raw async session (no RLS context set)."""
    async with AsyncSessionLocal() as session:
        yield session


get_session = get_db


async def set_user_context(
    session: AsyncSession,
    clearance: int,
    org_id: Optional[UUID],
) -> None:
    """Push the caller's clearance / org into the PG session.

    Uses the ``app.set_user_context`` helper installed by migration
    ``0001_state_grade_classification``. The function relies on
    ``SET LOCAL`` so the values are scoped to the current
    transaction.
    """
    await session.execute(
        text("SELECT app.set_user_context(:clearance, :org_id)"),
        {"clearance": int(clearance), "org_id": str(org_id) if org_id else None},
    )
