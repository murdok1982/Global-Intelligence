from __future__ import annotations

import asyncio
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, model_validator

from app.agents.base import AgentResult, AgentTask
from app.agents.cyber_sentinel import cyber_sentinel_agent
from app.agents.eagle_eye import eagle_eye_agent
from app.agents.early_warning import early_warning_agent
from app.agents.money_trail import money_trail_agent
from app.agents.narrative_watch import narrative_watch_agent
from app.agents.osint import OSINTAgent
from app.api.deps import get_current_active_user
from app.core.classification import ClassificationLevel, TLP
from app.core.limiter import limiter
from app.models.user import User

router = APIRouter()


class EagleEyeRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"country_iso": "UA", "days_back": 14, "cloud_cover_max": 20.0}]
        }
    }

    country_iso: str = Field(description="ISO 3166-1 alpha-3 country code")
    days_back: int = Field(default=14, description="Number of days to look back", ge=1, le=90)
    coordinates: Optional[Dict[str, float]] = None
    cloud_cover_max: float = Field(default=30.0, description="Maximum cloud cover percentage")


class MoneyTrailRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"entity_name": "Rosneft", "country_iso": "RU"}]
        }
    }

    entity_name: Optional[str] = Field(default=None, description="Name of the entity to track")
    country_iso: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-3 country code")
    commodities: List[str] = Field(default=["oil_brent", "natural_gas", "wheat", "rare_earths"], description="Commodity identifiers to monitor")
    crypto_addresses: List[str] = Field(default=[], description="Cryptocurrency wallet addresses to trace")

    @model_validator(mode="after")
    def _require_entity_or_country(self) -> "MoneyTrailRequest":
        if not self.entity_name and not self.country_iso:
            raise ValueError("entity_name or country_iso is required")
        return self


class CyberSentinelRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"target_ip": "1.2.3.4"}]
        }
    }

    target_ip: Optional[str] = Field(default=None, description="Target IP address or country ISO code")
    country_iso: Optional[str] = Field(default=None, description="ISO 3166-1 alpha-3 country code")
    target_asns: List[str] = Field(default=[], description="Autonomous System Numbers to investigate")
    cve_keywords: List[str] = Field(default=[], description="CVE identifiers or keywords to search")
    days_back: int = Field(default=7, description="Number of days to look back", ge=1, le=90)

    @model_validator(mode="after")
    def _require_target_or_country(self) -> "CyberSentinelRequest":
        if not self.target_ip and not self.country_iso:
            raise ValueError("target_ip or country_iso is required")
        return self


class NarrativeWatchRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"country_iso": "CN", "topic": "trade"}]
        }
    }

    country_iso: str = Field(description="ISO 3166-1 alpha-3 country code")
    topic: str = Field(description="Topic or narrative to monitor")
    days_back: int = Field(default=7, description="Number of days to look back", ge=1, le=90)
    sources: List[str] = Field(default=[], description="Specific source identifiers to query")
    detect_bots: bool = Field(default=True, description="Enable bot detection analysis")


class EarlyWarningRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"country_iso": "KP"}]
        }
    }

    country_iso: str = Field(description="ISO 3166-1 alpha-3 country code")
    country_name: Optional[str] = Field(default=None, description="Human-readable country name")
    agent_signals: Dict[str, Any] = Field(default={}, description="Aggregated signal data from other agents")
    historical_baseline: Optional[Dict[str, float]] = Field(default=None, description="Historical baseline metrics for comparison")


class FullAnalysisRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [{"country_iso": "RU", "days_back": 7}]
        }
    }

    country_iso: str = Field(description="ISO 3166-1 alpha-3 country code")
    days_back: int = Field(default=7, description="Number of days to look back", ge=1, le=90)
    topic: Optional[str] = Field(default=None, description="Specific topic focus for analysis")
    coordinates: Optional[Dict[str, float]] = Field(default=None, description="Geographic coordinates for regional analysis")


def _serialize_result(result: AgentResult) -> dict[str, Any]:
    data = asdict(result)
    data["classification"] = result.classification.value
    data["tlp"] = result.tlp.value
    return data


def _require_restricted(user: User) -> None:
    clearance = ClassificationLevel.from_any(int(user.clearance_level or 0))
    if clearance < ClassificationLevel.RESTRICTED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="RESTRICTED clearance minimum required for agent execution",
        )


@router.post("/eagle-eye/execute")
@limiter.limit("10/minute")
async def execute_eagle_eye(
    request: Request,
    body: EagleEyeRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)
    task = AgentTask(
        kind="satellite_analysis",
        classification=ClassificationLevel.RESTRICTED,
        tlp=TLP.GREEN,
        user_id=current_user.id,
        payload={
            "region": body.country_iso,
            "country_iso": body.country_iso,
            "days_back": body.days_back,
            "coordinates": body.coordinates,
            "cloud_cover_max": body.cloud_cover_max,
        },
    )
    result = await eagle_eye_agent.run(task)
    return _serialize_result(result)


@router.post("/money-trail/execute")
@limiter.limit("10/minute")
async def execute_money_trail(
    request: Request,
    body: MoneyTrailRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)
    task = AgentTask(
        kind="financial_intelligence",
        classification=ClassificationLevel.CONFIDENTIAL,
        tlp=TLP.AMBER,
        user_id=current_user.id,
        payload={
            "entity_name": body.entity_name,
            "country_iso": body.country_iso or "",
            "commodities": body.commodities,
            "crypto_addresses": body.crypto_addresses,
        },
    )
    result = await money_trail_agent.run(task)
    return _serialize_result(result)


