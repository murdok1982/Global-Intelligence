"""
Tests for OSINT provider plugins.

Covers:

* SSRF guard rejects private / loopback / link-local hosts.
* Canonical URL stripping removes utm_* params.
* RSS provider parses a fixture feed correctly.
* GDELT provider parses a fixture JSON response.
* OSINTAgent deduplicates equivalent URLs across providers.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from app.agents.osint import OSINTAgent
from app.agents.providers.osint import (
    GDELTProvider,
    NewsAPIProvider,
    OSINTProvider,
    OSINTSignal,
    RSSProvider,
    SSRFBlockedError,
    assert_public_url,
    canonical_url,
    classify_category,
)


# ---------------------------------------------------------------------------
# SSRF guard
# ---------------------------------------------------------------------------


def test_ssrf_blocks_loopback() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_public_url("http://127.0.0.1/feed.xml")


def test_ssrf_blocks_private_ip_literal() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_public_url("http://10.0.0.5/feed")


def test_ssrf_blocks_link_local() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_public_url("http://169.254.169.254/")  # AWS metadata


def test_ssrf_blocks_non_http_scheme() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_public_url("file:///etc/passwd")


def test_ssrf_blocks_localhost_name() -> None:
    with pytest.raises(SSRFBlockedError):
        assert_public_url("http://localhost/feed")


def test_ssrf_allows_public_ip_literal() -> None:
    # 8.8.8.8 — Google DNS, globally routable.
    assert_public_url("http://8.8.8.8/")


# ---------------------------------------------------------------------------
# Canonical URL
# ---------------------------------------------------------------------------


def test_canonical_url_strips_utm() -> None:
    raw = "https://Example.com/path/?utm_source=x&utm_medium=y&keep=1"
    assert canonical_url(raw) == "https://example.com/path?keep=1"


def test_canonical_url_idempotent() -> None:
    once = canonical_url("https://Example.com/a/?utm_campaign=c")
    twice = canonical_url(once)
    assert once == twice


# ---------------------------------------------------------------------------
# Category classifier
# ---------------------------------------------------------------------------


def test_classify_category_military() -> None:
    assert classify_category("NATO weapons shipment to Ukraine") == "defense"


def test_classify_category_economic() -> None:
    assert classify_category("Inflation hits new record, central bank reacts") == "economic"


def test_classify_category_fallback() -> None:
    assert classify_category("Recipe for chocolate cake") == "other"


# ---------------------------------------------------------------------------
# RSS provider with httpx MockTransport
# ---------------------------------------------------------------------------


_FIXTURE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Wire</title>
    <item>
      <title>NATO troops deploy near border</title>
      <link>https://example.com/article-a?utm_source=feed</link>
      <description>Brief on military movement.</description>
      <pubDate>Mon, 19 May 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Central bank raises rates amid inflation</title>
      <link>https://example.com/article-b</link>
      <description>Economic policy update.</description>
      <pubDate>Sun, 18 May 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""


def _mock_transport_serving(body: bytes, content_type: str = "application/xml"):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=body, headers={"content-type": content_type}
        )

    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_rss_provider_parses_fixture_feed(monkeypatch) -> None:
    transport = _mock_transport_serving(_FIXTURE_RSS)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = RSSProvider(
            sources=[
                {
                    "name": "Test Wire",
                    "url": "https://example.com/feed.xml",
                    "reliability": "B",
                }
            ],
            http_client=client,
        )
        # Bypass SSRF guard for example.com (which would otherwise
        # need DNS) by monkeypatching it to a no-op.
        from app.agents.providers.osint import base as base_mod

        monkeypatch.setattr(base_mod, "assert_public_url", lambda url: None)
        # Also patch in rss_provider's local namespace.
        from app.agents.providers.osint import rss_provider as rss_mod

        monkeypatch.setattr(rss_mod, "assert_public_url", lambda url: None)

        signals = await provider.execute("USA", days_back=365, limit=10)

    assert len(signals) == 2
    titles = [s.title for s in signals]
    assert "NATO troops deploy near border" in titles
    # utm_source was stripped on canonicalization.
    assert all("utm_source" not in s.url for s in signals)
    # Reliability inherited from the source config.
    assert all(s.admiralty_reliability == "B" for s in signals)


# ---------------------------------------------------------------------------
# GDELT provider
# ---------------------------------------------------------------------------


_FIXTURE_GDELT = {
    "articles": [
        {
            "url": "https://news.example.com/story-1?utm_campaign=x",
            "title": "Election results unsettle markets",
            "seendate": "20260519080000",
            "domain": "news.example.com",
            "language": "English",
            "sourcecountry": "US",
        },
        {
            "url": "https://news.example.com/story-2",
            "title": "Diplomatic incident at border crossing",
            "seendate": "20260518120000",
            "domain": "news.example.com",
            "language": "English",
            "sourcecountry": "US",
        },
    ]
}


@pytest.mark.asyncio
async def test_gdelt_provider_parses_fixture_json(monkeypatch) -> None:
    import json

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=json.dumps(_FIXTURE_GDELT).encode(),
            headers={"content-type": "application/json"},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = GDELTProvider(
            base_url="https://api.gdeltproject.org/api/v2/doc/doc",
            http_client=client,
        )
        from app.agents.providers.osint import base as base_mod
        from app.agents.providers.osint import gdelt_provider as gdelt_mod

        monkeypatch.setattr(base_mod, "assert_public_url", lambda url: None)
        monkeypatch.setattr(gdelt_mod, "assert_public_url", lambda url: None)
        signals = await provider.execute("USA", days_back=14, limit=10)

    assert len(signals) == 2
    assert signals[0].admiralty_reliability == "C"
    # Canonicalization stripped utm_campaign.
    assert all("utm_" not in s.url for s in signals)


# ---------------------------------------------------------------------------
# NewsAPI disabled when key missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_newsapi_disabled_without_key() -> None:
    provider = NewsAPIProvider(api_key="")
    signals = await provider.execute("USA")
    assert signals == []


# ---------------------------------------------------------------------------
# OSINTAgent dedup across providers
# ---------------------------------------------------------------------------


class _StaticProvider(OSINTProvider):
    name = "static"

    def __init__(self, signals: list[OSINTSignal]) -> None:
        self._signals = signals

    async def execute(
        self, country_iso: str, days_back: int = 7, limit: int = 25
    ) -> list[OSINTSignal]:
        return list(self._signals)


def _signal(url: str, title: str = "T") -> OSINTSignal:
    return OSINTSignal(
        country="USA",
        category="other",
        title=title,
        url=url,
        summary="",
        source_name="test",
        published_at=datetime(2026, 5, 19, tzinfo=timezone.utc),
        language="en",
        admiralty_reliability="C",
        admiralty_credibility=3,
        confidence_score=0.4,
    )


@pytest.mark.asyncio
async def test_osint_agent_dedups_duplicate_urls() -> None:
    a = _StaticProvider(
        [
            _signal("https://example.com/x?utm_source=a", "from-a"),
            _signal("https://example.com/y"),
        ]
    )
    b = _StaticProvider(
        [
            # Same canonical URL as the first signal above.
            _signal("https://Example.com/x?utm_medium=b", "from-b"),
            _signal("https://example.com/z"),
        ]
    )
    agent = OSINTAgent(providers=[a, b])
    signals = await agent.gather_signals("USA")
    urls = {s["url"] for s in signals}
    # 4 inputs → 3 deduped.
    assert len(signals) == 3
    assert urls == {
        "https://example.com/x",
        "https://example.com/y",
        "https://example.com/z",
    }


@pytest.mark.asyncio
async def test_osint_agent_returns_empty_when_no_providers() -> None:
    agent = OSINTAgent(providers=[])
    out = await agent.gather_signals("USA")
    assert out == []
