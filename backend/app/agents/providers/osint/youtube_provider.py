"""
YouTube OSINT provider via public RSS feeds — no API key required.

Uses the public YouTube RSS endpoint:
    https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

Reads channel list from ``sources.json`` (sibling file) under the
``youtube_channels`` key. Each channel entry must have ``channel_id``,
``name``, ``categories``, ``language`` and ``reliability`` fields.

This provider does NOT use the YouTube Data API v3 — it relies on the
public RSS feeds that YouTube exposes for every channel. Rate limiting
is applied via a 0.5s delay between channel fetches.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

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


_SOURCES_PATH = Path(__file__).with_name("sources.json")
_RATE_LIMIT_S = 0.5

_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_YT_NS = "{http://www.youtube.com/xml/schemas/2015}"


def _parse_pub_date(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    raw = raw.strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return datetime.now(timezone.utc)


def _text(elem: ET.Element | None) -> str:
    if elem is None or elem.text is None:
        return ""
    return elem.text.strip()


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"<[^>]+>", "", text).strip()


def _load_channels() -> list[dict[str, Any]]:
    try:
        data = json.loads(_SOURCES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data.get("youtube_channels", [])
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("YouTube sources.json could not be loaded: %s", exc)
        return []


class YouTubeProvider(OSINTProvider):
    """YouTube channel aggregator via public RSS feeds."""

    name = "youtube"
    default_reliability = "B"

    def __init__(
        self,
        channels: list[dict[str, Any]] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._channels = channels if channels is not None else _load_channels()
        self._client = http_client

    async def execute(
        self,
        country_iso: str,
        days_back: int = 7,
        limit: int = 25,
    ) -> list[OSINTSignal]:
        if not self._channels:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
        per_channel = min(limit, settings.OSINT_MAX_PER_SOURCE)

        results: list[OSINTSignal] = []

        async with self._client_ctx() as client:
            for ch in self._channels:
                try:
                    batch = await self._fetch_channel(
                        client, ch, country_iso, cutoff, per_channel
                    )
                    results.extend(batch)
                    await asyncio.sleep(_RATE_LIMIT_S)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "YouTube provider channel %s failed: %s",
                        ch.get("name", "?"),
                        exc.__class__.__name__,
                    )
                    continue

        return results[:limit]

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

    async def _fetch_channel(
        self,
        client: httpx.AsyncClient,
        channel: dict[str, Any],
        country_iso: str,
        cutoff: datetime,
        per_channel: int,
    ) -> list[OSINTSignal]:
        channel_id = channel.get("channel_id", "")
        if not channel_id:
            return []

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        channel_name = channel.get("name", "YouTube")
        reliability = channel.get("reliability", "B")
        categories = channel.get("categories", [])

        try:
            assert_public_url(feed_url)
        except SSRFBlockedError as exc:
            logger.warning("YouTube SSRF blocked for %s: %s", channel_name, exc)
            return []

        last_exc: Exception | None = None
        body: bytes | None = None
        for attempt in range(3):
            try:
                response = await client.get(feed_url)
                response.raise_for_status()
                body = response.content
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < 2:
                    await asyncio.sleep(0.5 * (attempt + 1))
        if body is None:
            logger.info(
                "YouTube fetch failed for %s after retries: %s",
                channel_name,
                last_exc.__class__.__name__ if last_exc else "?",
            )
            return []

        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            logger.info("YouTube parse error for %s: %s", channel_name, exc)
            return []

        signals: list[OSINTSignal] = []
        country_token = country_iso.upper()

        for entry in root.findall(f"{_ATOM_NS}entry"):
            title = _text(entry.find(f"{_ATOM_NS}title"))
            link_elem = entry.find(f"{_ATOM_NS}link")
            link = link_elem.get("href", "") if link_elem is not None else ""
            published_raw = _text(entry.find(f"{_ATOM_NS}published"))
            summary = _strip_html(
                _text(entry.find(f"{_ATOM_NS}summary"))
                or _text(entry.find(f"{_ATOM_NS}content"))
            )

            if not title or not link:
                continue
            try:
                assert_public_url(link)
            except SSRFBlockedError:
                continue
            link = canonical_url(link)

            published = _parse_pub_date(published_raw)
            if published < cutoff:
                continue

            combined_text = f"{title} {summary}"
            category = classify_category(combined_text)
            if category == "other" and categories:
                category = categories[0]

            signals.append(
                OSINTSignal(
                    country=country_token or "GLOBAL",
                    category=category,
                    title=title[:500],
                    url=link,
                    summary=summary[:1000],
                    source_name=channel_name,
                    published_at=published,
                    language=channel.get("language", "en"),
                    admiralty_reliability=reliability,
                    admiralty_credibility=3,
                    confidence_score=0.5,
                    raw_metadata={
                        "provider": "youtube",
                        "channel": channel_name,
                        "channel_id": channel_id,
                    },
                )
            )
            if len(signals) >= per_channel:
                break

        return signals


__all__ = ["YouTubeProvider"]
