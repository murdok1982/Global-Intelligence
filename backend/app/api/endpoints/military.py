"""
Military Equipment API endpoints.

Provides CRUD and query access to the military equipment database:
- Weapon systems (fighters, tanks, missiles, ships, etc.)
- Arms transfers (SIPRI-style deal tracking)
- Military bases (geolocated)
- Defense budgets (per country, per year)
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.military import (
    ArmsTransfer,
    DefenseBudget,
    MilitaryBase,
    WeaponOperator,
    WeaponSystem,
)
from app.schemas.military import (
    ArmsTransferList,
    ArmsTransferResponse,
    DefenseBudgetList,
    DefenseBudgetResponse,
    MilitaryBaseList,
    MilitaryBaseResponse,
    MilitaryStatsResponse,
    WeaponSystemList,
    WeaponSystemResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/military", tags=["military"])


@router.get("/weapons", response_model=WeaponSystemList)
async def list_weapons(
    category: Optional[str] = Query(None, description="Filter by weapon category"),
    origin: Optional[str] = Query(None, description="Filter by country of origin"),
    search: Optional[str] = Query(None, description="Search by name or designation"),
    active_only: bool = Query(True, description="Only show active systems"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    query = select(WeaponSystem)
    count_query = select(func.count(WeaponSystem.id))

    if category:
        query = query.where(WeaponSystem.category == category)
        count_query = count_query.where(WeaponSystem.category == category)
    if origin:
        query = query.where(WeaponSystem.origin == origin)
        count_query = count_query.where(WeaponSystem.origin == origin)
    if active_only:
        query = query.where(WeaponSystem.is_active == True)
        count_query = count_query.where(WeaponSystem.is_active == True)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            WeaponSystem.name.ilike(pattern) | WeaponSystem.designation.ilike(pattern)
        )
        count_query = count_query.where(
            WeaponSystem.name.ilike(pattern) | WeaponSystem.designation.ilike(pattern)
        )

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.offset((page - 1) * size).limit(size)
    query = query.order_by(WeaponSystem.name)
    result = await session.execute(query)
    items = result.scalars().all()

    return WeaponSystemList(items=items, total=total, page=page, size=size)


@router.get("/weapons/{weapon_id}", response_model=WeaponSystemResponse)
async def get_weapon(
    weapon_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WeaponSystem).where(WeaponSystem.id == weapon_id)
    )
    weapon = result.scalar_one_or_none()
    if not weapon:
        raise HTTPException(status_code=404, detail="Weapon system not found")
    return weapon


@router.get("/weapons/{weapon_id}/operators")
async def get_weapon_operators(
    weapon_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WeaponOperator)
        .where(WeaponOperator.weapon_id == weapon_id)
        .order_by(WeaponOperator.quantity.desc().nullslast())
    )
    operators = result.scalars().all()
    return [
        {
            "country_iso": op.country_iso,
            "country_name": op.country_name,
            "quantity": op.quantity,
            "operational_status": op.operational_status,
            "source": op.source,
        }
        for op in operators
    ]


@router.get("/transfers", response_model=ArmsTransferList)
async def list_arms_transfers(
    supplier_iso: Optional[str] = Query(None),
    recipient_iso: Optional[str] = Query(None),
    weapon_category: Optional[str] = Query(None),
    year_from: Optional[int] = Query(None, ge=1950, le=2030),
    year_to: Optional[int] = Query(None, ge=1950, le=2030),
    session: AsyncSession = Depends(get_session),
):
    query = select(ArmsTransfer)
    count_query = select(func.count(ArmsTransfer.id))

    if supplier_iso:
        query = query.where(ArmsTransfer.supplier_iso == supplier_iso.upper())
        count_query = count_query.where(ArmsTransfer.supplier_iso == supplier_iso.upper())
    if recipient_iso:
        query = query.where(ArmsTransfer.recipient_iso == recipient_iso.upper())
        count_query = count_query.where(ArmsTransfer.recipient_iso == recipient_iso.upper())
    if weapon_category:
        query = query.where(ArmsTransfer.weapon_category == weapon_category)
        count_query = count_query.where(ArmsTransfer.weapon_category == weapon_category)
    if year_from:
        query = query.where(ArmsTransfer.agreement_year >= year_from)
        count_query = count_query.where(ArmsTransfer.agreement_year >= year_from)
    if year_to:
        query = query.where(ArmsTransfer.agreement_year <= year_to)
        count_query = count_query.where(ArmsTransfer.agreement_year <= year_to)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ArmsTransfer.agreement_year.desc()).limit(500)
    result = await session.execute(query)
    items = result.scalars().all()

    return ArmsTransferList(items=items, total=total)


@router.get("/bases", response_model=MilitaryBaseList)
async def list_military_bases(
    country_iso: Optional[str] = Query(None),
    base_type: Optional[str] = Query(None),
    foreign_only: bool = Query(False),
    strategic_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    query = select(MilitaryBase)
    count_query = select(func.count(MilitaryBase.id))

    if country_iso:
        query = query.where(MilitaryBase.country_iso == country_iso.upper())
        count_query = count_query.where(MilitaryBase.country_iso == country_iso.upper())
    if base_type:
        query = query.where(MilitaryBase.base_type == base_type)
        count_query = count_query.where(MilitaryBase.base_type == base_type)
    if foreign_only:
        query = query.where(MilitaryBase.is_foreign_hosted == True)
        count_query = count_query.where(MilitaryBase.is_foreign_hosted == True)
    if strategic_only:
        query = query.where(MilitaryBase.strategic_importance == "Critical")
        count_query = count_query.where(MilitaryBase.strategic_importance == "Critical")

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(MilitaryBase.name).limit(500)
    result = await session.execute(query)
    items = result.scalars().all()

    return MilitaryBaseList(items=items, total=total)


@router.get("/budgets", response_model=DefenseBudgetList)
async def list_defense_budgets(
    country_iso: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    min_budget_usd: Optional[float] = Query(None),
    session: AsyncSession = Depends(get_session),
):
    query = select(DefenseBudget)
    count_query = select(func.count(DefenseBudget.id))

    if country_iso:
        query = query.where(DefenseBudget.country_iso == country_iso.upper())
        count_query = count_query.where(DefenseBudget.country_iso == country_iso.upper())
    if year:
        query = query.where(DefenseBudget.fiscal_year == year)
        count_query = count_query.where(DefenseBudget.fiscal_year == year)
    if min_budget_usd:
        query = query.where(DefenseBudget.budget_usd >= min_budget_usd)
        count_query = count_query.where(DefenseBudget.budget_usd >= min_budget_usd)

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(DefenseBudget.budget_usd.desc().nullslast()).limit(500)
    result = await session.execute(query)
    items = result.scalars().all()

    return DefenseBudgetList(items=items, total=total)


@router.get("/stats", response_model=MilitaryStatsResponse)
async def get_military_stats(
    session: AsyncSession = Depends(get_session),
):
    weapons_count = await session.execute(select(func.count(WeaponSystem.id)))
    transfers_count = await session.execute(select(func.count(ArmsTransfer.id)))
    bases_count = await session.execute(select(func.count(MilitaryBase.id)))
    budgets_count = await session.execute(select(func.count(DefenseBudget.id)))

    supplier_q = await session.execute(
        select(ArmsTransfer.supplier_country, func.count(ArmsTransfer.id))
        .group_by(ArmsTransfer.supplier_country)
        .order_by(func.count(ArmsTransfer.id).desc())
        .limit(10)
    )
    top_suppliers = [{"country": r[0], "deals": r[1]} for r in supplier_q.all()]

    recipient_q = await session.execute(
        select(ArmsTransfer.recipient_country, func.count(ArmsTransfer.id))
        .group_by(ArmsTransfer.recipient_country)
        .order_by(func.count(ArmsTransfer.id).desc())
        .limit(10)
    )
    top_recipients = [{"country": r[0], "deals": r[1]} for r in recipient_q.all()]

    total_spend_q = await session.execute(
        select(func.sum(DefenseBudget.budget_usd)).where(
            DefenseBudget.fiscal_year == 2024
        )
    )
    global_spend = total_spend_q.scalar() or 0.0

    return MilitaryStatsResponse(
        total_weapons=weapons_count.scalar() or 0,
        total_transfers=transfers_count.scalar() or 0,
        total_bases=bases_count.scalar() or 0,
        total_budgets=budgets_count.scalar() or 0,
        top_suppliers=top_suppliers,
        top_recipients=top_recipients,
        global_defense_spend_usd=global_spend,
    )


@router.get("/categories")
async def list_categories():
    return [
        {"key": "aircraft", "label": "Aeronaves de Combate", "icon": "✈️"},
        {"key": "helicopter", "label": "Helicópteros", "icon": "🚁"},
        {"key": "uav", "label": "Drones / UAV", "icon": "🛩️"},
        {"key": "tank", "label": "Carros de Combate", "icon": "🛡️"},
        {"key": "apc", "label": "Transportes Blindados", "icon": "🚛"},
        {"key": "ifv", "label": "Vehículos de Combate", "icon": "🚐"},
        {"key": "artillery", "label": "Artillería", "icon": "💥"},
        {"key": "mlrs", "label": "Cohetes / MLRS", "icon": "🚀"},
        {"key": "missile_atgm", "label": "Misiles Antitanque", "icon": "🎯"},
        {"key": "missile_aam", "label": "Misiles Aire-Aire", "icon": "✈️"},
        {"key": "missile_agm", "label": "Misiles Aire-Tierra", "icon": "💣"},
        {"key": "missile_cruise", "label": "Misiles de Crucero", "icon": "🚀"},
        {"key": "missile_ballistic", "label": "Misiles Balísticos", "icon": "☄️"},
        {"key": "missile_sam", "label": "Defensa Antiaérea", "icon": "🛡️"},
        {"key": "ship_carrier", "label": "Portaaviones", "icon": "🚢"},
        {"key": "ship_destroyer", "label": "Destructores", "icon": "⚓"},
        {"key": "ship_frigate", "label": "Fragatas", "icon": "🚤"},
        {"key": "ship_submarine", "label": "Submarinos", "icon": "🔱"},
        {"key": "radar", "label": "Radares", "icon": "📡"},
        {"key": "ew_system", "label": "Guerra Electrónica", "icon": "📻"},
        {"key": "cbrn", "label": "CBRN", "icon": "☢️"},
        {"key": "small_arm", "label": "Armamento Ligero", "icon": "🔫"},
    ]


@router.get("/origins")
async def list_origins():
    return [
        {"key": "USA", "label": "Estados Unidos", "flag": "🇺🇸"},
        {"key": "Russia", "label": "Rusia", "flag": "🇷🇺"},
        {"key": "China", "label": "China", "flag": "🇨🇳"},
        {"key": "UK", "label": "Reino Unido", "flag": "🇬🇧"},
        {"key": "France", "label": "Francia", "flag": "🇫🇷"},
        {"key": "Germany", "label": "Alemania", "flag": "🇩🇪"},
        {"key": "Israel", "label": "Israel", "flag": "🇮🇱"},
        {"key": "South Korea", "label": "Corea del Sur", "flag": "🇰🇷"},
        {"key": "Japan", "label": "Japón", "flag": "🇯🇵"},
        {"key": "India", "label": "India", "flag": "🇮🇳"},
        {"key": "Turkey", "label": "Turquía", "flag": "🇹🇷"},
        {"key": "Italy", "label": "Italia", "flag": "🇮🇹"},
        {"key": "Sweden", "label": "Suecia", "flag": "🇸🇪"},
        {"key": "Brazil", "label": "Brasil", "flag": "🇧🇷"},
        {"key": "Ukraine", "label": "Ucrania", "flag": "🇺🇦"},
    ]


__all__ = ["router"]
