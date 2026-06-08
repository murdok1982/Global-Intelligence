"""
Seed script for military equipment database.

Usage:
    python -m app.db.seeds.seed_military

Or via Alembic migration (automatic on first run).
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.models.military import (
    ArmsTransfer,
    DefenseBudget,
    MilitaryBase,
    WeaponSystem,
)
from app.db.seeds.weapons_seed import (
    WEAPON_SYSTEMS_SEED,
    ARMS_TRANSFERS_SEED,
    MILITARY_BASES_SEED,
    DEFENSE_BUDGETS_SEED,
)

logger = logging.getLogger(__name__)


async def seed_weapon_systems(session: AsyncSession) -> int:
    """Seed weapon systems from verified public sources."""
    existing = await session.execute(select(WeaponSystem.name))
    existing_names = set(existing.scalars().all())
    
    count = 0
    for data in WEAPON_SYSTEMS_SEED:
        if data["name"] not in existing_names:
            weapon = WeaponSystem(id=uuid.uuid4(), **data)
            session.add(weapon)
            count += 1
    
    if count > 0:
        await session.flush()
        logger.info(f"Seeded {count} weapon systems")
    return count


async def seed_arms_transfers(session: AsyncSession) -> int:
    """Seed arms transfers from SIPRI and official sources."""
    existing = await session.execute(
        select(ArmsTransfer.weapon_description, ArmsTransfer.recipient_iso, ArmsTransfer.agreement_year)
    )
    existing_keys = set(existing.all())
    
    count = 0
    for data in ARMS_TRANSFERS_SEED:
        key = (data["weapon_description"], data["recipient_iso"], data["agreement_year"])
        if key not in existing_keys:
            transfer = ArmsTransfer(id=uuid.uuid4(), **data)
            session.add(transfer)
            count += 1
    
    if count > 0:
        await session.flush()
        logger.info(f"Seeded {count} arms transfers")
    return count


async def seed_military_bases(session: AsyncSession) -> int:
    """Seed military bases from public sources."""
    existing = await session.execute(select(MilitaryBase.name))
    existing_names = set(existing.scalars().all())
    
    count = 0
    for data in MILITARY_BASES_SEED:
        if data["name"] not in existing_names:
            base = MilitaryBase(id=uuid.uuid4(), **data)
            session.add(base)
            count += 1
    
    if count > 0:
        await session.flush()
        logger.info(f"Seeded {count} military bases")
    return count


async def seed_defense_budgets(session: AsyncSession) -> int:
    """Seed defense budgets from SIPRI."""
    existing = await session.execute(
        select(DefenseBudget.country_iso, DefenseBudget.fiscal_year)
    )
    existing_keys = set(existing.all())
    
    count = 0
    for data in DEFENSE_BUDGETS_SEED:
        key = (data["country_iso"], data["fiscal_year"])
        if key not in existing_keys:
            budget = DefenseBudget(id=uuid.uuid4(), **data)
            session.add(budget)
            count += 1
    
    if count > 0:
        await session.flush()
        logger.info(f"Seeded {count} defense budgets")
    return count


async def run_seed() -> None:
    """Run all seed functions."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting military database seed...")
    
    async with AsyncSessionLocal() as session:
        try:
            weapons = await seed_weapon_systems(session)
            transfers = await seed_arms_transfers(session)
            bases = await seed_military_bases(session)
            budgets = await seed_defense_budgets(session)
            
            await session.commit()
            logger.info(
                f"Seed complete: {weapons} weapons, {transfers} transfers, "
                f"{bases} bases, {budgets} budgets"
            )
        except Exception as e:
            await session.rollback()
            logger.error(f"Seed failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())
