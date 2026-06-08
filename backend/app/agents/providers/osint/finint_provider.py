"""
Financial intelligence (FININT) provider.

Aggregates open economic indicators from the World Bank API, public
exchange-rate feeds, and commodity price data. Each data point is
normalized into an :class:`OSINTSignal` with ``category="economic"``.

World Bank data is treated as Admiralty reliability ``A`` (completely
reliable official statistics). Exchange rates and commodity prices
default to ``B`` (usually reliable) since they come from secondary
aggregators.
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

_WORLD_BANK_URL = (
    "https://api.worldbank.org/v2/country/{iso}/indicator/NY.GDP.MKTP.CD"
    "?format=json&per_page=5&date={start_year}:{end_year}&sort=date:desc"
)
_EXCHANGE_RATE_URL = "https://open.er-api.com/v6/latest/USD"
_COMMODITIES_URL = "https://api.worldbank.org/v2/country/USA/indicator/PX.REX.REAL?format=json&per_page=1&date={year}&sort=date:desc"


class FININTProvider(OSINTProvider):
    """Financial intelligence from World Bank, FX, and commodity feeds."""

    name = "finint"
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

        wb_signals = await self._fetch_world_bank(country)
        signals.extend(wb_signals)

        fx_signals = await self._fetch_exchange_rates(country)
        signals.extend(fx_signals)

        commodity_signals = await self._fetch_commodities(country)
        signals.extend(commodity_signals)

        return signals[: settings.OSINT_MAX_PER_SOURCE]

    async def _fetch_world_bank(self, country: str) -> list[OSINTSignal]:
        now = datetime.now(timezone.utc)
        start_year = now.year - 1
        end_year = now.year
        iso = country if len(country) == 3 else "WLD"
        url = _WORLD_BANK_URL.format(
            iso=iso, start_year=start_year, end_year=end_year
        )

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("World Bank URL blocked: %s", exc)
            return []

        body: list[Any] | None = None
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
                        logger.info("World Bank fetch failed: %s", exc)
                        return []

        if not isinstance(body, list) or len(body) < 2:
            return []

        records = body[1]
        if not isinstance(records, list):
            return []

        signals: list[OSINTSignal] = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            value = rec.get("value")
            if value is None:
                continue
            date_str = str(rec.get("date", now.year))
            try:
                published = datetime(int(date_str), 1, 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published = now

            indicator_name = rec.get("indicator", {}).get("value", "GDP")
            country_name = rec.get("country", {}).get("value", country)
            title = f"{country_name} GDP: {value:,.0f} USD ({date_str})"
            source_url = f"https://data.worldbank.org/indicator/NY.GDP.MKTP.CD?locations={iso}"

            signals.append(
                OSINTSignal(
                    country=country,
                    category="economic",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=f"World Bank official GDP indicator: {indicator_name}",
                    source_name="World Bank",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.90,
                    raw_metadata={
                        "indicator": "NY.GDP.MKTP.CD",
                        "value": value,
                        "date": date_str,
                    },
                )
            )
        return signals

    async def _fetch_exchange_rates(self, country: str) -> list[OSINTSignal]:
        url = _EXCHANGE_RATE_URL

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("Exchange rate URL blocked: %s", exc)
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
                        logger.info("Exchange rate fetch failed: %s", exc)
                        return []

        if not isinstance(body, dict) or body.get("result") != "success":
            return []

        rates = body.get("rates", {})
        if not isinstance(rates, dict):
            return []

        time_last_update = body.get("time_last_update_utc", "")
        try:
            published = datetime.strptime(
                time_last_update, "%a, %d %b %Y %H:%M:%S %z"
            )
        except (ValueError, TypeError):
            published = datetime.now(timezone.utc)

        target_currencies = ["EUR", "GBP", "JPY", "CNY", "MXN", "BRL", "COP"]
        signals: list[OSINTSignal] = []

        for currency in target_currencies:
            rate = rates.get(currency)
            if rate is None:
                continue
            title = f"USD/{currency} exchange rate: {rate}"
            source_url = "https://open.er-api.com/v6/latest/USD"

            signals.append(
                OSINTSignal(
                    country=country,
                    category="economic",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary=f"Exchange rate USD to {currency}: {rate}",
                    source_name="Open Exchange Rates",
                    published_at=published,
                    language="en",
                    admiralty_reliability="B",
                    admiralty_credibility=2,
                    confidence_score=0.75,
                    raw_metadata={
                        "base": "USD",
                        "target": currency,
                        "rate": rate,
                    },
                )
            )
        return signals

    async def _fetch_commodities(self, country: str) -> list[OSINTSignal]:
        now = datetime.now(timezone.utc)
        url = _COMMODITIES_URL.format(year=now.year)

        try:
            assert_public_url(url)
        except SSRFBlockedError as exc:
            logger.warning("Commodities URL blocked: %s", exc)
            return []

        body: list[Any] | None = None
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
                        logger.info("Commodities fetch failed: %s", exc)
                        return []

        if not isinstance(body, list) or len(body) < 2:
            return []

        records = body[1]
        if not isinstance(records, list) or not records:
            return []

        signals: list[OSINTSignal] = []
        for rec in records:
            if not isinstance(rec, dict):
                continue
            value = rec.get("value")
            if value is None:
                continue
            date_str = str(rec.get("date", now.year))
            try:
                published = datetime(int(date_str), 1, 1, tzinfo=timezone.utc)
            except (ValueError, TypeError):
                published = now

            title = f"Real exchange rate index: {value} ({date_str})"
            source_url = "https://data.worldbank.org/indicator/PX.REX.REAL"

            signals.append(
                OSINTSignal(
                    country=country,
                    category="economic",
                    title=title[:500],
                    url=canonical_url(source_url),
                    summary="World Bank real effective exchange rate index",
                    source_name="World Bank",
                    published_at=published,
                    language="en",
                    admiralty_reliability="A",
                    admiralty_credibility=1,
                    confidence_score=0.85,
                    raw_metadata={
                        "indicator": "PX.REX.REAL",
                        "value": value,
                        "date": date_str,
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


__all__ = ["FININTProvider"]
