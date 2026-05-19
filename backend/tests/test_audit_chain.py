"""
Audit chain integrity tests.

We exercise :class:`app.services.audit.AuditService` against an
in-memory SQLite database. SQLite has neither the advisory-lock
function nor the BYPASSRLS role, but the service degrades gracefully
in that case (see the try/except around ``pg_advisory_xact_lock``).
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, update

from app.models.audit import (
    AuditEvent,
    GENESIS_PREV_HASH,
    GENESIS_ROW_HASH,
)
from app.services.audit import audit_service


async def _seed_genesis(db) -> None:
    """Insert the genesis row that the migration would normally create."""
    import uuid
    from datetime import datetime, timezone

    db.add(
        AuditEvent(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            timestamp=datetime.now(timezone.utc),
            event_type="audit.genesis",
            outcome="success",
            prev_hash=GENESIS_PREV_HASH,
            row_hash=GENESIS_ROW_HASH,
        )
    )
    await db.commit()


@pytest.mark.asyncio
async def test_chain_valid_after_three_events(db_session):
    await _seed_genesis(db_session)

    for i in range(3):
        await audit_service.record(
            db_session,
            event_type=f"test.event.{i}",
            outcome="success",
            metadata={"i": i},
        )
        await db_session.commit()

    report = await audit_service.verify_chain(db_session)
    assert report["valid"] is True
    assert report["broken_at"] is None
    assert report["total_events"] == 4  # genesis + 3
    assert report["last_hash"] is not None


@pytest.mark.asyncio
async def test_chain_breaks_when_row_hash_tampered(db_session):
    await _seed_genesis(db_session)

    e1 = await audit_service.record(
        db_session, event_type="test.a", outcome="success"
    )
    e2 = await audit_service.record(
        db_session, event_type="test.b", outcome="success"
    )
    await db_session.commit()

    # Tamper directly via SQL — SQLite has no protective trigger here,
    # which is exactly the scenario the verifier must detect.
    await db_session.execute(
        update(AuditEvent)
        .where(AuditEvent.id == e1.id)
        .values(metadata_json={"tampered": True})
    )
    await db_session.commit()

    report = await audit_service.verify_chain(db_session)
    assert report["valid"] is False
    assert report["broken_at"] == str(e1.id)


@pytest.mark.asyncio
async def test_chain_breaks_when_link_swapped(db_session):
    await _seed_genesis(db_session)

    e1 = await audit_service.record(
        db_session, event_type="test.a", outcome="success"
    )
    e2 = await audit_service.record(
        db_session, event_type="test.b", outcome="success"
    )
    await db_session.commit()

    # Break the link: rewrite prev_hash of e2 so it no longer references
    # e1.row_hash. The verifier must catch this immediately.
    await db_session.execute(
        update(AuditEvent)
        .where(AuditEvent.id == e2.id)
        .values(prev_hash="0" * 64)
    )
    await db_session.commit()

    report = await audit_service.verify_chain(db_session)
    assert report["valid"] is False
    assert report["broken_at"] == str(e2.id)
