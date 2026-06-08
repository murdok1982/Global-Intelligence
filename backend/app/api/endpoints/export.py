from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_active_user,
    get_current_institutional_user,
    get_db,
)
from app.core.classification import ClassificationLevel, can_user_access
from app.models.user import User
from app.services import export_service
from app.services.edge_sync import (
    compute_delta,
    prepare_offline_package,
    sync_field_reports,
    validate_device,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


class OfflinePackageRequest(BaseModel):
    country_iso: str
    classification: str = "RESTRICTED"


class FieldReportSubmission(BaseModel):
    device_id: str
    reports: list[dict]


class DeltaRequest(BaseModel):
    last_sync: datetime
    country_iso: str


@router.get("/report/{report_id}/pdf")
async def export_report_pdf(
    report_id: UUID,
    classification: str = Query("RESTRICTED"),
    current_user: User = Depends(get_current_institutional_user),
) -> Response:
    user_clearance = ClassificationLevel.from_any(current_user.clearance_level)
    requested_level = ClassificationLevel.from_any(classification)
    if not can_user_access(user_clearance, requested_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient clearance for requested classification",
        )
    if user_clearance < ClassificationLevel.RESTRICTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RESTRICTED clearance minimum required for PDF export",
        )

    try:
        pdf_bytes = await export_service.export_pdf(report_id, classification)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    watermarked = await export_service.add_watermark(
        pdf_bytes, current_user.id, datetime.now().isoformat()
    )
    sig = await export_service.sign_export(watermarked)

    headers = {}
    if sig.get("fingerprint"):
        headers["X-Signature-Fingerprint"] = sig["fingerprint"]
    if sig.get("signature"):
        headers["X-Signature"] = sig["signature"]

    return Response(
        content=watermarked,
        media_type="application/pdf",
        headers=headers,
    )


@router.get("/report/{report_id}/docx")
async def export_report_docx(
    report_id: UUID,
    current_user: User = Depends(get_current_institutional_user),
) -> Response:
    if ClassificationLevel.from_any(current_user.clearance_level) < ClassificationLevel.RESTRICTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RESTRICTED clearance minimum required for DOCX export",
        )

    try:
        docx_bytes = await export_service.export_docx(report_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    watermarked = await export_service.add_watermark(
        docx_bytes, current_user.id, datetime.now().isoformat()
    )
    sig = await export_service.sign_export(watermarked)

    headers = {}
    if sig.get("fingerprint"):
        headers["X-Signature-Fingerprint"] = sig["fingerprint"]
    if sig.get("signature"):
        headers["X-Signature"] = sig["signature"]

    return Response(
        content=watermarked,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@router.get("/report/{report_id}/json")
async def export_report_json(
    report_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Response:
    try:
        json_bytes = await export_service.export_json(report_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    watermarked = await export_service.add_watermark(
        json_bytes, current_user.id, datetime.now().isoformat()
    )
    sig = await export_service.sign_export(watermarked)

    headers = {}
    if sig.get("fingerprint"):
        headers["X-Signature-Fingerprint"] = sig["fingerprint"]
    if sig.get("signature"):
        headers["X-Signature"] = sig["signature"]

    return Response(
        content=watermarked,
        media_type="application/json",
        headers=headers,
    )


@router.get("/report/{report_id}/markdown")
async def export_report_markdown(
    report_id: UUID,
    current_user: User = Depends(get_current_active_user),
) -> Response:
    try:
        md_content = await export_service.export_markdown(report_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    md_bytes = md_content.encode("utf-8")
    watermarked = await export_service.add_watermark(
        md_bytes, current_user.id, datetime.now().isoformat()
    )

    return Response(
        content=watermarked,
        media_type="text/markdown",
    )


@router.post("/offline-package")
async def create_offline_package(
    body: OfflinePackageRequest,
    current_user: User = Depends(get_current_institutional_user),
) -> JSONResponse:
    user_clearance = ClassificationLevel.from_any(current_user.clearance_level)
    requested_level = ClassificationLevel.from_any(body.classification)
    if not can_user_access(user_clearance, requested_level):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient clearance for requested classification",
        )

    package = await prepare_offline_package(body.country_iso, body.classification)
    return JSONResponse(content=package)


@router.post("/field-reports")
async def submit_field_reports(
    body: FieldReportSubmission,
    current_user: User = Depends(get_current_active_user),
) -> JSONResponse:
    if not validate_device(body.device_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Device {body.device_id} is not authorized",
        )

    results = await sync_field_reports(body.device_id, body.reports)
    return JSONResponse(content={"device_id": body.device_id, "results": results})


__all__ = ["router"]
