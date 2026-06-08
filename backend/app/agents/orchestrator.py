"""
OpenClaw Orchestrator — top-level coordinator.

The orchestrator does not call LLMs directly. It builds typed
:class:`AgentTask` envelopes and dispatches them to the relevant
sub-agent. Every dispatch method requires an explicit
``classification`` argument — there is no implicit default. Calling
with ``classification=None`` is rejected.

Coordinates 8 specialized agents:
- OSINTAgent (collection)
- SynthesisAgent (analysis)
- ScenarioAgent (what-if)
- EagleEyeAgent (satellite/GEOINT)
- MoneyTrailAgent (financial)
- CyberSentinelAgent (cyber)
- NarrativeWatchAgent (disinformation)
- EarlyWarningAgent (alert system)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Iterable, Optional
from uuid import UUID

from app.agents.base import AgentResult, AgentTask
from app.agents.cyber_sentinel import CyberSentinelAgent
from app.agents.eagle_eye import EagleEyeAgent
from app.agents.early_warning import EarlyWarningAgent
from app.agents.money_trail import MoneyTrailAgent
from app.agents.narrative_watch import NarrativeWatchAgent
from app.agents.osint import OSINTAgent
from app.agents.scenario import ScenarioAgent
from app.agents.synthesis import SynthesisAgent
from app.core.classification import ClassificationLevel, TLP

logger = logging.getLogger(__name__)


class OpenClawOrchestrator:
    """Top-level agent coordinator for all 8 intelligence agents."""

    def __init__(self) -> None:
        self.name = "OpenClaw-Prime"
        self._osint = OSINTAgent()
        self._synthesis = SynthesisAgent()
        self._scenario = ScenarioAgent()
        self._eagle_eye = EagleEyeAgent()
        self._money_trail = MoneyTrailAgent()
        self._cyber_sentinel = CyberSentinelAgent()
        self._narrative_watch = NarrativeWatchAgent()
        self._early_warning = EarlyWarningAgent()

    @property
    def agents(self) -> dict[str, Any]:
        return {
            "osint": self._osint,
            "synthesis": self._synthesis,
            "scenario": self._scenario,
            "eagle_eye": self._eagle_eye,
            "money_trail": self._money_trail,
            "cyber_sentinel": self._cyber_sentinel,
            "narrative_watch": self._narrative_watch,
            "early_warning": self._early_warning,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_classification(
        classification: Optional[ClassificationLevel],
    ) -> ClassificationLevel:
        if classification is None:
            raise ValueError(
                "Orchestrator dispatch requires an explicit classification. "
                "Pass ClassificationLevel.PUBLIC for open-source workloads."
            )
        return ClassificationLevel.from_any(classification)

    # ------------------------------------------------------------------
    # Public dispatch methods
    # ------------------------------------------------------------------

    async def dispatch_osint_scan(
        self,
        target_country: str,
        *,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_osint target=%s classification=%s",
            target_country,
            cls.name,
        )
        task = AgentTask(
            kind="osint_scan",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"country_iso": target_country.upper()},
        )
        return await self._osint.run(task)

    async def dispatch_synthesis(
        self,
        raw_events: Iterable[Any],
        topic: str,
        *,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> str:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_synthesis topic=%r classification=%s",
            topic,
            cls.name,
        )
        task = AgentTask(
            kind="synthesis",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"country": topic, "signals": list(raw_events)},
        )
        result = await self._synthesis.run(task)
        return str(result.content or "")

    async def process_user_scenario(
        self,
        report_context: str,
        user_variable: str,
        *,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> str:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.process_user_scenario classification=%s",
            cls.name,
        )
        task = AgentTask(
            kind="scenario",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={
                "report_markdown": report_context,
                "variable": user_variable,
            },
        )
        result = await self._scenario.run(task)
        return str(result.content or "")

    async def dispatch_geoint_analysis(
        self,
        country_iso: str,
        *,
        days_back: int = 7,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_geoint target=%s classification=%s",
            country_iso,
            cls.name,
        )
        task = AgentTask(
            kind="geoint_analysis",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"country_iso": country_iso.upper(), "days_back": days_back},
        )
        return await self._eagle_eye.run(task)

    async def dispatch_financial_intel(
        self,
        *,
        entity_name: Optional[str] = None,
        country_iso: str = "",
        commodities: Optional[list[str]] = None,
        crypto_addresses: Optional[list[str]] = None,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_financial entity=%s classification=%s",
            entity_name,
            cls.name,
        )
        task = AgentTask(
            kind="financial_intelligence",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={
                "entity_name": entity_name,
                "country_iso": country_iso.upper(),
                "commodities": commodities or ["oil_brent", "natural_gas", "wheat", "rare_earths"],
                "crypto_addresses": crypto_addresses or [],
            },
        )
        return await self._money_trail.run(task)

    async def dispatch_cyber_intel(
        self,
        *,
        target_ip: Optional[str] = None,
        country_iso: str = "",
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_cyber target=%s classification=%s",
            target_ip or country_iso,
            cls.name,
        )
        task = AgentTask(
            kind="cyber_intelligence",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"target_ip": target_ip, "country_iso": country_iso.upper()},
        )
        return await self._cyber_sentinel.run(task)

    async def dispatch_narrative_analysis(
        self,
        *,
        country_iso: str = "",
        topic: str = "",
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_narrative country=%s topic=%s",
            country_iso,
            topic,
        )
        task = AgentTask(
            kind="narrative_analysis",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"country_iso": country_iso.upper(), "topic": topic},
        )
        return await self._narrative_watch.run(task)

    async def dispatch_early_warning(
        self,
        *,
        country_iso: str,
        signals: Optional[dict[str, Any]] = None,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> AgentResult:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_early_warning country=%s classification=%s",
            country_iso,
            cls.name,
        )
        task = AgentTask(
            kind="early_warning",
            classification=cls,
            tlp=tlp,
            user_id=user_id,
            payload={"country_iso": country_iso.upper(), "signals": signals or {}},
        )
        return await self._early_warning.run(task)

    async def dispatch_full_analysis(
        self,
        country_iso: str,
        *,
        classification: Optional[ClassificationLevel] = None,
        tlp: TLP = TLP.CLEAR,
        user_id: Optional[UUID] = None,
    ) -> dict[str, AgentResult]:
        cls = self._require_classification(classification)
        logger.info(
            "orchestrator.dispatch_full_analysis country=%s classification=%s",
            country_iso,
            cls.name,
        )

        coros = {
            "osint": self.dispatch_osint_scan(
                country_iso, classification=cls, tlp=tlp, user_id=user_id
            ),
            "geoint": self.dispatch_geoint_analysis(
                country_iso, classification=cls, tlp=tlp, user_id=user_id
            ),
            "financial": self.dispatch_financial_intel(
                country_iso=country_iso, classification=cls, tlp=tlp, user_id=user_id
            ),
            "cyber": self.dispatch_cyber_intel(
                country_iso=country_iso, classification=cls, tlp=tlp, user_id=user_id
            ),
            "narrative": self.dispatch_narrative_analysis(
                country_iso=country_iso, classification=cls, tlp=tlp, user_id=user_id
            ),
        }

        results = await asyncio.gather(*coros.values(), return_exceptions=True)
        
        output = {}
        for key, result in zip(coros.keys(), results):
            if isinstance(result, Exception):
                logger.warning("Agent %s failed: %s", key, result)
                output[key] = AgentResult(
                    kind=f"{key}_error",
                    classification=cls,
                    tlp=tlp,
                    content=None,
                    metadata={"error": str(result)},
                )
            else:
                output[key] = result

        warning_result = await self.dispatch_early_warning(
            country_iso=country_iso,
            signals={k: str(v.content)[:500] for k, v in output.items() if v.content},
            classification=cls,
            tlp=tlp,
            user_id=user_id,
        )
        output["early_warning"] = warning_result

        return output


openclaw_master = OpenClawOrchestrator()


__all__ = ["OpenClawOrchestrator", "openclaw_master"]
