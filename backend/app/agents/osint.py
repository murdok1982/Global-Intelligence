"""
OSINT Agent — open-source intelligence collector.

This agent only processes PUBLIC data. It is a thin orchestration
layer over the provider plugins under
:mod:`app.agents.providers.osint`.

Execution model:

* All configured providers are launched in parallel through
  :func:`asyncio.gather` with ``return_exceptions=True`` so a single
  failing provider never sinks the scan.
* Signals are de-duplicated by canonical URL (case-insensitive host,
  no ``utm_*`` / ``fbclid`` query params). The first occurrence wins.
* If every provider returns empty / fails, an
  ``osint.all_providers_failed`` audit event is emitted via
  :data:`audit_service`. The agent still returns an empty list so
  upstream callers receive a deterministic shape.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from typing import Any, Dict, List, Sequence

from app.agents.base import AgentResult, AgentTask, BaseAgent
from app.agents.providers.osint import (
    ACLEDProvider,
    CYBINTProvider,
    GDELTProvider,
    FININTProvider,
    GEOINTProvider,
    NewsAPIProvider,
    OSINTProvider,
    OSINTSignal,
    RSSProvider,
    SIGINTProvider,
    SIPRIProvider,
    YouTubeProvider,
    canonical_url,
)
from app.core.classification import ClassificationLevel, TLP


logger = logging.getLogger(__name__)


def _default_providers() -> list[OSINTProvider]:
    """Build the default provider set from settings.

    Always-on (no API key required):
        * GDELT (global events database)
        * RSS curated feed list (30 sources)
        * YouTube OSINT (10 channels via public RSS)
        * SIPRI (arms transfers)
        * ACLED (conflict events)
        * FININT (financial indicators)
        * GEOINT (geospatial events)
        * SIGINT (AIS/ADS-B tracking)
        * CYBINT (cyber threat intelligence)

    Conditional:
        * NewsAPI — only if ``settings.NEWSAPI_API_KEY`` is set.
    """
    providers: list[OSINTProvider] = [
        GDELTProvider(),
        RSSProvider(),
        YouTubeProvider(),
        SIPRIProvider(),
        ACLEDProvider(),
        FININTProvider(),
        GEOINTProvider(),
        SIGINTProvider(),
        CYBINTProvider(),
    ]
    newsapi = NewsAPIProvider()
    if newsapi._api_key:  # noqa: SLF001
        providers.append(newsapi)
    return providers


class OSINTAgent(BaseAgent):
    """Collects structured signals from open public sources only."""

    name = "OSINT-Alpha"
    max_classification = ClassificationLevel.PUBLIC

    def __init__(self, providers: Sequence[OSINTProvider] | None = None) -> None:
        self.providers: list[OSINTProvider] = list(
            providers if providers is not None else _default_providers()
        )

    # ------------------------------------------------------------------
    # Primary entrypoint
    # ------------------------------------------------------------------

    async def execute(self, task: AgentTask) -> AgentResult:
        # OSINT data is open-source. The agent's max_classification is
        # already PUBLIC so BaseAgent.run() would refuse anything
        # higher, but the explicit check helps when execute() is
        # called directly in tests.
        if ClassificationLevel.from_any(task.classification) > ClassificationLevel.PUBLIC:
            return AgentResult(
                kind="osint_scan",
                classification=ClassificationLevel.PUBLIC,
                tlp=TLP.CLEAR,
                content=[],
                metadata={"error": "classification_above_public"},
            )

        country_iso = str(task.payload.get("country_iso", "")).upper()
        days_back = int(task.payload.get("days_back", 7))
        limit = int(task.payload.get("limit", 25))

        if not self.providers:
            return AgentResult(
                kind="osint_scan",
                classification=ClassificationLevel.PUBLIC,
                tlp=TLP.CLEAR,
                content=[],
                metadata={"providers": 0},
            )

        results = await asyncio.gather(
            *[
                p.execute(country_iso, days_back=days_back, limit=limit)
                for p in self.providers
            ],
            return_exceptions=True,
        )

        all_signals: list[OSINTSignal] = []
        per_provider_counts: dict[str, int] = {}
        all_failed = True
        for provider, batch in zip(self.providers, results):
            if isinstance(batch, Exception):
                logger.warning(
                    "OSINT provider %s raised %s",
                    provider.name,
                    batch.__class__.__name__,
                )
                per_provider_counts[provider.name] = 0
                continue
            per_provider_counts[provider.name] = len(batch)
            if batch:
                all_failed = False
            all_signals.extend(batch)

        deduped = self._dedup(all_signals)

        if all_failed:
            await self._audit_total_failure(per_provider_counts)

        return AgentResult(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content=[asdict(s) for s in deduped],
            metadata={
                "providers": per_provider_counts,
                "deduped_count": len(deduped),
                "raw_count": len(all_signals),
            },
        )

    # ------------------------------------------------------------------
    # Backwards-compatible shim
    # ------------------------------------------------------------------

    async def gather_signals(self, country_iso: str) -> List[Dict[str, Any]]:
        """Legacy entrypoint used by older endpoints."""
        task = AgentTask(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            payload={"country_iso": country_iso.upper()},
        )
        result = await self.run(task)
        return list(result.content or [])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dedup(signals: list[OSINTSignal]) -> list[OSINTSignal]:
        """Drop duplicate URLs and normalize the kept ``url`` field.

        We rewrite ``signal.url`` to its canonical form so downstream
        consumers see a single stable spelling even when one provider
        emitted the tracked URL and another the bare one.
        """
        seen: set[str] = set()
        out: list[OSINTSignal] = []
        for s in signals:
            canonical = canonical_url(s.url)
            key = canonical.lower()
            if key in seen:
                continue
            seen.add(key)
            s.url = canonical
            out.append(s)
        return out

    async def _audit_total_failure(self, counts: dict[str, int]) -> None:
        """Emit an audit event when every provider returned empty / failed.

        We do this with a fresh session so the agent doesn't depend on
        the caller's DB transaction. Failure to audit is logged but
        never propagated — losing the audit row is preferable to
        breaking the OSINT pipeline.
        """
        try:
            from app.db.session import AsyncSessionLocal
            from app.services.audit import audit_service

            async with AsyncSessionLocal() as session:
                await audit_service.record(
                    session,
                    event_type="osint.all_providers_failed",
                    outcome="error",
                    metadata={"providers": counts},
                )
                await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "OSINT total-failure audit could not be written: %s",
                exc.__class__.__name__,
            )


class PublicSignalsAgent:
    """Sub-agent that aggregates public-data APIs.

    Placeholder kept for backwards compatibility with older imports.
    Real macro fetchers will land alongside the OSINT providers in
    follow-up sprints.
    """

    async def fetch_macro_data(self, iso: str):
        raise NotImplementedError(
            "PublicSignalsAgent requires concrete provider plugins. "
            "See docs/OSINT_PROVIDERS.md"
        )


__all__ = ["OSINTAgent", "PublicSignalsAgent"]
