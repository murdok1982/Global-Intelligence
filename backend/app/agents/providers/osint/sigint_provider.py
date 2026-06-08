"""
Signals intelligence (SIGINT) provider.

Monitors electromagnetic signals in the public domain across two
domains: maritime (AIS — Automatic Identification System) and aerial
(ADS-B — Automatic Dependent Surveillance-Broadcast).

Data sources
------------
* **AISHub** — community-driven AIS receiver network.  Free JSON API,
  no key required.  Bounding-box query.
* **OpenSky Network** — open ADS-B / Mode-S receiver network.  Free
  REST API with bounding-box filter.  No key required for the
  ``/states/all`` endpoint (rate-limited to 4 s between requests for
  anonymous users).
* **MarineTraffic** — commercial AIS aggregator.  Only queried when
  ``MARINETRAFFIC_API_KEY`` is configured.

All signals are emitted with admiralty reliability ``A`` (direct
interception of cooperative transponder signals) and category
``security``.
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
)
from .exceptions import SSRFBlockedError


logger = logging.getLogger(__name__)

_AISHUB_URL = (
    "http://data.aishub.net/v1/testing/query"
    "?format=json&latmin={latmin}&latmax={latmax}&lonmin={lonmin}&lonmax={lonmax}"
)
_OPENSKY_URL = (
    "https://opensky-network.org/api/states/all"
    "?lamin={latmin}&lomin={lonmin}&lamax={latmax}&lomax={lonmax}"
)
_MARINETRAFFIC_URL = (
    "https://api.marinetraffic.com/api/ais/getvesselinfo"
    "?apikey={api_key}&timeout=15"
)

_COUNTRY_BBOX: dict[str, tuple[float, float, float, float]] = {
    "USA": (24.396308, -125.0, 49.384358, -66.93457),
    "US": (24.396308, -125.0, 49.384358, -66.93457),
    "GBR": (49.9, -8.17, 58.64, 1.75),
    "GB": (49.9, -8.17, 58.64, 1.75),
    "ESP": (36.0, -9.3, 43.79, 3.04),
    "ES": (36.0, -9.3, 43.79, 3.04),
    "FRA": (42.33, -5.14, 51.09, 8.23),
    "FR": (42.33, -5.14, 51.09, 8.23),
    "DEU": (47.27, 5.87, 55.06, 15.04),
    "DE": (47.27, 5.87, 55.06, 15.04),
    "ITA": (36.62, 6.63, 47.09, 18.52),
    "IT": (36.62, 6.63, 47.09, 18.52),
    "RUS": (41.19, 19.64, 81.86, 180.0),
    "RU": (41.19, 19.64, 81.86, 180.0),
    "CHN": (18.15, 73.62, 53.56, 134.77),
    "CN": (18.15, 73.62, 53.56, 134.77),
    "JPN": (24.25, 122.93, 45.52, 153.99),
    "JP": (24.25, 122.93, 45.52, 153.99),
    "BRA": (-33.75, -73.98, 5.27, -34.79),
    "BR": (-33.75, -73.98, 5.27, -34.79),
    "IND": (6.75, 68.18, 35.5, 97.4),
    "IN": (6.75, 68.18, 35.5, 97.4),
    "IRN": (25.06, 44.04, 39.78, 63.32),
    "IR": (25.06, 44.04, 39.78, 63.32),
    "PRK": (37.67, 124.27, 43.01, 130.7),
    "KP": (37.67, 124.27, 43.01, 130.7),
    "UKR": (44.39, 22.13, 52.38, 40.23),
    "UA": (44.39, 22.13, 52.38, 40.23),
    "TUR": (35.81, 25.66, 42.11, 44.83),
    "TR": (35.81, 25.66, 42.11, 44.83),
    "ISR": (29.5, 34.27, 33.27, 35.87),
    "IL": (29.5, 34.27, 33.27, 35.87),
    "EGY": (22.0, 24.7, 31.67, 36.87),
    "EG": (22.0, 24.7, 31.67, 36.87),
    "SAU": (16.37, 34.58, 32.18, 55.17),
    "SA": (16.37, 34.58, 32.18, 55.17),
    "AUS": (-43.65, 113.16, -10.07, 153.64),
    "AU": (-43.65, 113.16, -10.07, 153.64),
}

_GLOBAL_BBOX: tuple[float, float, float, float] = (-90.0, -180.0, 90.0, 180.0)

_SHIP_TYPE_MAP: dict[str, str] = {
    "0": "Reserved",
    "1": "Reserved",
    "2": "WIG",
    "3": "Fishing",
    "4": "Towing",
    "5": "Military",
    "6": "Sailing",
    "7": "Pleasure",
    "8": "Reserved",
    "9": "HSC",
    "30": "Fishing",
    "35": "Military",
    "36": "Sailing",
    "37": "Pleasure",
    "40": "HSC",
    "50": "Pilot",
    "51": "SAR",
    "52": "Tug",
    "53": "Port tender",
    "55": "Law enforcement",
    "60": "Passenger",
    "70": "Cargo",
    "80": "Tanker",
    "90": "Other",
}


class SIGINTProvider(OSINTProvider):
    """Signals intelligence from AIS, ADS-B, and MarineTraffic."""

    name = "sigint"
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
        bbox = _COUNTRY_BBOX.get(country, _GLOBAL_BBOX)
        signals: list[OSINTSignal] = []

        ais_signals = await self._fetch_aishub(country, bbox, limit)
        signals.extend(ais_signals)

        adsb_signals = await self._fetch_opensky(country, bbox, limit)
        signals.extend(adsb_signals)

        if getattr(settings, "MARINETRAFFIC_API_KEY", ""):
            mt_signals = await self._fetch_marinetraffic(country, limit)
            signals.extend(mt_signals)

        return signals[: settings.OSINT_MAX_PER_SOURCE]

    async def _fetch_aishub(
        self,
        country: str,
        bbox: tuple[float, float, float, float],
        limit: int,
    ) -> list[OSINTSignal]:
        latmin, lonmin, latmax, lonmax = bbox
        url = _AISHUB_URL.format(
            latmin=latmin, latmax=latmax, lonmin=lonmin, lonmax=lonmax
        )

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("AISHub URL blocked: %s", exc)
            return []

        body: list[Any] | dict[str, Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    parsed = resp.json()
                    if isinstance(parsed, list):
                        body = parsed
                    elif isinstance(parsed, dict):
                        body = parsed.get("data", parsed.get("results", []))
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("AISHub fetch failed: %s", exc)
                        return []

        if not isinstance(body, list):
            return []

        signals: list[OSINTSignal] = []
        for vessel in body[:limit]:
            if not isinstance(vessel, dict):
                continue

            mmsi = str(vessel.get("MMSI", "") or "")
            if not mmsi:
                continue

            vessel_name = str(vessel.get("NAME", "") or "Unknown").strip()
            flag = str(vessel.get("FLAG", "") or country).strip()
            ship_type_raw = str(vessel.get("SHIP_TYPE", "") or "")
            ship_type = _SHIP_TYPE_MAP.get(ship_type_raw, ship_type_raw or "Unknown")
            imo = str(vessel.get("IMO", "") or "")
            callsign = str(vessel.get("CALLSIGN", "") or "")

            lat = vessel.get("LATITUDE")
            lon = vessel.get("LONGITUDE")
            sog = vessel.get("SOG")
            heading = vessel.get("HEADING")
            course = vessel.get("COURSE")

            time_str = str(vessel.get("TIME", "") or "")
            try:
                published = datetime.strptime(
                    time_str, "%Y-%m-%d %H:%M:%S"
                ).replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published = datetime.now(timezone.utc)

            title = f"AIS: {vessel_name} (MMSI {mmsi})"
            source_url = f"https://www.vesselfinder.com/vessels?mmsi={mmsi}"

            summary_parts = [
                f"MMSI: {mmsi}",
                f"Name: {vessel_name}",
                f"Flag: {flag}",
                f"Type: {ship_type}",
            ]
            if lat is not None and lon is not None:
                summary_parts.append(f"Position: {lat}, {lon}")
            if sog is not None:
                summary_parts.append(f"Speed: {sog} kn")
            if course is not None:
                summary_parts.append(f"Course: {course}\u00b0")
            if heading is not None:
                summary_parts.append(f"Heading: {heading}\u00b0")

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name="AISHub",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.93,
                    raw_metadata={
                        "mmsi": mmsi,
                        "imo": imo,
                        "callsign": callsign,
                        "vessel_name": vessel_name,
                        "flag": flag,
                        "ship_type": ship_type,
                        "latitude": lat,
                        "longitude": lon,
                        "speed_knots": sog,
                        "heading": heading,
                        "course": course,
                        "signal_type": "ais",
                    },
                )
            )
        return signals

    async def _fetch_opensky(
        self,
        country: str,
        bbox: tuple[float, float, float, float],
        limit: int,
    ) -> list[OSINTSignal]:
        latmin, lonmin, latmax, lonmax = bbox
        url = _OPENSKY_URL.format(
            latmin=latmin, lonmin=lonmin, latmax=latmax, lonmax=lonmax
        )

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("OpenSky URL blocked: %s", exc)
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
                        await asyncio.sleep(4.0 * (attempt + 1))
                    else:
                        logger.info("OpenSky fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        states = body.get("states", [])
        if not isinstance(states, list):
            return []

        now = datetime.now(timezone.utc)
        signals: list[OSINTSignal] = []

        for state in states[:limit]:
            if not isinstance(state, list) or len(state) < 12:
                continue

            icao24 = str(state[0] or "").strip()
            if not icao24:
                continue

            callsign = str(state[1] or "").strip()
            origin_country = str(state[2] or country).strip()
            time_position = state[3]
            longitude = state[5]
            latitude = state[6]
            baro_altitude = state[7]
            on_ground = state[8]
            velocity = state[9]
            true_track = state[10]
            vertical_rate = state[11]

            if isinstance(time_position, (int, float)):
                published = datetime.fromtimestamp(
                    time_position, tz=timezone.utc
                )
            else:
                published = now

            display_name = callsign or icao24.upper()
            title = f"ADS-B: {display_name} (ICAO {icao24.upper()})"
            source_url = f"https://opensky-network.org/aircraft-details?icao24={icao24}"

            summary_parts = [
                f"ICAO24: {icao24.upper()}",
                f"Callsign: {callsign or 'N/A'}",
                f"Country: {origin_country}",
            ]
            if latitude is not None and longitude is not None:
                summary_parts.append(f"Position: {latitude}, {longitude}")
            if baro_altitude is not None:
                summary_parts.append(f"Altitude: {baro_altitude} m")
            if velocity is not None:
                summary_parts.append(f"Velocity: {velocity} m/s")
            if true_track is not None:
                summary_parts.append(f"Track: {true_track}\u00b0")
            if vertical_rate is not None:
                summary_parts.append(f"Vertical rate: {vertical_rate} m/s")
            if on_ground is not None:
                summary_parts.append(f"On ground: {on_ground}")

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name="OpenSky Network",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.90,
                    raw_metadata={
                        "icao24": icao24,
                        "callsign": callsign,
                        "origin_country": origin_country,
                        "latitude": latitude,
                        "longitude": longitude,
                        "baro_altitude": baro_altitude,
                        "on_ground": on_ground,
                        "velocity": velocity,
                        "true_track": true_track,
                        "vertical_rate": vertical_rate,
                        "signal_type": "adsb",
                    },
                )
            )
        return signals

    async def _fetch_marinetraffic(
        self, country: str, limit: int
    ) -> list[OSINTSignal]:
        api_key = getattr(settings, "MARINETRAFFIC_API_KEY", "")
        if not api_key:
            return []

        url = _MARINETRAFFIC_URL.format(api_key=api_key)

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("MarineTraffic URL blocked: %s", exc)
            return []

        body: list[Any] | dict[str, Any] | None = None
        async with self._client_ctx() as client:
            for attempt in range(3):
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    parsed = resp.json()
                    if isinstance(parsed, list):
                        body = parsed
                    elif isinstance(parsed, dict):
                        body = parsed.get("data", parsed.get("result", []))
                    break
                except Exception as exc:  # noqa: BLE001
                    if attempt < 2:
                        await asyncio.sleep(1.0 * (attempt + 1))
                    else:
                        logger.info("MarineTraffic fetch failed: %s", exc)
                        return []

        if not isinstance(body, list):
            return []

        signals: list[OSINTSignal] = []
        for vessel in body[:limit]:
            if not isinstance(vessel, dict):
                continue

            mmsi = str(vessel.get("MMSI", "") or "")
            if not mmsi:
                continue

            vessel_name = str(vessel.get("SHIPNAME", "") or vessel.get("NAME", "") or "Unknown").strip()
            flag = str(vessel.get("COUNTRY", "") or vessel.get("FLAG", "") or country).strip()
            ship_type = str(vessel.get("SHIPTYPE", "") or vessel.get("VESSEL_TYPE", "") or "Unknown").strip()
            imo = str(vessel.get("IMO", "") or "")
            callsign = str(vessel.get("CALLSIGN", "") or "")

            lat = vessel.get("LAT") or vessel.get("LATITUDE")
            lon = vessel.get("LON") or vessel.get("LONGITUDE")
            speed = vessel.get("SPEED") or vessel.get("SOG")
            course = vessel.get("COURSE") or vessel.get("HEADING")

            time_str = str(vessel.get("LAST_POS", "") or vessel.get("LAST_POS_UTC", "") or vessel.get("TIME", "") or "")
            try:
                published = datetime.fromisoformat(
                    time_str.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                published = datetime.now(timezone.utc)

            title = f"MarineTraffic: {vessel_name} (MMSI {mmsi})"
            source_url = f"https://www.marinetraffic.com/en/ais/details/ships/mmsi:{mmsi}"

            summary_parts = [
                f"MMSI: {mmsi}",
                f"Name: {vessel_name}",
                f"Flag: {flag}",
                f"Type: {ship_type}",
            ]
            if lat is not None and lon is not None:
                summary_parts.append(f"Position: {lat}, {lon}")
            if speed is not None:
                summary_parts.append(f"Speed: {speed} kn")
            if course is not None:
                summary_parts.append(f"Course: {course}\u00b0")

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=" | ".join(summary_parts)[:1000],
                    source_name="MarineTraffic",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.91,
                    raw_metadata={
                        "mmsi": mmsi,
                        "imo": imo,
                        "callsign": callsign,
                        "vessel_name": vessel_name,
                        "flag": flag,
                        "ship_type": ship_type,
                        "latitude": lat,
                        "longitude": lon,
                        "speed_knots": speed,
                        "course": course,
                        "signal_type": "ais",
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


__all__ = ["SIGINTProvider"]
