import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.api.deps import get_db, get_current_active_user, get_current_institutional_user
from app.models.geography import Country
from app.models.reports import DailyReport
from app.models.user import User
from app.schemas.report import ReportResponse, ReportDetail, ReportGenerateRequest
from app.agents.synthesis import synthesis_agent
from app.agents.osint import OSINTAgent

router = APIRouter()


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> list[ReportResponse]:
    result = await db.execute(
        select(DailyReport)
        .where(DailyReport.published.is_(True))
        .order_by(DailyReport.report_date.desc())
    )
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/{report_id}", response_model=ReportDetail)
async def get_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
) -> ReportDetail:
    result = await db.execute(
        select(DailyReport).where(
            DailyReport.id == report_id,
            DailyReport.published.is_(True),
        )
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportDetail.model_validate(report)


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def generate_report(
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_institutional_user),
) -> ReportResponse:
    country_result = await db.execute(
        select(Country).where(Country.iso_code == body.country_iso.upper())
    )
    country = country_result.scalars().first()
    if not country:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Country not found")

    osint = OSINTAgent()
    signals = await osint.gather_signals(body.country_iso)
    summary = synthesis_agent.generate_daily_report(country.name, signals)

    report = DailyReport(
        country_id=country.id,
        executive_summary=summary,
        content_json="{}",
        published=False,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return ReportResponse.model_validate(report)


@router.get("/{report_id}/premium", response_model=ReportDetail)
async def get_premium_report(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_institutional_user),
) -> ReportDetail:
    result = await db.execute(
        select(DailyReport).where(DailyReport.id == report_id)
    )
    report = result.scalars().first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return ReportDetail.model_validate(report)
