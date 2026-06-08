"""
Armed Conflict Location & Event Data (ACLED) provider.

Queries the ACLED API for structured conflict event data including
battles, violence against civilians, riots, protests, and strategic
developments.  ACLED is the canonical source for subnational conflict
data worldwide.

API reference
-------------
Endpoint: ``https://api.acleddata.com/acled/read``
Auth: ``key`` + ``email`` query parameters (free registration).

When no API credentials are configured the provider falls back to
the public ACLED CSV download endpoint.

All signals are emitted with admiralty reliability ``A`` and category
``security``.
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

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

_ACLED_API_URL = "https://api.acleddata.com/acled/read"
_ACLED_CSV_URL = "https://acleddata.com/wp-content/uploads/2024/01/1997-2024-Aug2324.csv.zip"

_EVENT_TYPE_CONFIDENCE: dict[str, float] = {
    "Battles": 0.95,
    "Violence against civilians": 0.93,
    "Explosions/Remote violence": 0.92,
    "Protests": 0.88,
    "Riots": 0.87,
    "Strategic developments": 0.85,
}


class ACLEDProvider(OSINTProvider):
    """Armed Conflict Location & Event Data provider."""

    name = "acled"
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
        country = country_iso.upper().strip() or "GLOBAL"
        api_key = getattr(settings, "ACLED_API_KEY", "")
        api_email = getattr(settings, "ACLED_EMAIL", "")

        if api_key and api_email:
            signals = await self._fetch_api(country, api_key, api_email, days_back, limit)
        else:
            signals = await self._fetch_csv_fallback(country, days_back, limit)

        return signals[: settings.OSINT_MAX_PER_SOURCE]

    async def _fetch_api(
        self,
        country: str,
        api_key: str,
        api_email: str,
        days_back: int,
        limit: int,
    ) -> list[OSINTSignal]:
        now = datetime.now(timezone.utc)
        date_from = (now - timedelta(days=days_back)).strftime("%Y-%m-%d")
        date_to = now.strftime("%Y-%m-%d")

        params: dict[str, str | int] = {
            "key": api_key,
            "email": api_email,
            "terms": f"event_date=>|{date_from}&event_date=<|{date_to}",
            "limit": min(limit, settings.OSINT_MAX_PER_SOURCE),
        }
        if country != "GLOBAL":
            params["country"] = country

        url = _ACLED_API_URL

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("ACLED API URL blocked: %s", exc)
            return []

        body: dict[str, Any] | list[Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url, params=params)
                    resp.raise_for_status()
                    body = resp.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("ACLED API fetch failed: %s", exc)
                        return []

        if body is None:
            return []

        events: list[Any] = []
        if isinstance(body, list):
            events = body
        elif isinstance(body, dict):
            events = body.get("data", body.get("events", []))
            if not isinstance(events, list):
                return []

        return self._parse_events(events, country)

    async def _fetch_csv_fallback(
        self,
        country: str,
        days_back: int,
        limit: int,
    ) -> list[OSINTSignal]:
        url = _ACLED_CSV_URL

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("ACLED CSV URL blocked: %s", exc)
            return []

        csv_text: str | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url, follow_redirects=True)
                    resp.raise_for_status()
                    csv_text = resp.text
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.5 * (attempt + 1))
                    else:
                        logger.info("ACLED CSV fetch failed: %s", exc)
                        return []

        if not csv_text:
            return []

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=days_back)
        events: list[dict[str, str]] = []

        reader = csv.DictReader(io.StringIO(csv_text))
        for row in reader:
            if not isinstance(row, dict):
                continue

            row_country = str(row.get("COUNTRY", "") or "").upper()
            if country != "GLOBAL" and row_country != country:
                continue

            date_str = str(row.get("EVENT_DATE", "") or "")
            try:
                event_date = datetime.strptime(date_str, "%d %B %Y").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                continue

            if event_date < cutoff:
                continue

            events.append(row)
            if len(events) >= limit:
                break

        return self._parse_csv_events(events, country)

    def _parse_events(
        self, events: list[Any], country: str
    ) -> list[OSINTSignal]:
        signals: list[OSINTSignal] = []

        for event in events:
            if not isinstance(event, dict):
                continue

            event_id = str(
                event.get("event_id_cnty", "")
                or event.get("EVENT_ID_CNTY", "")
                or event.get("data_id", "")
                or ""
            )
            if not event_id:
                continue

            event_date_str = str(
                event.get("event_date", "") or event.get("EVENT_DATE", "") or ""
            )
            try:
                published = datetime.fromisoformat(
                    event_date_str.replace("Z", "+00:00")
                )
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                try:
                    published = datetime.strptime(
                        event_date_str, "%d %B %Y"
                    ).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    published = datetime.now(timezone.utc)

            event_type = str(
                event.get("event_type", "") or event.get("EVENT_TYPE", "") or "Unknown"
            )
            sub_event_type = str(
                event.get("sub_event_type", "")
                or event.get("SUB_EVENT_TYPE", "")
                or ""
            )
            actor1 = str(
                event.get("actor1", "") or event.get("ACTOR1", "") or ""
            )
            actor2 = str(
                event.get("actor2", "") or event.get("ACTOR2", "") or ""
            )
            country_name = str(
                event.get("country", "") or event.get("COUNTRY", "") or country
            )
            admin1 = str(
                event.get("admin1", "") or event.get("ADMIN1", "") or ""
            )
            admin2 = str(
                event.get("admin2", "") or event.get("ADMIN2", "") or ""
            )
            location = str(
                event.get("location", "") or event.get("LOCATION", "") or ""
            )
            notes = str(
                event.get("notes", "") or event.get("NOTES", "") or ""
            )
            fatalities = event.get("fatalities") or event.get("FATALITIES") or 0
            latitude = event.get("latitude") or event.get("LATITUDE")
            longitude = event.get("longitude") or event.get("LONGITUDE")
            iso3 = str(
                event.get("iso3", "") or event.get("ISO3", "") or ""
            )
            source = str(
                event.get("source", "") or event.get("SOURCE", "") or "ACLED"
            )

            title_parts = [event_type]
            if sub_event_type:
                title_parts.append(f"({sub_event_type})")
            if location:
                title_parts.append(f"— {location}")
            if admin1:
                title_parts.append(f", {admin1}")
            title = " ".join(title_parts)

            source_url = f"https://acleddata.com/dashboard/#/dashboard/event/{event_id}" if event_id else "https://acleddata.com"

            summary_parts = [
                f"Type: {event_type}",
                f"Actor: {actor1}",
            ]
            if actor2:
                summary_parts.append(f"Target: {actor2}")
            if location:
                summary_parts.append(f"Location: {location}")
            if admin1:
                summary_parts.append(f"Region: {admin1}")
            if fatalities:
                summary_parts.append(f"Fatalities: {fatalities}")
            if notes:
                summary_parts.append(f"Notes: {notes[:200]}")

            confidence = _EVENT_TYPE_CONFIDENCE.get(event_type, 0.85)

            try:
                if isinstance(latitude, str):
                    latitude = float(latitude)
                if isinstance(longitude, str):
                    longitude = float(longitude)
            except (ValueError, TypeError):
                latitude = None
                longitude = None

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name=f"ACLED ({source})" if source != "ACLED" else "ACLED",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=confidence,
                    raw_metadata={
                        "event_id": event_id,
                        "event_type": event_type,
                        "sub_event_type": sub_event_type,
                        "actor1": actor1,
                        "actor2": actor2,
                        "country": country_name,
                        "iso3": iso3,
                        "admin1": admin1,
                        "admin2": admin2,
                        "location": location,
                        "fatalities": fatalities,
                        "latitude": latitude,
                        "longitude": longitude,
                        "notes": notes[:500] if notes else "",
                    },
                )
            )
        return signals

    def _parse_csv_events(
        self, events: list[dict[str, str]], country: str
    ) -> list[OSINTSignal]:
        normalized: list[dict[str, Any]] = []
        for row in events:
            normalized.append({
                "event_id_cnty": row.get("EVENT_ID_CNTY", ""),
                "event_date": row.get("EVENT_DATE", ""),
                "event_type": row.get("EVENT_TYPE", ""),
                "sub_event_type": row.get("SUB_EVENT_TYPE", ""),
                "actor1": row.get("ACTOR1", ""),
                "actor2": row.get("ACTOR2", ""),
                "country": row.get("COUNTRY", ""),
                "iso3": row.get("ISO3", ""),
                "admin1": row.get("ADMIN1", ""),
                "admin2": row.get("ADMIN2", ""),
                "location": row.get("LOCATION", ""),
                "notes": row.get("NOTES", ""),
                "fatalities": row.get("FATALITIES", "0"),
                "latitude": row.get("LATITUDE", ""),
                "longitude": row.get("LONGITUDE", ""),
                "source": row.get("SOURCE", "ACLED"),
            })
        return self._parse_events(normalized, country)

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


__all__ = ["ACLEDProvider"]
