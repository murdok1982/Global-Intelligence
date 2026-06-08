from __future__ import annotations

import hashlib
import json
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from cryptography.fernet import Fernet

from app.core.classification import ClassificationLevel
from app.core.config import settings

logger = logging.getLogger(__name__)

_DEVICE_REGISTRY: dict[str, dict[str, Any]] = {}
_REVOKED_DEVICES: set[str] = set()

_CONFLICT_SERVER_WINS_CLASSIFICATIONS = {
    ClassificationLevel.RESTRICTED,
    ClassificationLevel.CONFIDENTIAL,
    ClassificationLevel.SECRET,
}


def _derive_encryption_key() -> bytes:
    raw = settings.SECRET_KEY or "fallback-dev-key-not-for-production"
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    import base64
    return base64.urlsafe_b64encode(digest)


def _get_fernet() -> Fernet:
    key = _derive_encryption_key()
    return Fernet(key)


def _encrypt_payload(data: dict[str, Any]) -> str:
    f = _get_fernet()
    raw = json.dumps(data, default=str, ensure_ascii=False).encode("utf-8")
    return f.encrypt(raw).decode("ascii")


def _decrypt_payload(token: str) -> dict[str, Any]:
    f = _get_fernet()
    raw = f.decrypt(token.encode("ascii"))
    return json.loads(raw)


def _resolve_classification(classification: str | int) -> int:
    if isinstance(classification, int):
        return classification
    return int(ClassificationLevel.from_any(classification))


def _fetch_country_reports(country_iso: str, classification: int) -> list[dict[str, Any]]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.reports import DailyReport
    from app.models.geography import Country
    from sqlalchemy.future import select

    async def _load() -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            country_result = await session.execute(
                select(Country).where(Country.iso_code == country_iso.upper())
            )
            country = country_result.scalars().first()
            if not country:
                return []

            result = await session.execute(
                select(DailyReport)
                .where(
                    DailyReport.country_id == country.id,
                    DailyReport.published.is_(True),
                    DailyReport.classification <= classification,
                )
                .order_by(DailyReport.report_date.desc())
                .limit(100)
            )
            reports = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "country_id": str(r.country_id),
                    "report_date": r.report_date.isoformat() if r.report_date else None,
                    "executive_summary": r.executive_summary or "",
                    "content_json": r.content_json or "{}",
                    "classification": int(r.classification or 0),
                    "tlp": r.tlp,
                    "signature": r.signature,
                    "signature_fingerprint": r.signature_fingerprint,
                    "signed_at": r.signed_at.isoformat() if r.signed_at else None,
                }
                for r in reports
            ]

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except RuntimeError:
        return asyncio.run(_load())


def _fetch_delta_reports(
    country_iso: str,
    classification: int,
    since: datetime,
) -> list[dict[str, Any]]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.reports import DailyReport
    from app.models.geography import Country
    from sqlalchemy.future import select

    async def _load() -> list[dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            country_result = await session.execute(
                select(Country).where(Country.iso_code == country_iso.upper())
            )
            country = country_result.scalars().first()
            if not country:
                return []

            result = await session.execute(
                select(DailyReport)
                .where(
                    DailyReport.country_id == country.id,
                    DailyReport.published.is_(True),
                    DailyReport.classification <= classification,
                    DailyReport.report_date >= since,
                )
                .order_by(DailyReport.report_date.asc())
            )
            reports = result.scalars().all()
            return [
                {
                    "id": str(r.id),
                    "country_id": str(r.country_id),
                    "report_date": r.report_date.isoformat() if r.report_date else None,
                    "executive_summary": r.executive_summary or "",
                    "content_json": r.content_json or "{}",
                    "classification": int(r.classification or 0),
                    "tlp": r.tlp,
                    "signature": r.signature,
                    "signature_fingerprint": r.signature_fingerprint,
                    "signed_at": r.signed_at.isoformat() if r.signed_at else None,
                }
                for r in reports
            ]

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _load()).result()
    except RuntimeError:
        return asyncio.run(_load())


