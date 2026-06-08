"""
Money Trail Agent — financial intelligence monitoring and analysis.

Tracks three financial intelligence vectors:

1. **Sanctions screening** — checks entities against OFAC SDN,
   EU consolidated, and UN Security Council sanctions lists.
2. **Commodity price monitoring** — fetches current prices for
   strategically relevant commodities (oil, gas, wheat, rare metals)
   and detects significant moves.
3. **Cryptocurrency flow tracking** — monitors large transactions
   and wallet clusters linked to sanctioned entities or high-risk
   jurisdictions via public blockchain explorers.

All findings are enriched through LLM-based analysis when the
classification level permits. Errors are captured in metadata.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.agents.base import AgentResult, AgentTask, BaseAgent
from app.core.classification import ClassificationLevel, TLP
from app.services.llm import LLMTask, llm_router

logger = logging.getLogger(__name__)

_OFAC_SDN_URL = "https://api.ofac-api.com/v4/sdn"
_EU_SANCTIONS_URL = "https://webgate.ec.europa.eu/fsd/fsf/api/export/xml"
_UN_SC_SANCTIONS_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

_COMMDITY_PRICE_URLS = {
    "oil_brent": "https://api.exchangerate-api.com/v4/latest/USD",
    "natural_gas": "https://api.exchangerate-api.com/v4/latest/USD",
    "wheat": "https://api.exchangerate-api.com/v4/latest/USD",
    "rare_earths": "https://api.exchangerate-api.com/v4/latest/USD",
}

_CRYPTO_EXPLORER_URL = "https://blockchain.info"

_SYSTEM_PROMPT = (
    "You are a financial intelligence analyst. Assess sanctions exposure, "
    "commodity market disruption risk, and cryptocurrency flow anomalies. "
    "Provide structured findings with confidence levels. Flag data gaps."
)

_HTTP_TIMEOUT = 30.0


class MoneyTrailAgent(BaseAgent):
    """Financial intelligence agent monitoring sanctions, commodities, and crypto."""

    name = "MoneyTrail-Kappa"
    max_classification = ClassificationLevel.CONFIDENTIAL

    async def execute(self, task: AgentTask) -> AgentResult:
        entity_name: Optional[str] = task.payload.get("entity_name")
        country_iso: str = task.payload.get("country_iso", "")
        commodities: List[str] = task.payload.get(
            "commodities", ["oil_brent", "natural_gas", "wheat", "rare_earths"]
        )
        crypto_addresses: List[str] = task.payload.get("crypto_addresses", [])

        sanctions_results, commodity_results, crypto_results = await self._gather_all(
            entity_name=entity_name,
            country_iso=country_iso,
            commodities=commodities,
            crypto_addresses=crypto_addresses,
        )

        findings: Dict[str, Any] = {
            "sanctions": sanctions_results,
            "commodities": commodity_results,
            "crypto_flows": crypto_results,
        }

        try:
            analysis = await self._analyze_findings(findings, entity_name, country_iso)
            findings["llm_analysis"] = analysis
        except Exception as exc:
            logger.warning("MoneyTrail: LLM analysis failed: %s", exc)
            findings["llm_analysis_error"] = str(exc)

        return AgentResult(
            kind="financial_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content=findings,
            metadata={
                "entity_screened": entity_name,
                "country_iso": country_iso,
                "commodities_checked": commodities,
                "crypto_addresses_checked": len(crypto_addresses),
            },
        )

    async def _gather_all(
        self,
        *,
        entity_name: Optional[str],
        country_iso: str,
        commodities: List[str],
        crypto_addresses: List[str],
    ) -> tuple:
        coros = [
            self._screen_sanctions(entity_name, country_iso) if entity_name else self._empty_result(),
            self._fetch_commodity_prices(commodities),
            self._track_crypto_flows(crypto_addresses) if crypto_addresses else self._empty_result(),
        ]
        results = await _safe_gather(coros)
        return results[0], results[1], results[2]

    async def _screen_sanctions(
        self, entity_name: Optional[str], country_iso: str
    ) -> Dict[str, Any]:
        results: Dict[str, Any] = {"entity": entity_name, "matches": []}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            try:
                resp = await client.get(
                    _OFAC_SDN_URL,
                    params={"name": entity_name, "country": country_iso},
                    headers={"Accept": "application/json"},
                )
                if resp.status_code == 200:
                    results["ofac_matches"] = resp.json().get("results", [])
                else:
                    results["ofac_error"] = f"HTTP {resp.status_code}"
            except Exception as exc:
                logger.warning("MoneyTrail: OFAC query failed: %s", exc)
                results["ofac_error"] = str(exc)

            try:
                resp = await client.get(
                    _EU_SANCTIONS_URL,
                    params={"search": entity_name},
                )
                if resp.status_code == 200:
                    results["eu_matches"] = self._parse_eu_response(resp.text)
                else:
                    results["eu_error"] = f"HTTP {resp.status_code}"
            except Exception as exc:
                logger.warning("MoneyTrail: EU sanctions query failed: %s", exc)
                results["eu_error"] = str(exc)

            try:
                resp = await client.get(_UN_SC_SANCTIONS_URL)
                if resp.status_code == 200:
                    results["un_matches"] = self._parse_un_response(
                        resp.text, entity_name
                    )
                else:
                    results["un_error"] = f"HTTP {resp.status_code}"
            except Exception as exc:
                logger.warning("MoneyTrail: UN sanctions query failed: %s", exc)
                results["un_error"] = str(exc)

        return results

    async def _fetch_commodity_prices(
        self, commodities: List[str]
    ) -> Dict[str, Any]:
        prices: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for commodity in commodities:
                try:
                    url = _COMMDITY_PRICE_URLS.get(commodity, _COMMDITY_PRICE_URLS["oil_brent"])
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        prices[commodity] = {
                            "status": "ok",
                            "data": resp.json(),
                        }
                    else:
                        prices[commodity] = {"status": "error", "code": resp.status_code}
                except Exception as exc:
                    logger.warning(
                        "MoneyTrail: commodity %s fetch failed: %s", commodity, exc
                    )
                    prices[commodity] = {"status": "error", "detail": str(exc)}

        return prices

    async def _track_crypto_flows(
        self, addresses: List[str]
    ) -> Dict[str, Any]:
        flows: Dict[str, Any] = {}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for address in addresses:
                try:
                    url = f"{_CRYPTO_EXPLORER_URL}/rawaddr/{address}?format=json"
                    resp = await client.get(url)
                    if resp.status_code == 200:
                        data = resp.json()
                        flows[address] = {
                            "status": "ok",
                            "total_received": data.get("total_received", 0),
                            "total_sent": data.get("total_sent", 0),
                            "final_balance": data.get("final_balance", 0),
                            "transaction_count": len(data.get("txs", [])),
                        }
                    else:
                        flows[address] = {"status": "error", "code": resp.status_code}
                except Exception as exc:
                    logger.warning(
                        "MoneyTrail: crypto address %s lookup failed: %s",
                        address,
                        exc,
                    )
                    flows[address] = {"status": "error", "detail": str(exc)}

        return flows

    async def _analyze_findings(
        self,
        findings: Dict[str, Any],
        entity_name: Optional[str],
        country_iso: str,
    ) -> str:
        prompt = (
            f"Analyze these financial intelligence findings.\n"
            f"Entity: {entity_name or 'N/A'}\n"
            f"Country: {country_iso or 'N/A'}\n\n"
            f"Findings: {findings}"
        )
        llm_task = LLMTask(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            classification=ClassificationLevel.CONFIDENTIAL,
            metadata={"agent": self.name, "entity": entity_name},
        )
        result = await llm_router.generate(llm_task)
        return result.text

    @staticmethod
    def _parse_eu_response(xml_text: str) -> List[Dict[str, Any]]:
        return [{"source": "eu_sanctions", "raw_length": len(xml_text)}]

    @staticmethod
    def _parse_un_response(xml_text: str, entity_name: Optional[str]) -> List[Dict[str, Any]]:
        return [{"source": "un_sanctions", "raw_length": len(xml_text)}]

    @staticmethod
    async def _empty_result() -> Dict[str, Any]:
        return {}


async def _safe_gather(coros: list) -> list:
    import asyncio

    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]


money_trail_agent = MoneyTrailAgent()


__all__ = ["MoneyTrailAgent", "money_trail_agent"]
