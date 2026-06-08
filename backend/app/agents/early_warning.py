"""
Early Warning Agent — automated multi-signal risk assessment and alerting.

Aggregates intelligence signals from all other specialized agents
(EagleEye, MoneyTrail, CyberSentinel, NarrativeWatch, OSINT) and
computes per-country risk scores. When a country's composite risk
exceeds configured thresholds, the agent generates structured alerts
for analyst review.

Risk scoring methodology:

* Each agent signal is weighted by domain relevance and confidence.
* Signals are decayed over time (exponential decay, half-life = 72h).
* The composite score is a weighted sum normalized to [0, 100].
* Thresholds: LOW (<30), ELEVATED (30-50), HIGH (50-70), CRITICAL (>70).

The agent operates at SECRET classification since it aggregates
data from multiple classified sources.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.agents.base import AgentResult, AgentTask, BaseAgent
from app.core.classification import ClassificationLevel, TLP
from app.services.llm import LLMTask, llm_router

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a strategic early warning analyst. Assess composite risk "
    "from multi-domain intelligence signals. Identify escalation vectors, "
    "tipping points, and recommend monitoring priorities. Be precise "
    "about confidence levels and information gaps."
)

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "military": 0.25,
    "financial": 0.20,
    "cyber": 0.15,
    "narrative": 0.10,
    "osint": 0.15,
    "historical": 0.15,
}

_DECAY_HALF_LIFE_HOURS = 72.0

_THRESHOLD_LOW = 30.0
_THRESHOLD_ELEVATED = 50.0
_THRESHOLD_HIGH = 70.0


class EarlyWarningAgent(BaseAgent):
    """Automated early warning system aggregating multi-agent intelligence."""

    name = "EarlyWarning-Omicron"
    max_classification = ClassificationLevel.SECRET

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
        alert_threshold: float = _THRESHOLD_ELEVATED,
    ) -> None:
        self._weights = weights or dict(_DEFAULT_WEIGHTS)
        self._alert_threshold = alert_threshold

    async def execute(self, task: AgentTask) -> AgentResult:
        country_iso: str = task.payload.get("country_iso", "")
        country_name: str = task.payload.get("country_name", country_iso)
        agent_signals: Dict[str, Any] = task.payload.get("agent_signals", {})
        historical_baseline: Optional[Dict[str, float]] = task.payload.get(
            "historical_baseline"
        )

        if not country_iso:
            return AgentResult(
                kind="early_warning",
                classification=ClassificationLevel.SECRET,
                tlp=TLP.RED,
                content=[],
                metadata={"error": "country_iso_required"},
            )

        domain_scores = self._compute_domain_scores(agent_signals)
        composite_score = self._compute_composite_score(domain_scores)
        risk_level = self._classify_risk(composite_score)
        alerts = self._generate_alerts(
            country_iso=country_iso,
            country_name=country_name,
            composite_score=composite_score,
            risk_level=risk_level,
            domain_scores=domain_scores,
        )

        findings: Dict[str, Any] = {
            "country_iso": country_iso,
            "country_name": country_name,
            "composite_score": round(composite_score, 2),
            "risk_level": risk_level,
            "domain_scores": {
                k: round(v, 2) for k, v in domain_scores.items()
            },
            "alerts": alerts,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if historical_baseline:
            findings["delta_from_baseline"] = self._compute_baseline_delta(
                domain_scores, historical_baseline
            )

        try:
            analysis = await self._analyze_risk(findings)
            findings["llm_analysis"] = analysis
        except Exception as exc:
            logger.warning("EarlyWarning: LLM analysis failed: %s", exc)
            findings["llm_analysis_error"] = str(exc)

        return AgentResult(
            kind="early_warning",
            classification=ClassificationLevel.SECRET,
            tlp=TLP.RED,
            content=findings,
            metadata={
                "country_iso": country_iso,
                "risk_level": risk_level,
                "alert_count": len(alerts),
                "signals_processed": sum(
                    len(v) if isinstance(v, list) else 1
                    for v in agent_signals.values()
                ),
            },
        )

    def _compute_domain_scores(
        self, agent_signals: Dict[str, Any]
    ) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        now = datetime.now(timezone.utc)

        for domain, signals in agent_signals.items():
            if isinstance(signals, list):
                raw_scores = [
                    self._score_signal(s, now) for s in signals if isinstance(s, dict)
                ]
            elif isinstance(signals, dict):
                raw_scores = [self._score_signal(signals, now)]
            else:
                raw_scores = [0.0]

            if raw_scores:
                scores[domain] = min(100.0, sum(raw_scores) / len(raw_scores) * 1.5)
            else:
                scores[domain] = 0.0

        return scores

    @staticmethod
    def _score_signal(signal: Dict[str, Any], now: datetime) -> float:
        base_score = float(signal.get("severity", signal.get("score", 50.0)))
        timestamp_str = signal.get("timestamp")
        if timestamp_str:
            try:
                signal_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                age_hours = (now - signal_time).total_seconds() / 3600.0
                decay = math.exp(-0.693 * age_hours / _DECAY_HALF_LIFE_HOURS)
                base_score *= decay
            except (ValueError, TypeError):
                pass
        return min(100.0, max(0.0, base_score))

    def _compute_composite_score(self, domain_scores: Dict[str, float]) -> float:
        total_weight = 0.0
        weighted_sum = 0.0

        for domain, score in domain_scores.items():
            weight = self._weights.get(domain, 0.1)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return weighted_sum / total_weight

    @staticmethod
    def _classify_risk(score: float) -> str:
        if score >= _THRESHOLD_HIGH:
            return "CRITICAL"
        if score >= _THRESHOLD_ELEVATED:
            return "HIGH"
        if score >= _THRESHOLD_LOW:
            return "ELEVATED"
        return "LOW"

    def _generate_alerts(
        self,
        *,
        country_iso: str,
        country_name: str,
        composite_score: float,
        risk_level: str,
        domain_scores: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        alerts: list[dict[str, Any]] = []

        if composite_score >= self._alert_threshold:
            alerts.append({
                "type": "composite_threshold",
                "severity": risk_level,
                "message": (
                    f"{country_name} ({country_iso}) composite risk score "
                    f"{composite_score:.1f} exceeds threshold "
                    f"{self._alert_threshold:.1f}"
                ),
                "score": composite_score,
            })

        for domain, score in domain_scores.items():
            if score >= _THRESHOLD_HIGH:
                alerts.append({
                    "type": "domain_critical",
                    "severity": "CRITICAL",
                    "domain": domain,
                    "message": (
                        f"{country_name} ({country_iso}) domain '{domain}' "
                        f"score {score:.1f} is CRITICAL"
                    ),
                    "score": score,
                })
            elif score >= _THRESHOLD_ELEVATED:
                alerts.append({
                    "type": "domain_elevated",
                    "severity": "HIGH",
                    "domain": domain,
                    "message": (
                        f"{country_name} ({country_iso}) domain '{domain}' "
                        f"score {score:.1f} is ELEVATED"
                    ),
                    "score": score,
                })

        return alerts

    @staticmethod
    def _compute_baseline_delta(
        current: Dict[str, float], baseline: Dict[str, float]
    ) -> Dict[str, float]:
        delta: Dict[str, float] = {}
        for domain, score in current.items():
            base = baseline.get(domain, 0.0)
            delta[domain] = round(score - base, 2)
        return delta

    async def _analyze_risk(self, findings: Dict[str, Any]) -> str:
        prompt = (
            f"Provide a strategic early warning assessment based on these "
            f"multi-domain risk scores.\n\n"
            f"Country: {findings.get('country_name')} ({findings.get('country_iso')})\n"
            f"Composite Score: {findings.get('composite_score')}\n"
            f"Risk Level: {findings.get('risk_level')}\n"
            f"Domain Scores: {findings.get('domain_scores')}\n"
            f"Alerts: {findings.get('alerts')}\n"
            f"Delta from Baseline: {findings.get('delta_from_baseline', 'N/A')}"
        )
        llm_task = LLMTask(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            classification=ClassificationLevel.SECRET,
            metadata={
                "agent": self.name,
                "country": findings.get("country_iso"),
                "risk_level": findings.get("risk_level"),
            },
        )
        result = await llm_router.generate(llm_task)
        return result.text


early_warning_agent = EarlyWarningAgent()


__all__ = ["EarlyWarningAgent", "early_warning_agent"]
