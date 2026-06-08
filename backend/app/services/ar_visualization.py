from __future__ import annotations

import json
import logging
import math
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.core.classification import ClassificationLevel

logger = logging.getLogger(__name__)


def _fetch_military_data(country_iso: str) -> dict[str, Any]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.military import MilitaryBase, MilitaryUnit, WeaponOperator, WeaponSystem
    from sqlalchemy import func, select

    async def _load() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            bases_result = await session.execute(
                select(MilitaryBase).where(
                    MilitaryBase.country_iso == country_iso.upper()
                )
            )
            bases = bases_result.scalars().all()

            units_result = await session.execute(
                select(MilitaryUnit).where(
                    MilitaryUnit.country_iso == country_iso.upper()
                )
            )
            units = units_result.scalars().all()

            return {
                "bases": [
                    {
                        "id": str(b.id),
                        "name": b.name,
                        "latitude": b.latitude,
                        "longitude": b.longitude,
                        "base_type": b.base_type,
                        "personnel_count": b.personnel_count,
                        "facilities": b.facilities or [],
                        "is_foreign_hosted": b.is_foreign_hosted,
                        "host_country_iso": b.host_country_iso,
                        "strategic_importance": b.strategic_importance,
                    }
                    for b in bases
                ],
                "units": [
                    {
                        "id": str(u.id),
                        "unit_name": u.unit_name,
                        "unit_type": u.unit_type,
                        "unit_size": u.unit_size,
                        "branch": u.branch,
                        "garrison_location": u.garrison_location,
                        "latitude": u.latitude,
                        "longitude": u.longitude,
                        "personnel_count": u.personnel_count,
                        "primary_equipment": u.primary_equipment or [],
                        "operational_status": u.operational_status,
                        "readiness_level": u.readiness_level,
                    }
                    for u in units
                ],
            }

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except RuntimeError:
        return asyncio.run(_load())


def _fetch_geo_data(layer_type: str, country_iso: str) -> list[dict[str, Any]]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.military import MilitaryBase, MilitaryUnit, ArmsTransfer
    from sqlalchemy.future import select

    async def _load() -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            if layer_type == "bases":
                result = await session.execute(
                    select(MilitaryBase).where(
                        MilitaryBase.country_iso == country_iso.upper()
                    )
                )
                return [
                    {
                        "id": str(b.id),
                        "name": b.name,
                        "latitude": b.latitude,
                        "longitude": b.longitude,
                        "type": b.base_type,
                        "personnel": b.personnel_count,
                        "strategic_importance": b.strategic_importance,
                    }
                    for b in result.scalars().all()
                ]

            elif layer_type == "units":
                result = await session.execute(
                    select(MilitaryUnit).where(
                        MilitaryUnit.country_iso == country_iso.upper()
                    )
                )
                return [
                    {
                        "id": str(u.id),
                        "name": u.unit_name,
                        "latitude": u.latitude,
                        "longitude": u.longitude,
                        "type": u.unit_type,
                        "branch": u.branch,
                        "personnel": u.personnel_count,
                        "readiness": u.readiness_level,
                    }
                    for u in result.scalars().all()
                ]

            elif layer_type == "transfers":
                result = await session.execute(
                    select(ArmsTransfer).where(
                        ArmsTransfer.recipient_iso == country_iso.upper()
                    )
                )
                return [
                    {
                        "id": str(t.id),
                        "supplier": t.supplier_country,
                        "supplier_iso": t.supplier_iso,
                        "weapon": t.weapon_description,
                        "category": str(t.weapon_category) if t.weapon_category else None,
                        "quantity": t.quantity,
                        "year": t.agreement_year,
                        "status": t.status,
                    }
                    for t in result.scalars().all()
                ]

            return []

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except RuntimeError:
        return asyncio.run(_load())


def _fetch_timeline_data(country_iso: str, days: int) -> list[dict[str, Any]]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.reports import DailyReport
    from app.models.geography import Country
    from app.models.military import ArmsTransfer
    from sqlalchemy.future import select

    async def _load() -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        async with AsyncSessionLocal() as session:
            country_result = await session.execute(
                select(Country).where(Country.iso_code == country_iso.upper())
            )
            country = country_result.scalars().first()

            if country:
                reports_result = await session.execute(
                    select(DailyReport)
                    .where(
                        DailyReport.country_id == country.id,
                        DailyReport.published.is_(True),
                        DailyReport.report_date >= cutoff,
                    )
                    .order_by(DailyReport.report_date.asc())
                )
                for r in reports_result.scalars().all():
                    events.append({
                        "id": str(r.id),
                        "type": "report",
                        "date": r.report_date.isoformat() if r.report_date else None,
                        "title": (r.executive_summary or "")[:100],
                        "classification": int(r.classification or 0),
                        "source": "daily_report",
                    })

            transfers_result = await session.execute(
                select(ArmsTransfer)
                .where(ArmsTransfer.recipient_iso == country_iso.upper())
                .order_by(ArmsTransfer.agreement_year.asc())
            )
            for t in transfers_result.scalars().all():
                events.append({
                    "id": str(t.id),
                    "type": "arms_transfer",
                    "date": f"{t.agreement_year}-01-01T00:00:00+00:00" if t.agreement_year else None,
                    "title": f"{t.supplier_country} -> {t.weapon_description}",
                    "category": str(t.weapon_category) if t.weapon_category else None,
                    "quantity": t.quantity,
                    "source": "arms_transfer",
                })

        events.sort(key=lambda e: e.get("date") or "")
        return events

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except RuntimeError:
        return asyncio.run(_load())


