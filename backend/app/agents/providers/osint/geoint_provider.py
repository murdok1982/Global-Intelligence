"""
Geospatial intelligence (GEOINT) provider.

Aggregates geospatial event data from the USGS earthquake feed,
NASA EONET natural events, and Copernicus Sentinel-2 imagery metadata.

USGS and NASA data is treated as Admiralty reliability ``A`` (official
government sources). Copernicus metadata defaults to ``B``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

from .base import (
    OSINTProvider,
    OSINTSignal,
    assert_public_url,
    canonical_url,
    classify_category,
)
from .exceptions import SSRFBlockedError


logger = logging.getLogger(__name__)

_USGS_URL = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query"
    "?format=geojson&orderby=time&limit={limit}"
)
_NASA_EONET_URL = "https://eonet.gsfc.nasa.gov/api/v3/events?limit={limit}&days={days}"
_COPERNICUS_SEARCH_URL = (
    "https://catalogue.dataspace.copernicus.eu/odata/v1/Products"
    "?$filter=Collection/Name eq 'SENTINEL-2' and ContentDate/Start gt {start_date}"
    "&$orderby=ContentDate/Start desc&$top={limit}"
)

_EONET_CATEGORY_MAP: dict[str, str] = {
    "Wildfires": "security",
    "Volcanoes": "security",
    "Severe Storms": "security",
    "Floods": "security",
    "Earthquakes": "security",
    "Drought": "economic",
    "Landslides": "security",
    "Icebergs": "other",
    "Manmade": "security",
    "Water Color": "other",
}


class GEOINTProvider(OSINTProvider):
    """Geospatial intelligence from USGS, NASA EONET, and Copernicus."""

    name = "geoint"
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
        signals: list[OSINTSignal] = []

        usgs_signals = await self._fetch_usgs_earthquakes(country, limit)
        signals.extend(usgs_signals)

        eonet_signals = await self._fetch_nasa_eonet(country, days_back, limit)
        signals.extend(eonet_signals)

        copernicus_signals = await self._fetch_copernicus(country, days_back, limit)
        signals.extend(copernicus_signals)

        return signals[: settings.OSINT_MAX_PER_SOURCE]

    async def _fetch_usgs_earthquakes(
        self, country: str, limit: int
    ) -> list[OSINTSignal]:
        url = _USGS_URL.format(limit=min(limit, settings.OSINT_MAX_PER_SOURCE))

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("USGS URL blocked: %s", exc)
            return []

        body: dict[str, Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    body = resp.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("USGS fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        features = body.get("features", [])
        if not isinstance(features, list):
            return []

        signals: list[OSINTSignal] = []
        for feature in features:
            if not isinstance(feature, dict):
                continue

            props = feature.get("properties", {})
            geometry = feature.get("geometry", {})
            if not isinstance(props, dict):
                continue

            title = str(props.get("title", "") or props.get("place", "") or "")
            if not title:
                continue

            mag = props.get("mag")
            url_val = str(props.get("url", "") or "")
            if not url_val:
                continue

            try:
                assert_public_url(url_val)
            except SSRFBlockedError:
                continue

            time_ms = props.get("time")
            if isinstance(time_ms, (int, float)):
                published = datetime.fromtimestamp(
                    time_ms / 1000, tz=timezone.utc
                )
            else:
                published = datetime.now(timezone.utc)

            coords = geometry.get("coordinates", []) if isinstance(geometry, dict) else []
            lat = coords[1] if len(coords) > 1 else None
            lon = coords[0] if len(coords) > 0 else None
            depth = coords[2] if len(coords) > 2 else None

            place = str(props.get("place", "") or "")
            alert = str(props.get("alert", "") or "")
            tsunami = props.get("tsunami")
            felt = props.get("felt")
            sig = props.get("sig")

            summary_parts = [f"Magnitude: {mag}"]
            if place:
                summary_parts.append(f"Location: {place}")
            if depth is not None:
                summary_parts.append(f"Depth: {depth} km")
            if alert:
                summary_parts.append(f"Alert: {alert}")
            if tsunami:
                summary_parts.append("Tsunami warning")

            full_title = f"Earthquake M{mag}: {title}" if mag else title

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=full_title[:500],
                    url=canonical_url(url_val),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name="USGS Earthquake Hazards",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.92,
                    raw_metadata={
                        "magnitude": mag,
                        "place": place,
                        "latitude": lat,
                        "longitude": lon,
                        "depth": depth,
                        "alert": alert,
                        "tsunami": tsunami,
                        "felt": felt,
                        "significance": sig,
                    },
                )
            )
        return signals

    async def _fetch_nasa_eonet(
        self, country: str, days_back: int, limit: int
    ) -> list[OSINTSignal]:
        url = _NASA_EONET_URL.format(
            limit=min(limit, settings.OSINT_MAX_PER_SOURCE),
            days=days_back,
        )

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("NASA EONET URL blocked: %s", exc)
            return []

        body: dict[str, Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    body = resp.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("NASA EONET fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        events = body.get("events", [])
        if not isinstance(events, list):
            return []

        signals: list[OSINTSignal] = []
        for event in events:
            if not isinstance(event, dict):
                continue

            event_title = str(event.get("title", "") or "")
            event_id = str(event.get("id", "") or "")
            if not event_title:
                continue

            categories = event.get("categories", [])
            category_name = ""
            if isinstance(categories, list) and categories:
                first_cat = categories[0]
                if isinstance(first_cat, dict):
                    category_name = str(first_cat.get("title", "") or "")

            category = _EONET_CATEGORY_MAP.get(category_name, "security")

            link_list = event.get("sources", [])
            source_url = ""
            if isinstance(link_list, list) and link_list:
                first_source = link_list[0]
                if isinstance(first_source, dict):
                    urls = first_source.get("url", "")
                    if isinstance(urls, str) and urls:
                        source_url = urls

            if not source_url:
                source_url = f"https://eonet.gsfc.nasa.gov/api/v3/events/{event_id}"

            try:
                assert_public_url(source_url)
            except SSRFBlockedError:
                continue

            geometries = event.get("geometry", [])
            published = datetime.now(timezone.utc)
            coordinates: list[float] = []
            if isinstance(geometries, list) and geometries:
                latest_geom = geometries[-1]
                if isinstance(latest_geom, dict):
                    date_str = str(latest_geom.get("date", "") or "")
                    try:
                        published = datetime.fromisoformat(
                            date_str.replace("Z", "+00:00")
                        )
                    except (ValueError, TypeError):
                        pass
                    coords = latest_geom.get("coordinates", [])
                    if isinstance(coords, list) and len(coords) >= 2:
                        coordinates = coords[:2]

            closed = event.get("closed")
            description = str(event.get("description", "") or "")

            signals.append(
                OSINTSignal(
                    country=country,
                    category=category,
                    title=event_title[:500],
                    url=canonical_url(source_url),
                    summary=description[:1000] if description else f"NASA EONET event: {category_name}",
                    source_name="NASA EONET",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.88,
                    raw_metadata={
                        "event_id": event_id,
                        "category": category_name,
                        "closed": closed,
                        "latitude": coordinates[1] if len(coordinates) >= 2 else None,
                        "longitude": coordinates[0] if len(coordinates) >= 1 else None,
                    },
                )
            )
        return signals

    async def _fetch_copernicus(
        self, country: str, days_back: int, limit: int
    ) -> list[OSINTSignal]:
        if not settings.COPERNICUS_USERNAME or not settings.COPERNICUS_PASSWORD:
            return []

        now = datetime.now(timezone.utc)
        start_date = f"{now.year}-{now.month:02d}-{max(1, now.day - days_back):02d}T00:00:00.000Z"
        url = _COPERNICUS_SEARCH_URL.format(
            start_date=start_date,
            limit=min(limit, settings.OSINT_MAX_PER_SOURCE),
        )

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("Copernicus URL blocked: %s", exc)
            return []

        body: dict[str, Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(
                        url,
                        auth=(settings.COPERNICUS_USERNAME, settings.COPERNICUS_PASSWORD),
                    )
                    resp.raise_for_status()
                    body = resp.json()
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("Copernicus fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        values = body.get("value", [])
        if not isinstance(values, list):
            return []

        signals: list[OSINTSignal] = []
        for product in values:
            if not isinstance(product, dict):
                continue

            product_id = str(product.get("Id", "") or "")
            product_name = str(product.get("Name", "") or "")
            if not product_name:
                continue

            content_date = product.get("ContentDate", {})
            start_str = ""
            if isinstance(content_date, dict):
                start_str = str(content_date.get("Start", "") or "")

            try:
                published = datetime.fromisoformat(
                    start_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                published = datetime.now(timezone.utc)

            footprint = str(product.get("Footprint", "") or "")
            online = product.get("Online")
            cloud_cover = None
            attrs = product.get("Attributes", [])
            if isinstance(attrs, list):
                for attr in attrs:
                    if isinstance(attr, dict) and attr.get("Name") == "cloudCover":
                        cloud_cover = attr.get("Value")
                        break

            title = f"Sentinel-2: {product_name}"
            source_url = f"https://browser.dataspace.copernicus.eu/?product={product_id}"

            summary_parts = [f"Product: {product_name}"]
            if cloud_cover is not None:
                summary_parts.append(f"Cloud cover: {cloud_cover}%")
            summary_parts.append(f"Acquired: {start_str}")

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name="Copernicus Open Access Hub",
                    published_at=published,
                    language="en",
                    admiralty_reliability="B",
                    admiralty_credibility=2,
                    confidence_score=0.70,
                    raw_metadata={
                        "product_id": product_id,
                        "product_name": product_name,
                        "online": online,
                        "cloud_cover": cloud_cover,
                        "footprint": footprint[:500] if footprint else "",
                    },
                )
            )
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


__all__ = ["GEOINTProvider"]