def _store_field_reports(device_id: str, reports: list[dict[str, Any]]) -> list[dict[str, Any]]:
    import asyncio
    import concurrent.futures
    from app.db.session import AsyncSessionLocal
    from app.models.reports import DailyReport
    from sqlalchemy.future import select

    async def _persist() -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        async with AsyncSessionLocal() as session:
            for report_data in reports:
                existing_id = report_data.get("id")
                if existing_id:
                    try:
                        result = await session.execute(
                            select(DailyReport).where(
                                DailyReport.id == uuid.UUID(existing_id)
                            )
                        )
                        existing = result.scalars().first()
                        if existing:
                            results.append({
                                "id": existing_id,
                                "action": "conflict",
                                "resolution": "server_wins",
                                "server_version": {
                                    "executive_summary": existing.executive_summary,
                                    "classification": int(existing.classification or 0),
                                },
                            })
                            continue
                    except (ValueError, Exception):
                        pass

                new_report = DailyReport(
                    id=uuid.UUID(existing_id) if existing_id else uuid.uuid4(),
                    executive_summary=report_data.get("executive_summary", ""),
                    content_json=json.dumps(report_data.get("content_json", {})),
                    classification=int(report_data.get("classification", 0)),
                    tlp=report_data.get("tlp", "TLP:CLEAR"),
                    published=False,
                )
                session.add(new_report)
                results.append({
                    "id": str(new_report.id),
                    "action": "created",
                    "resolution": "accepted",
                })

            await session.commit()
        return results

    try:
        asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor() as pool:
            return pool.submit(asyncio.run, _persist()).result()
    except RuntimeError:
        return asyncio.run(_persist())


def validate_device(device_id: str) -> bool:
    if device_id in _REVOKED_DEVICES:
        logger.warning("Device %s is revoked", device_id)
        return False
    if device_id in _DEVICE_REGISTRY:
        device = _DEVICE_REGISTRY[device_id]
        if device.get("expires_at"):
            expires = datetime.fromisoformat(device["expires_at"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) > expires:
                logger.warning("Device %s registration expired", device_id)
                return False
        return True
    register_device(device_id)
    return True


def register_device(
    device_id: str,
    ttl_hours: int = 720,
    metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    registration = {
        "device_id": device_id,
        "registered_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
        "api_token": secrets.token_urlsafe(32),
        "metadata": metadata or {},
    }
    _DEVICE_REGISTRY[device_id] = registration
    _REVOKED_DEVICES.discard(device_id)
    logger.info("Device %s registered, expires %s", device_id, expires_at.isoformat())
    return registration


def revoke_device(device_id: str) -> bool:
    if device_id in _DEVICE_REGISTRY:
        del _DEVICE_REGISTRY[device_id]
    _REVOKED_DEVICES.add(device_id)
    logger.info("Device %s revoked", device_id)
    return True


async def prepare_offline_package(country_iso: str, classification: str) -> dict:
    cls_level = _resolve_classification(classification)
    reports = _fetch_country_reports(country_iso.upper(), cls_level)

    package_metadata = {
        "package_id": str(uuid.uuid4()),
        "country_iso": country_iso.upper(),
        "classification": classification,
        "classification_level": cls_level,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "report_count": len(reports),
        "platform": "Global Intelligence Platform",
    }

    package_data = {
        "metadata": package_metadata,
        "reports": reports,
    }

    encrypted_payload = _encrypt_payload(package_data)

    integrity_hash = hashlib.sha256(
        json.dumps(package_data, default=str).encode("utf-8")
    ).hexdigest()

    return {
        "metadata": package_metadata,
        "encrypted_data": encrypted_payload,
        "integrity_hash": integrity_hash,
        "encryption_algorithm": "Fernet (AES-128-CBC)",
        "instructions": {
            "decrypt": "Use platform API with valid device token to decrypt",
            "verify": f"SHA-256 hash: {integrity_hash}",
        },
    }


async def sync_field_reports(device_id: str, reports: list[dict]) -> list[dict]:
    if not validate_device(device_id):
        return [{"error": f"Device {device_id} is not authorized"}]

    validated_reports: list[dict[str, Any]] = []
    for report in reports:
        if not isinstance(report, dict):
            continue
        if not report.get("executive_summary"):
            continue
        validated_reports.append(report)

    if not validated_reports:
        return [{"error": "No valid reports in submission"}]

    results = _store_field_reports(device_id, validated_reports)

    logger.info(
        "Synced %d field reports from device %s (%d processed)",
        len(validated_reports),
        device_id,
        len(results),
    )

    return results


async def compute_delta(last_sync: datetime, country_iso: str) -> dict:
    if last_sync.tzinfo is None:
        last_sync = last_sync.replace(tzinfo=timezone.utc)

    cls_level = int(ClassificationLevel.RESTRICTED)
    new_reports = _fetch_delta_reports(country_iso.upper(), cls_level, last_sync)

    return {
        "country_iso": country_iso.upper(),
        "since": last_sync.isoformat(),
        "computed_at": datetime.now(timezone.utc).isoformat(),
        "new_reports": new_reports,
        "report_count": len(new_reports),
        "has_changes": len(new_reports) > 0,
    }


__all__ = [
    "prepare_offline_package",
    "sync_field_reports",
    "compute_delta",
    "validate_device",
    "register_device",
    "revoke_device",
]