@router.post("/cyber-sentinel/execute")
@limiter.limit("10/minute")
async def execute_cyber_sentinel(
    request: Request,
    body: CyberSentinelRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)
    target_ips = [body.target_ip] if body.target_ip else []
    task = AgentTask(
        kind="cyber_intelligence",
        classification=ClassificationLevel.CONFIDENTIAL,
        tlp=TLP.AMBER,
        user_id=current_user.id,
        payload={
            "target_ips": target_ips,
            "target_asns": body.target_asns,
            "cve_keywords": body.cve_keywords,
            "days_back": body.days_back,
            "country_iso": body.country_iso or "",
        },
    )
    result = await cyber_sentinel_agent.run(task)
    return _serialize_result(result)


@router.post("/narrative-watch/execute")
@limiter.limit("10/minute")
async def execute_narrative_watch(
    request: Request,
    body: NarrativeWatchRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)
    task = AgentTask(
        kind="narrative_analysis",
        classification=ClassificationLevel.PUBLIC,
        tlp=TLP.CLEAR,
        user_id=current_user.id,
        payload={
            "country_iso": body.country_iso,
            "topic": body.topic,
            "days_back": body.days_back,
            "sources": body.sources,
            "detect_bots": body.detect_bots,
        },
    )
    result = await narrative_watch_agent.run(task)
    return _serialize_result(result)


@router.post("/early-warning/execute")
@limiter.limit("10/minute")
async def execute_early_warning(
    request: Request,
    body: EarlyWarningRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)
    task = AgentTask(
        kind="early_warning",
        classification=ClassificationLevel.SECRET,
        tlp=TLP.RED,
        user_id=current_user.id,
        payload={
            "country_iso": body.country_iso,
            "country_name": body.country_name or body.country_iso,
            "agent_signals": body.agent_signals,
            "historical_baseline": body.historical_baseline,
        },
    )
    result = await early_warning_agent.run(task)
    return _serialize_result(result)


@router.post("/full-analysis/execute")
@limiter.limit("5/minute")
async def execute_full_analysis(
    request: Request,
    body: FullAnalysisRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict[str, Any]:
    _require_restricted(current_user)

    eagle_task = AgentTask(
        kind="satellite_analysis",
        classification=ClassificationLevel.RESTRICTED,
        tlp=TLP.GREEN,
        user_id=current_user.id,
        payload={
            "region": body.country_iso,
            "country_iso": body.country_iso,
            "days_back": body.days_back,
            "coordinates": body.coordinates,
        },
    )
    money_task = AgentTask(
        kind="financial_intelligence",
        classification=ClassificationLevel.CONFIDENTIAL,
        tlp=TLP.AMBER,
        user_id=current_user.id,
        payload={"country_iso": body.country_iso},
    )
    cyber_task = AgentTask(
        kind="cyber_intelligence",
        classification=ClassificationLevel.CONFIDENTIAL,
        tlp=TLP.AMBER,
        user_id=current_user.id,
        payload={"country_iso": body.country_iso, "days_back": body.days_back},
    )
    narrative_task = AgentTask(
        kind="narrative_analysis",
        classification=ClassificationLevel.PUBLIC,
        tlp=TLP.CLEAR,
        user_id=current_user.id,
        payload={
            "country_iso": body.country_iso,
            "topic": body.topic or "geopolitical tensions",
            "days_back": body.days_back,
        },
    )
    osint_agent = OSINTAgent()
    osint_task = AgentTask(
        kind="osint_scan",
        classification=ClassificationLevel.PUBLIC,
        tlp=TLP.CLEAR,
        user_id=current_user.id,
        payload={"country_iso": body.country_iso, "days_back": body.days_back},
    )

    eagle_result, money_result, cyber_result, narrative_result, osint_result = (
        await asyncio.gather(
            eagle_eye_agent.run(eagle_task),
            money_trail_agent.run(money_task),
            cyber_sentinel_agent.run(cyber_task),
            narrative_watch_agent.run(narrative_task),
            osint_agent.run(osint_task),
            return_exceptions=True,
        )
    )

    agent_signals: Dict[str, Any] = {}
    if isinstance(eagle_result, AgentResult):
        agent_signals["military"] = eagle_result.content
    if isinstance(money_result, AgentResult):
        agent_signals["financial"] = money_result.content
    if isinstance(cyber_result, AgentResult):
        agent_signals["cyber"] = cyber_result.content
    if isinstance(narrative_result, AgentResult):
        agent_signals["narrative"] = narrative_result.content
    if isinstance(osint_result, AgentResult):
        agent_signals["osint"] = osint_result.content

    warning_task = AgentTask(
        kind="early_warning",
        classification=ClassificationLevel.SECRET,
        tlp=TLP.RED,
        user_id=current_user.id,
        payload={
            "country_iso": body.country_iso,
            "country_name": body.country_iso,
            "agent_signals": agent_signals,
        },
    )
    
    try:
        warning_result = await early_warning_agent.run(warning_task)
    except Exception as e:
        warning_result = AgentResult(
            kind="early_warning",
            classification=ClassificationLevel.SECRET,
            tlp=TLP.RED,
            content={"error": str(e)},
            metadata={"error": True},
        )

    return {
        "eagle_eye": _serialize_result(eagle_result) if isinstance(eagle_result, AgentResult) else {"error": str(eagle_result)},
        "money_trail": _serialize_result(money_result) if isinstance(money_result, AgentResult) else {"error": str(money_result)},
        "cyber_sentinel": _serialize_result(cyber_result) if isinstance(cyber_result, AgentResult) else {"error": str(cyber_result)},
        "narrative_watch": _serialize_result(narrative_result) if isinstance(narrative_result, AgentResult) else {"error": str(narrative_result)},
        "osint": _serialize_result(osint_result) if isinstance(osint_result, AgentResult) else {"error": str(osint_result)},
        "early_warning": _serialize_result(warning_result),
    }
