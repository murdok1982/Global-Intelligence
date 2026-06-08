"""
Cyber intelligence (CYBINT) provider.

Aggregates threat data from GreyNoise Community API, CISA Known
Exploited Vulnerabilities catalog, and optionally Shodan (when an
API key is configured).

CISA KEV data is treated as Admiralty reliability ``A`` (official US
government source). GreyNoise community data is ``B``. Shodan is
``B`` when available.
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

_GREYNOISE_URL = "https://api.greynoise.io/v3/community/{ip}"
_CISA_KEV_URL = (
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
)
_SHODAN_URL = "https://api.shodan.io/shodan/host/{ip}?key={api_key}"


class CYBINTProvider(OSINTProvider):
    """Cyber intelligence from GreyNoise, CISA KEV, and Shodan."""

    name = "cybint"
    default_reliability = "B"

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

        kev_signals = await self._fetch_cisa_kev(country, limit)
        signals.extend(kev_signals)

        gn_signals = await self._fetch_greynoise(country)
        signals.extend(gn_signals)

        if settings.SHODAN_API_KEY:
            shodan_signals = await self._fetch_shodan(country)
            signals.extend(shodan_signals)

        return signals[: settings.OSINT_MAX_PER_SOURCE]

    async def _fetch_cisa_kev(
        self, country: str, limit: int
    ) -> list[OSINTSignal]:
        url = _CISA_KEV_URL

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("CISA KEV URL blocked: %s", exc)
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
                        logger.info("CISA KEV fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        vulnerabilities = body.get("vulnerabilities", [])
        if not isinstance(vulnerabilities, list):
            return []

        now = datetime.now(timezone.utc)
        signals: list[OSINTSignal] = []

        for vuln in vulnerabilities[:limit]:
            if not isinstance(vuln, dict):
                continue
            cve_id = str(vuln.get("cveID", "") or "")
            if not cve_id:
                continue

            vendor = str(vuln.get("vendorProject", "") or "Unknown")
            product = str(vuln.get("product", "") or "Unknown")
            vuln_name = str(vuln.get("vulnerabilityName", "") or cve_id)
            date_added = str(vuln.get("dateAdded", "") or "")
            short_desc = str(vuln.get("shortDescription", "") or "")
            required_action = str(vuln.get("requiredAction", "") or "")
            known_ransomware = str(vuln.get("knownRansomwareCampaignUse", "") or "")

            try:
                published = datetime.strptime(date_added, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                published = now

            title = f"{cve_id}: {vuln_name}"
            source_url = f"https://www.cisa.gov/known-exploited-vulnerabilities-catalog/{cve_id}"

            signals.append(
                OSINTSignal(
                    country=country,
                    category="security",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=short_desc[:1000],
                    source_name="CISA KEV",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.95,
                    raw_metadata={
                        "cve_id": cve_id,
                        "vendor": vendor,
                        "product": product,
                        "date_added": date_added,
                        "required_action": required_action,
                        "known_ransomware_use": known_ransomware,
                    },
                )
            )
        return signals

    async def _fetch_greynoise(self, country: str) -> list[OSINTSignal]:
        ip = "8.8.8.8"
        url = _GREYNOISE_URL.format(ip=ip)

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("GreyNoise URL blocked: %s", exc)
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
                        logger.info("GreyNoise fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        if body.get("message") != "Success":
            return []

        now = datetime.now(timezone.utc)
        signals: list[OSINTSignal] = []

        ip_val = str(body.get("ip", ip))
        classification = str(body.get("classification", "unknown"))
        name = str(body.get("name", "unknown"))
        last_seen = str(body.get("last_seen", "") or "")
        noise = body.get("noise")
        riot = body.get("riot")

        title = f"GreyNoise: {ip_val} classified as {classification} ({name})"
        source_url = f"https://viz.greynoise.io/ip/{ip_val}"

        try:
            published = datetime.strptime(last_seen, "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except (ValueError, TypeError):
            published = now

        signals.append(
            OSINTSignal(
                country=country,
                category="security",
                title=title[:500],
                url=canonical_url(source_url),
                summary=f"IP {ip_val}: noise={noise}, riot={riot}, classification={classification}",
                source_name="GreyNoise Community",
                published_at=published,
                language="en",
                admiralty_reliability="B",
                admiralty_credibility=3,
                confidence_score=0.60,
                raw_metadata={
                    "ip": ip_val,
                    "classification": classification,
                    "name": name,
                    "noise": noise,
                    "riot": riot,
                    "last_seen": last_seen,
                },
            )
        )
        return signals

    async def _fetch_shodan(self, country: str) -> list[OSINTSignal]:
        api_key = settings.SHODAN_API_KEY
        ip = "8.8.8.8"
        url = _SHODAN_URL.format(ip=ip, api_key=api_key)

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("Shodan URL blocked: %s", exc)
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
                        logger.info("Shodan fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict):
            return []

        now = datetime.now(timezone.utc)
        signals: list[OSINTSignal] = []

        ip_val = str(body.get("ip_str", ip))
        org = str(body.get("org", "Unknown"))
        isp = str(body.get("isp", "Unknown"))
        os_info = str(body.get("os", "") or "Unknown")
        country_code = str(body.get("country_code", "") or "")
        city = str(body.get("city", "") or "")
        hostnames = body.get("hostnames", [])
        ports = body.get("ports", [])
        vulns = body.get("vulns", [])

        title = f"Shodan: {ip_val} ({org}, {isp})"
        source_url = f"https://www.shodan.io/host/{ip_val}"

        vuln_list = [str(v) for v in vulns[:10]] if isinstance(vulns, list) else []
        port_list = [str(p) for p in ports[:20]] if isinstance(ports, list) else []

        summary_parts = [
            f"IP: {ip_val}",
            f"Org: {org}",
            f"ISP: {isp}",
            f"OS: {os_info}",
        ]
        if city:
            summary_parts.append(f"City: {city}")
        if country_code:
            summary_parts.append(f"Country: {country_code}")
        if port_list:
            summary_parts.append(f"Ports: {', '.join(port_list)}")
        if vuln_list:
            summary_parts.append(f"Vulns: {', '.join(vuln_list)}")

        signals.append(
            OSINTSignal(
                country=country,
                category="security",
                title=title[:500],
                url=canonical_url(source_url),
                summary=" | ".join(summary_parts)[:1000],
                source_name="Shodan",
                published_at=now,
                language="en",
                admiralty_reliability="B",
                admiralty_credibility=3,
                confidence_score=0.65,
                raw_metadata={
                    "ip": ip_val,
                    "org": org,
                    "isp": isp,
                    "os": os_info,
                    "country_code": country_code,
                    "city": city,
                    "hostnames": hostnames,
                    "ports": ports,
                    "vulns": vulns,
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


__all__ = ["CYBINTProvider"]
