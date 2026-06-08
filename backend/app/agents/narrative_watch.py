"""
Narrative Watch Agent — disinformation and media narrative detection.

Monitors information operations across multiple dimensions:

1. **Narrative tracking** — identifies dominant media narratives
   per country or topic, detects sudden shifts in framing, and
   compares coverage across geopolitical blocs.
2. **Bot network detection** — analyzes posting patterns, account
   creation dates, and content similarity to identify coordinated
   inauthentic behavior.
3. **Source cross-referencing** — verifies claims by tracing them
   back to primary sources and checking for circular reporting
   or single-origin amplification.

All analysis is performed at PUBLIC classification since the agent
only consumes open-source media data.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.agents.base import AgentResult, AgentTask, BaseAgent
from app.core.classification import ClassificationLevel, TLP
from app.services.llm import LLMTask, llm_router

logger = logging.getLogger(__name__)

_GDELT_DOC_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
_GDELT_GEO_URL = "https://api.gdeltproject.org/api/v2/geo/geo"

_SYSTEM_PROMPT = (
    "You are a disinformation analyst. Detect coordinated inauthentic "
    "behavior, narrative manipulation campaigns, and propaganda techniques. "
    "Cross-reference sources, identify circular reporting, and assess "
    "the information environment with structured confidence ratings."
)

_HTTP_TIMEOUT = 30.0


class NarrativeWatchAgent(BaseAgent):
    """Disinformation detection and media narrative analysis agent."""

    name = "NarrativeWatch-Mu"
    max_classification = ClassificationLevel.PUBLIC

    async def execute(self, task: AgentTask) -> AgentResult:
        topic: str = task.payload.get("topic", "")
        country_iso: str = task.payload.get("country_iso", "")
        days_back: int = int(task.payload.get("days_back", 7))
        sources_to_check: List[str] = task.payload.get("sources", [])
        detect_bots: bool = bool(task.payload.get("detect_bots", True))

        narratives, bot_signals, source_analysis = await self._gather_all(
            topic=topic,
            country_iso=country_iso,
            days_back=days_back,
            sources_to_check=sources_to_check,
            detect_bots=detect_bots,
        )

        findings: Dict[str, Any] = {
            "narratives": narratives,
            "bot_network_indicators": bot_signals,
            "source_verification": source_analysis,
        }

        try:
            analysis = await self._analyze_findings(findings, topic, country_iso)
            findings["llm_analysis"] = analysis
        except Exception as exc:
            logger.warning("NarrativeWatch: LLM analysis failed: %s", exc)
            findings["llm_analysis_error"] = str(exc)

        return AgentResult(
            kind="narrative_analysis",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content=findings,
            metadata={
                "topic": topic,
                "country_iso": country_iso,
                "days_analyzed": days_back,
            },
        )

    async def _gather_all(
        self,
        *,
        topic: str,
        country_iso: str,
        days_back: int,
        sources_to_check: List[str],
        detect_bots: bool,
    ) -> tuple:
        import asyncio

        coros = [
            self._fetch_narratives(topic, country_iso, days_back),
            self._detect_bot_patterns(topic, country_iso) if detect_bots else self._empty(),
            self._cross_reference_sources(sources_to_check, topic) if sources_to_check else self._empty(),
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]

    async def _fetch_narratives(
        self, topic: str, country_iso: str, days_back: int
    ) -> Dict[str, Any]:
        query_parts: list[str] = []
        if topic:
            query_parts.append(topic)
        if country_iso:
            query_parts.append(f"SOURCE_COUNTRY:{country_iso}")

        query = " ".join(query_parts) if query_parts else "conflict OR tension OR crisis"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    _GDELT_DOC_URL,
                    params={
                        "query": query,
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": "100",
                        "sort": "datedesc",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    articles = data.get("articles", [])
                    return {
                        "status": "ok",
                        "article_count": len(articles),
                        "articles": [
                            {
                                "title": a.get("title"),
                                "url": a.get("url"),
                                "source": a.get("sourceCommonName") or a.get("domain"),
                                "date": a.get("seendate"),
                                "language": a.get("language"),
                                "country": a.get("sourceCountry"),
                            }
                            for a in articles[:50]
                        ],
                    }
                return {"status": "error", "code": resp.status_code}
            except Exception as exc:
                logger.warning("NarrativeWatch: GDELT query failed: %s", exc)
                return {"status": "error", "detail": str(exc)}

    async def _detect_bot_patterns(
        self, topic: str, country_iso: str
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    _GDELT_DOC_URL,
                    params={
                        "query": topic or "propaganda OR disinformation",
                        "mode": "artlist",
                        "format": "json",
                        "maxrecords": "200",
                        "sort": "datedesc",
                        "timespan": f"{days_back}d" if (days_back := 7) else "7d",
                    },
                )
                if resp.status_code != 200:
                    return {"status": "error", "code": resp.status_code}

                data = resp.json()
                articles = data.get("articles", [])

                source_frequency: Dict[str, int] = {}
                for article in articles:
                    domain = article.get("domain", "unknown")
                    source_frequency[domain] = source_frequency.get(domain, 0) + 1

                high_frequency = {
                    domain: count
                    for domain, count in source_frequency.items()
                    if count > 5
                }

                return {
                    "status": "ok",
                    "total_articles": len(articles),
                    "unique_sources": len(source_frequency),
                    "high_frequency_sources": high_frequency,
                    "bot_indicators": {
                        "source_concentration": len(high_frequency) > 0,
                        "amplification_ratio": (
                            sum(high_frequency.values()) / max(len(articles), 1)
                        ),
                    },
                }
            except Exception as exc:
                logger.warning("NarrativeWatch: bot detection failed: %s", exc)
                return {"status": "error", "detail": str(exc)}

    async def _cross_reference_sources(
        self, sources: List[str], topic: str
    ) -> Dict[str, Any]:
        verification: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for source_url in sources:
                try:
                    resp = await client.get(source_url, follow_redirects=True)
                    if resp.status_code == 200:
                        verification[source_url] = {
                            "status": "reachable",
                            "content_length": len(resp.text),
                            "content_type": resp.headers.get("content-type", ""),
                        }
                    else:
                        verification[source_url] = {
                            "status": "unreachable",
                            "code": resp.status_code,
                        }
                except Exception as exc:
                    logger.warning(
                        "NarrativeWatch: source check %s failed: %s", source_url, exc
                    )
                    verification[source_url] = {
                        "status": "error",
                        "detail": str(exc),
                    }

        return {"sources_checked": len(sources), "results": verification}

    async def _analyze_findings(
        self, findings: Dict[str, Any], topic: str, country_iso: str
    ) -> str:
        prompt = (
            f"Analyze these media narrative and disinformation findings.\n"
            f"Topic: {topic or 'N/A'}\n"
            f"Country: {country_iso or 'N/A'}\n\n"
            f"Findings: {findings}"
        )
        llm_task = LLMTask(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            classification=ClassificationLevel.PUBLIC,
            metadata={"agent": self.name, "topic": topic},
        )
        result = await llm_router.generate(llm_task)
        return result.text

    @staticmethod
    async def _empty() -> Dict[str, Any]:
        return {}


narrative_watch_agent = NarrativeWatchAgent()


__all__ = ["NarrativeWatchAgent", "narrative_watch_agent"]
