import asyncio
from datetime import datetime, timezone

from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.osint_tasks.scan_country", bind=True, max_retries=3)
def scan_country(self, country_iso: str) -> dict:
    """
    Gathers OSINT signals for a single country and persists them to the database.
    Uses asyncio.run() because Celery workers are synchronous by default.
    """
    try:
        return asyncio.run(_scan_country_async(country_iso))
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)


async def _scan_country_async(country_iso: str) -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.future import select
    from app.core.config import settings
    from app.models.geography import Country
    from app.models.intelligence import IntelligenceItem, IntelligenceCategory
    from app.agents.osint import OSINTAgent

    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        country_result = await db.execute(
            select(Country).where(Country.iso_code == country_iso.upper())
        )
        country = country_result.scalars().first()
        if not country:
            return {"error": f"Country {country_iso} not found"}

        osint = OSINTAgent()
        signals = await osint.gather_signals(country_iso)

        saved = 0
        for signal in signals:
            cat_result = await db.execute(
                select(IntelligenceCategory).where(
                    IntelligenceCategory.name == signal.get("category", "General")
                )
            )
            category = cat_result.scalars().first()
            if not category:
                category = IntelligenceCategory(
                    name=signal.get("category", "General")
                )
                db.add(category)
                await db.flush()

            item = IntelligenceItem(
                country_id=country.id,
                category_id=category.id,
                agent_source="osint_agent",
                content=signal.get("extracted_signal", ""),
                confidence_score=signal.get("confidence", 0.5),
                metadata_json={"timestamp": signal.get("timestamp")},
            )
            db.add(item)
            saved += 1

        await db.commit()

    await engine.dispose()
    return {"country": country_iso, "signals_saved": saved}


@celery_app.task(name="app.tasks.osint_tasks.scan_all_countries")
def scan_all_countries() -> dict:
    """Iterates all active countries and dispatches scan_country for each."""
    iso_codes = asyncio.run(_fetch_all_iso_codes())
    for iso in iso_codes:
        scan_country.delay(iso)
    return {"dispatched": len(iso_codes)}


async def _fetch_all_iso_codes() -> list[str]:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.future import select
    from app.core.config import settings
    from app.models.geography import Country

    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with SessionLocal() as db:
        result = await db.execute(select(Country.iso_code))
        codes = [row[0] for row in result.all()]

    await engine.dispose()
    return codes


@celery_app.task(name="app.tasks.osint_tasks.generate_daily_reports")
def generate_daily_reports() -> dict:
    """Generates published daily reports for countries that have new intelligence signals."""
    return asyncio.run(_generate_daily_reports_async())


async def _generate_daily_reports_async() -> dict:
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from sqlalchemy.future import select
    from app.core.config import settings
    from app.models.geography import Country
    from app.models.intelligence import IntelligenceItem
    from app.models.reports import DailyReport
    from app.agents.osint import OSINTAgent
    from app.agents.synthesis import synthesis_agent

    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    generated = 0
    async with SessionLocal() as db:
        countries_result = await db.execute(select(Country))
        countries = countries_result.scalars().all()

        for country in countries:
            # Only generate if there are intelligence items for this country
            intel_result = await db.execute(
                select(IntelligenceItem).where(
                    IntelligenceItem.country_id == country.id
                ).limit(1)
            )
            if not intel_result.scalars().first():
                continue

            osint = OSINTAgent()
            signals = await osint.gather_signals(country.iso_code)
            summary = await synthesis_agent.generate_daily_report(country.name, signals)

            report = DailyReport(
                country_id=country.id,
                executive_summary=summary,
                content_json="{}",
                published=True,
                report_date=datetime.now(timezone.utc),
            )
            db.add(report)
            generated += 1

        await db.commit()

    await engine.dispose()
    return {"reports_generated": generated}
