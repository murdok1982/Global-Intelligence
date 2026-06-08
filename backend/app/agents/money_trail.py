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
from app.core.config import settings
from app.services.llm import LLMTask, llm_router

logger = logging.getLogger(__name__)

_OFAC_SDN_URL = "https://api.ofac-api.com/v4/sdn"
_EU_SANCTIONS_URL = "https://webgate.ec.europa.eu/fsd/fsf/api/export/xml"
_UN_SC_SANCTIONS_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"

_ALPHA_VANTAGE_BASE = "https://www.alphavantage.co/query"
_EIA_BASE = "https://api.eia.gov/v2"
_WORLDBANK_BASE = "https://api.worldbank.org/v2"
_METALPRICE_BASE = "https://api.metalpriceapi.com/v1/latest"

_COMMODITY_CONFIG = {
    "oil_brent": {
        "symbol": "BRT",
        "api": "alphavantage",
        "label": "Brent Crude Oil (USD/bbl)",
    },
    "natural_gas": {
        "series_id": "NG.RNGC1.D",
        "api": "eia",
        "label": "Natural Gas (USD/MMBtu)",
    },
    "wheat": {
        "indicator": "PPWHEAMT",
        "api": "worldbank",
        "label": "Wheat (USD/MT)",
    },
    "rare_earths": {
        "base": "USD",
        "symbols": "La,Nd,Dy",
        "api": "metalprice",
        "label": "Rare Earth Elements Index",
    },
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
                config = _COMMODITY_CONFIG.get(commodity)
                if not config:
                    prices[commodity] = {"status": "error", "detail": "unknown commodity"}
                    continue

                api_type = config["api"]
                try:
                    if api_type == "alphavantage":
                        result = await self._fetch_alphavantage(client, config)
                    elif api_type == "eia":
                        result = await self._fetch_eia(client, config)
                    elif api_type == "worldbank":
                        result = await self._fetch_worldbank(client, config)
                    elif api_type == "metalprice":
                        result = await self._fetch_metalprice(client, config)
                    else:
                        result = {"status": "error", "detail": "unsupported api type"}
                    prices[commodity] = result
                except Exception as exc:
                    logger.warning(
                        "MoneyTrail: commodity %s fetch failed: %s", commodity, exc
                    )
                    prices[commodity] = {"status": "error", "detail": str(exc)}

        return prices

    async def _fetch_alphavantage(
        self, client: httpx.AsyncClient, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        api_key = settings.ALPHA_VANTAGE_API_KEY or "demo"
        params = {
            "function": "GLOBAL_QUOTE",
            "symbol": config["symbol"],
            "apikey": api_key,
        }
        resp = await client.get(_ALPHA_VANTAGE_BASE, params=params)
        if resp.status_code != 200:
            return {"status": "error", "code": resp.status_code, "label": config["label"]}

        data = resp.json()
        quote = data.get("Global Quote", {})
        if not quote:
            return {"status": "no_data", "label": config["label"]}

        price = quote.get("05. price")
        change_pct = quote.get("10. change percent")
        return {
            "status": "ok",
            "label": config["label"],
            "price": float(price) if price else None,
            "change_percent": float(change_pct.rstrip("%")) if change_pct else None,
            "source": "Alpha Vantage",
        }

    async def _fetch_eia(
        self, client: httpx.AsyncClient, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        api_key = settings.EIA_API_KEY or "demo"
        url = f"{_EIA_BASE}/natural-gas/pri/sum/data/"
        params = {
            "api_key": api_key,
            "frequency": "daily",
            "data[0]": "value",
            "facets[series][]": config["series_id"],
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": 1,
        }
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return {"status": "error", "code": resp.status_code, "label": config["label"]}

        data = resp.json()
        series_data = data.get("response", {}).get("data", [])
        if not series_data:
            return {"status": "no_data", "label": config["label"]}

        latest = series_data[0]
        return {
            "status": "ok",
            "label": config["label"],
            "price": float(latest.get("value", 0)),
            "period": latest.get("period", ""),
            "source": "EIA",
        }

    async def _fetch_worldbank(
        self, client: httpx.AsyncClient, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = f"{_WORLDBANK_BASE}/country/USA/indicator/{config['indicator']}"
        params = {"format": "json", "per_page": 1, "date": "2024"}
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return {"status": "error", "code": resp.status_code, "label": config["label"]}

        data = resp.json()
        if isinstance(data, list) and len(data) > 1:
            records = data[1]
            if records and isinstance(records, list):
                latest = records[0]
                return {
                    "status": "ok",
                    "label": config["label"],
                    "price": latest.get("value"),
                    "period": latest.get("date", ""),
                    "source": "World Bank",
                }
        return {"status": "no_data", "label": config["label"]}

    async def _fetch_metalprice(
        self, client: httpx.AsyncClient, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        api_key = settings.METALPRICE_API_KEY
        if not api_key:
            return {
                "status": "no_api_key",
                "label": config["label"],
                "detail": "METALPRICE_API_KEY not configured",
            }

        params = {
            "api_key": api_key,
            "base": config["base"],
            "currencies": config["symbols"],
        }
        resp = await client.get(_METALPRICE_BASE, params=params)
        if resp.status_code != 200:
            return {"status": "error", "code": resp.status_code, "label": config["label"]}

        data = resp.json()
        rates = data.get("rates", {})
        return {
            "status": "ok",
            "label": config["label"],
            "rates": rates,
            "timestamp": data.get("timestamp", ""),
            "source": "MetalPriceAPI",
        }

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
        """Parse EU Financial Sanctions File (FSF) XML export."""
        import xml.etree.ElementTree as ET
        
        matches = []
        try:
            root = ET.fromstring(xml_text)
            for sanction in root.findall(".//sanctionEntity"):
                entity_id = sanction.get("id", "")
                remark = sanction.find(".//remark")
                regime = sanction.find(".//regulation")
                
                match_data = {
                    "source": "eu_sanctions",
                    "entity_id": entity_id,
                    "regulation": regime.get("code", "") if regime is not None else "",
                    "remark": remark.text if remark is not None and remark.text else "",
                }
                matches.append(match_data)
        except ET.ParseError:
            matches.append({"source": "eu_sanctions", "error": "XML parse failed", "raw_length": len(xml_text)})
        
        return matches

    @staticmethod
    def _parse_un_response(xml_text: str, entity_name: Optional[str]) -> List[Dict[str, Any]]:
        """Parse UN Security Council consolidated sanctions list XML."""
        import xml.etree.ElementTree as ET
        
        matches = []
        try:
            root = ET.fromstring(xml_text)
            for individual in root.findall(".//INDIVIDUAL"):
                full_name = " ".join(filter(None, [
                    individual.findtext("FIRST_NAME", ""),
                    individual.findtext("SECOND_NAME", ""),
                    individual.findtext("THIRD_NAME", ""),
                ])).strip()
                
                if entity_name and entity_name.lower() in full_name.lower():
                    matches.append({
                        "source": "un_sanctions",
                        "type": "individual",
                        "full_name": full_name,
                        "list_type": individual.findtext("UN_LIST_TYPE", ""),
                        "reference_number": individual.findtext("REFERENCE_NUMBER", ""),
                        "listed_on": individual.findtext("LISTED_ON", ""),
                    })
            
            for entity in root.findall(".//ENTITY"):
                entity_full_name = entity.findtext("FIRST_NAME", "")
                
                if entity_name and entity_name.lower() in entity_full_name.lower():
                    matches.append({
                        "source": "un_sanctions",
                        "type": "entity",
                        "full_name": entity_full_name,
                        "list_type": entity.findtext("UN_LIST_TYPE", ""),
                        "reference_number": entity.findtext("REFERENCE_NUMBER", ""),
                        "listed_on": entity.findtext("LISTED_ON", ""),
                    })
        except ET.ParseError:
            matches.append({"source": "un_sanctions", "error": "XML parse failed", "raw_length": len(xml_text)})
        
        return matches

    @staticmethod
    async def _empty_result() -> Dict[str, Any]:
        return {}


async def _safe_gather(coros: list) -> list:
    import asyncio

    results = await asyncio.gather(*coros, return_exceptions=True)
    return [r if not isinstance(r, Exception) else {"error": str(r)} for r in results]


money_trail_agent = MoneyTrailAgent()


__all__ = ["MoneyTrailAgent", "money_trail_agent"]