async def generate_3d_deployment(country_iso: str) -> dict:
    data = _fetch_military_data(country_iso.upper())
    bases = data.get("bases", [])
    units = data.get("units", [])

    equipment_counts: dict[str, int] = {}
    for unit in units:
        for equip in unit.get("primary_equipment", []):
            if isinstance(equip, dict):
                name = equip.get("name", "Unknown")
                qty = equip.get("quantity", 1)
            elif isinstance(equip, str):
                name = equip
                qty = 1
            else:
                continue
            equipment_counts[name] = equipment_counts.get(name, 0) + qty

    base_models: list[dict[str, Any]] = []
    for base in bases:
        lat = base.get("latitude", 0)
        lon = base.get("longitude", 0)
        base_models.append({
            "id": base.get("id"),
            "name": base.get("name"),
            "position": {
                "latitude": lat,
                "longitude": lon,
                "altitude": 0,
            },
            "type": base.get("base_type", "unknown"),
            "scale": 1.0,
            "rotation": {"x": 0, "y": 0, "z": 0},
            "color": _importance_color(base.get("strategic_importance")),
            "personnel": base.get("personnel_count", 0),
            "facilities": base.get("facilities", []),
        })

    unit_markers: list[dict[str, Any]] = []
    for unit in units:
        lat = unit.get("latitude")
        lon = unit.get("longitude")
        if lat is None or lon is None:
            continue
        unit_markers.append({
            "id": unit.get("id"),
            "name": unit.get("unit_name"),
            "position": {
                "latitude": lat,
                "longitude": lon,
                "altitude": 0,
            },
            "type": unit.get("unit_type", "unknown"),
            "branch": unit.get("branch", "unknown"),
            "size": unit.get("unit_size", "unknown"),
            "personnel": unit.get("personnel_count", 0),
            "readiness": unit.get("readiness_level", "unknown"),
            "operational_status": unit.get("operational_status", "unknown"),
            "movement_vector": None,
        })

    return {
        "format": "cesium-3d-tiles",
        "country_iso": country_iso.upper(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "coordinate_system": "WGS84",
        "scene": {
            "center": _compute_center(bases + [u for u in units if u.get("latitude")]),
            "zoom_level": _compute_zoom(bases + [u for u in units if u.get("latitude")]),
        },
        "bases": base_models,
        "units": unit_markers,
        "equipment_summary": [
            {"name": name, "count": count}
            for name, count in sorted(equipment_counts.items(), key=lambda x: -x[1])
        ],
        "totals": {
            "base_count": len(bases),
            "unit_count": len(unit_markers),
            "total_personnel": sum(
                b.get("personnel_count", 0) for b in bases
            ) + sum(
                u.get("personnel_count", 0) for u in units if u.get("latitude")
            ),
        },
    }


async def generate_geojson_layer(layer_type: str, country_iso: str) -> dict:
    features_data = _fetch_geo_data(layer_type, country_iso.upper())

    features: list[dict[str, Any]] = []
    for item in features_data:
        lat = item.get("latitude")
        lon = item.get("longitude")
        if lat is None or lon is None:
            continue

        properties = {k: v for k, v in item.items() if k not in ("latitude", "longitude")}

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [lon, lat],
            },
            "properties": properties,
        })

    geojson = {
        "type": "FeatureCollection",
        "metadata": {
            "layer_type": layer_type,
            "country_iso": country_iso.upper(),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "feature_count": len(features),
            "coordinate_system": "WGS84",
        },
        "features": features,
    }

    return geojson


async def generate_timeline_events(country_iso: str, days: int = 30) -> list[dict]:
    events = _fetch_timeline_data(country_iso.upper(), days)

    enriched: list[dict[str, Any]] = []
    for event in events:
        enriched.append({
            "id": event.get("id"),
            "type": event.get("type"),
            "date": event.get("date"),
            "title": event.get("title"),
            "source": event.get("source"),
            "metadata": {
                k: v for k, v in event.items()
                if k not in ("id", "type", "date", "title", "source")
            },
        })

    return enriched


def _importance_color(importance: Optional[str]) -> str:
    if importance == "Critical":
        return "#ff0000"
    if importance == "High":
        return "#ff8800"
    if importance == "Medium":
        return "#ffcc00"
    return "#00cc00"


def _compute_center(positioned_items: list[dict[str, Any]]) -> dict[str, float]:
    valid = [
        item for item in positioned_items
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    if not valid:
        return {"latitude": 0.0, "longitude": 0.0, "altitude": 0.0}

    avg_lat = sum(item["latitude"] for item in valid) / len(valid)
    avg_lon = sum(item["longitude"] for item in valid) / len(valid)
    return {"latitude": round(avg_lat, 6), "longitude": round(avg_lon, 6), "altitude": 0.0}


def _compute_zoom(positioned_items: list[dict[str, Any]]) -> float:
    valid = [
        item for item in positioned_items
        if item.get("latitude") is not None and item.get("longitude") is not None
    ]
    if len(valid) < 2:
        return 8.0

    lats = [item["latitude"] for item in valid]
    lons = [item["longitude"] for item in valid]
    lat_spread = max(lats) - min(lats)
    lon_spread = max(lons) - min(lons)
    spread = max(lat_spread, lon_spread)

    if spread < 0.01:
        return 14.0
    if spread < 0.1:
        return 11.0
    if spread < 1.0:
        return 9.0
    if spread < 5.0:
        return 7.0
    if spread < 15.0:
        return 5.0
    return 3.0


__all__ = [
    "generate_3d_deployment",
    "generate_geojson_layer",
    "generate_timeline_events",
]
