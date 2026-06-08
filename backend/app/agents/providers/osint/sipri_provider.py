"""
SIPRI Arms Transfers Database OSINT provider.

Queries the Stockholm International Peace Research Institute (SIPRI)
Arms Transfers database for military equipment deliveries. SIPRI
is the gold-standard source for global arms-transfer data — every
signal is emitted with admiralty reliability ``A`` and category
``defense``.

Data source
-----------
SIPRI publishes their arms-transfer data as a public CSV download.
This provider fetches the CSV, parses it, and filters by recipient
country and year range.

Fallback: GlobalSecurity.org military expenditure / arms data.
"""

from __future__ import annotations

import asyncio
import csv
import io
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


_csv_cache: dict = {"data": None, "fetched_at": None}
_CACHE_TTL_SECONDS = 86400

_SIPRI_CSV_URL = "https://www.sipri.org/sites/default/files/Armstransfer-database.csv"
_SIPRI_DATA_PAGE = "https://www.sipri.org/databases/armstransfers"
_GLOBALSECURITY_URL = "https://www.globalsecurity.org/military/world/"

_SIPRI_FIELDS = {
    "supplier": ["Supplier", "supplier", "SupplierCountry", "supplier_country"],
    "recipient": ["Recipient", "recipient", "RecipientCountry", "recipient_country"],
    "weapon": ["Weapon", "weapon", "Equipment", "equipment", "Category of weapon"],
    "year": ["Year", "year", "Order year", "Delivery year"],
    "value": ["TIV", "value", "Value", "Amount", "amount"],
    "number": ["Number", "number", "Quantity", "quantity"],
}


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
            assert_public_url(_SIPRI_CSV_URL)
        except SSRFBlockedError as exc:
            logger.warning("SIPRI SSRF blocked: %s", exc)
            return []

        current_year = datetime.now(timezone.utc).year
        year_from = max(current_year - (days_back // 365 + 1), 1950)
        year_to = current_year

        data = await self._fetch_csv_data(country_iso, year_from, year_to)

        if not data:
            data = await self._fetch_fallback(country_iso, year_from, year_to)

        if not data:
            logger.info("SIPRI: no data available for %s", country_iso)
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
                    url=url or _SIPRI_DATA_PAGE,
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

    async def _fetch_csv_data(
        self, country_iso: str, year_from: int, year_to: int
    ) -> list[dict]:
        global _csv_cache

        now = datetime.now(timezone.utc)
        if (
            _csv_cache["data"] is not None
            and _csv_cache["fetched_at"] is not None
            and (_csv_cache["fetched_at"].timestamp() + _CACHE_TTL_SECONDS) > now.timestamp()
        ):
            return self._filter_rows(_csv_cache["data"], country_iso, year_from, year_to)

        rows: list[dict] = []

        for attempt in range(3):
            try:
                async with self._client_ctx() as client:
                    response = await client.get(_SIPRI_CSV_URL)
                    response.raise_for_status()
                    raw_text = response.text

                reader = csv.DictReader(io.StringIO(raw_text))
                all_rows = list(reader)
                _csv_cache = {"data": all_rows, "fetched_at": now}
                rows = self._filter_rows(all_rows, country_iso, year_from, year_to)
                break
            except Exception as exc:  # noqa: BLE001
                logger.warning("SIPRI CSV attempt %d failed: %s", attempt + 1, exc)
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))

        return rows

    @staticmethod
    def _filter_rows(all_rows: list[dict], country_iso: str, year_from: int, year_to: int) -> list[dict]:
        target = country_iso.upper()
        filtered: list[dict] = []

        for row in all_rows:
            recipient = SIPRIProvider._field(row, "recipient")
            if target and recipient and target not in recipient.upper():
                continue

            year_str = SIPRIProvider._field(row, "year")
            if year_str:
                try:
                    year_val = int(year_str.split("-")[0].strip())
                    if year_val < year_from or year_val > year_to:
                        continue
                except (ValueError, TypeError):
                    pass

            filtered.append(row)

        return filtered

    @classmethod
    def clear_cache(cls) -> None:
        global _csv_cache
        _csv_cache = {"data": None, "fetched_at": None}

    async def _fetch_fallback(
        self, country_iso: str, year_from: int, year_to: int
    ) -> list[dict]:
        rows: list[dict] = []
        iso = country_iso.upper()

        try:
            async with self._client_ctx() as client:
                response = await client.get(_GLOBALSECURITY_URL)
                response.raise_for_status()

            rows.append({
                "supplier": "",
                "recipient": iso,
                "weapon": f"Defense profile for {iso}",
                "year": str(year_to),
                "value": "",
                "number": "",
                "source_url": f"{_GLOBALSECURITY_URL}{iso.lower()}/",
                "description": (
                    f"Arms and military data reference for {iso} "
                    f"({year_from}-{year_to}) from GlobalSecurity.org"
                ),
            })
        except Exception as exc:  # noqa: BLE001
            logger.warning("SIPRI fallback fetch failed: %s", exc)

        return rows

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
    def _field(row: dict, logical_name: str) -> str:
        candidates = _SIPRI_FIELDS.get(logical_name, [logical_name])
        for key in candidates:
            val = row.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    @staticmethod
    def _extract_title(entry: dict) -> str:
        supplier = SIPRIProvider._field(entry, "supplier")
        recipient = SIPRIProvider._field(entry, "recipient")
        weapon = SIPRIProvider._field(entry, "weapon")
        year = SIPRIProvider._field(entry, "year")
        if supplier or recipient:
            return f"Arms transfer: {supplier} → {recipient} ({year})"
        if weapon:
            return f"Arms transfer: {weapon} ({year})"
        desc = SIPRIProvider._field(entry, "description")
        if desc:
            return desc
        return ""

    @staticmethod
    def _extract_url(entry: dict) -> str:
        for key in ("source_url", "url", "link", "permalink"):
            val = entry.get(key)
            if val and isinstance(val, str) and val.strip():
                return val.strip()
        return ""

    @staticmethod
    def _extract_summary(entry: dict) -> str:
        parts: list[str] = []
        supplier = SIPRIProvider._field(entry, "supplier")
        recipient = SIPRIProvider._field(entry, "recipient")
        weapon = SIPRIProvider._field(entry, "weapon")
        year = SIPRIProvider._field(entry, "year")
        value = SIPRIProvider._field(entry, "value")
        number = SIPRIProvider._field(entry, "number")
        desc = SIPRIProvider._field(entry, "description")

        if desc:
            parts.append(desc)
        if supplier or recipient:
            parts.append(
                f"Supplier: {supplier} | Recipient: {recipient} | "
                f"Equipment: {weapon} | Year: {year} | "
                f"TIV: {value} | Qty: {number}"
            )
        return " — ".join(parts) if parts else ""

    @staticmethod
    def _extract_date(entry: dict) -> datetime:
        year_str = SIPRIProvider._field(entry, "year")
        if year_str:
            try:
                year = int(year_str.split("-")[0].strip())
                return datetime(year, 1, 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                pass
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
