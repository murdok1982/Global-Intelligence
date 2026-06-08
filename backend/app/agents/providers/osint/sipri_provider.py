"""
SIPRI Arms Transfers Database OSINT provider.

Queries the Stockholm International Peace Research Institute (SIPRI)
Arms Transfers webservice for military equipment deliveries. SIPRI
is the gold-standard source for global arms-transfer data — every
signal is emitted with admiralty reliability ``A`` and category
``defense``.

API reference
-------------
Endpoint: ``https://armstransfer.sipri.org/webservice/v2/search``
Parameters: ``recipient_country`` (ISO 3-letter), ``supplier_country``,
``year_from``, ``year_to``, ``limit``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.core.config import settings

from .base import (
    OSINTProvider,
    OSINTSignal,
    assert_public_url,
    canonical_url,
)
from .exceptions import SSRFBlockedError


logger = logging.getLogger(__name__)


_SIPRI_ENDPOINT = "https://armstransfer.sipri.org/webservice/v2/search"


class SIPRIProvider(OSINTProvider):
    """SIPRI Arms Transfers Database."""

    name = "sipri"
    default_reliability = "A"

    def __init__(
        self,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._client = http_client

    async def execute(
        self,
        country_iso: str,
        days_back: int = 7,
        limit: int = 25,
    ) -> list[OSINTSignal]:
        per_source = min(limit, settings.OSINT_MAX_PER_SOURCE)

        try:
            assert_public_url(_SIPRI_ENDPOINT)
        except SSRFBlockedError as exc:
            logger.warning("SIPRI SSRF blocked: %s", exc)
            return []

        current_year = datetime.now(timezone.utc).year
        year_from = max(current_year - (days_back // 365 + 1), 1950)
        year_to = current_year

        params: dict[str, str | int] = {
            "recipient_country": country_iso.upper(),
            "year_from": year_from,
            "year_to": year_to,
            "limit": per_source,
        }

        last_exc: Exception | None = None
        data: list[dict] | None = None

        for attempt in range(3):
            try:
                async with self._client_ctx() as client:
                    response = await client.get(
                        _SIPRI_ENDPOINT,
                        params=params,
                    )
                    response.raise_for_status()
                    payload = response.json()
                if isinstance(payload, list):
                    data = payload
                elif isinstance(payload, dict):
                    data = payload.get("results", payload.get("data", []))
                    if not isinstance(data, list):
                        data = []
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))

        if data is None:
            logger.info(
                "SIPRI fetch failed after retries: %s",
                last_exc.__class__.__name__ if last_exc else "?",
            )
            return []

        signals: list[OSINTSignal] = []
        country_token = country_iso.upper() or "GLOBAL"

        for entry in data:
            if not isinstance(entry, dict):
                continue

            title = self._extract_title(entry)
            url = self._extract_url(entry)
            summary = self._extract_summary(entry)
            published = self._extract_date(entry)

            if not title:
                continue

            if url:
                try:
                    assert_public_url(url)
                except SSRFBlockedError:
                    url = ""
                else:
                    url = canonical_url(url)

            signals.append(
                OSINTSignal(
                    country=country_token,
                    category="defense",
                    title=title[:500],
                    url=url or _SIPRI_ENDPOINT,
                    summary=summary[:1000],
                    source_name="SIPRI Arms Transfers",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.9,
                    raw_metadata={
                        "sipri_entry": entry,
                        "provider": "sipri",
                    },
                )
            )
            if len(signals) >= per_source:
                break

        return signals

    def _client_ctx(self):  # noqa: ANN202
        if self._client is not None:
            injected = self._client

            class _Passthrough:
                async def __aenter__(self_inner) -> httpx.AsyncClient:  # noqa: N805
                    return injected

                async def __aexit__(self_inner, exc_type, exc, tb) -> None:  # noqa: N805
                    return None

            return _Passthrough()
        return httpx.AsyncClient(
            timeout=settings.OSINT_HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": "GlobalIntelligenceOSINT/1.0 (+state-grade)"},
        )

    @staticmethod
    def _extract_title(entry: dict) -> str:
        for key in ("title", "weapon", "equipment", "category", "description"):
            val = entry.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        supplier = entry.get("supplier") or entry.get("exporter") or ""
        recipient = entry.get("recipient") or entry.get("importer") or ""
        year = entry.get("year") or entry.get("order_year") or ""
        if supplier or recipient:
            return f"Arms transfer: {supplier} → {recipient} ({year})".strip()
        return ""

    @staticmethod
    def _extract_url(entry: dict) -> str:
        for key in ("url", "link", "source_url", "permalink"):
            val = entry.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    @staticmethod
    def _extract_summary(entry: dict) -> str:
        parts: list[str] = []
        for key in ("summary", "description", "notes", "details"):
            val = entry.get(key)
            if val and isinstance(val, str) and val.strip():
                parts.append(val.strip())
        supplier = entry.get("supplier") or entry.get("exporter") or ""
        recipient = entry.get("recipient") or entry.get("importer") or ""
        weapon = entry.get("weapon") or entry.get("equipment") or ""
        year = entry.get("year") or entry.get("order_year") or ""
        value = entry.get("value") or entry.get("amount") or ""
        if not parts:
            if supplier or recipient:
                parts.append(
                    f"Supplier: {supplier} | Recipient: {recipient} | "
                    f"Equipment: {weapon} | Year: {year} | Value: {value}"
                )
        return " — ".join(parts) if parts else ""

    @staticmethod
    def _extract_date(entry: dict) -> datetime:
        for key in ("year", "order_year", "delivery_year"):
            val = entry.get(key)
            if val:
                try:
                    year = int(val)
                    return datetime(year, 1, 1, tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue
        for key in ("date", "published", "timestamp"):
            val = entry.get(key)
            if val and isinstance(val, str):
                try:
                    dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except ValueError:
                    continue
        return datetime.now(timezone.utc)


__all__ = ["SIPRIProvider"]
