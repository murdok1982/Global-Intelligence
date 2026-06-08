"""
Cyber Sentinel Agent — cyber threat intelligence and infrastructure exposure.

Monitors three cyber intelligence vectors:

1. **Infrastructure exposure** — queries Shodan to map publicly
   exposed services, open ports, and known vulnerabilities for
   target IP ranges or ASNs.
2. **Mass scanning detection** — uses GreyNoise to distinguish
   targeted attacks from background internet noise and identify
   active threat actors.
3. **CVE monitoring** — tracks critical and high-severity
   vulnerabilities from the NVD/CVE databases that may affect
   critical infrastructure or widely deployed software.

All findings are correlated and enriched through LLM-based analysis.
Errors are captured in result metadata — the agent never raises.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.agents.base import AgentResult, AgentTask, BaseAgent
from app.core.classification import ClassificationLevel, TLP
from app.services.llm import LLMTask, llm_router

logger = logging.getLogger(__name__)

_SHODAN_BASE_URL = "https://api.shodan.io"
_GREYNOISE_BASE_URL = "https://api.greynoise.io/v2"
_NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

_SYSTEM_PROMPT = (
    "You are a cyber threat intelligence analyst. Assess infrastructure "
    "exposure, distinguish targeted attacks from background noise, and "
    "prioritize vulnerabilities by exploitability and strategic impact. "
    "Provide actionable remediation guidance."
)

_HTTP_TIMEOUT = 30.0


class CyberSentinelAgent(BaseAgent):
    """Cyber intelligence agent monitoring infrastructure exposure and vulnerabilities."""

    name = "CyberSentinel-Lambda"
    max_classification = ClassificationLevel.CONFIDENTIAL

    def __init__(
        self,
        shodan_api_key: Optional[str] = None,
        greynoise_api_key: Optional[str] = None,
    ) -> None:
        self._shodan_api_key = shodan_api_key
        self._greynoise_api_key = greynoise_api_key

    async def execute(self, task: AgentTask) -> AgentResult:
        target_ips: List[str] = task.payload.get("target_ips", [])
        target_asns: List[str] = task.payload.get("target_asns", [])
        cve_keywords: List[str] = task.payload.get("cve_keywords", [])
        days_back: int = int(task.payload.get("days_back", 7))

        shodan_results, greynoise_results, cve_results = await self._gather_all(
            target_ips=target_ips,
            target_asns=target_asns,
            cve_keywords=cve_keywords,
            days_back=days_back,
        )

        findings: Dict[str, Any] = {
            "shodan_exposure": shodan_results,
            "greynoise_noise": greynoise_results,
            "cve_alerts": cve_results,
        }

        try:
            analysis = await self._analyze_findings(findings)
            findings["llm_analysis"] = analysis
        except Exception as exc:
            logger.warning("CyberSentinel: LLM analysis failed: %s", exc)
            findings["llm_analysis_error"] = str(exc)

        return AgentResult(
            kind="cyber_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content=findings,
            metadata={
                "targets_scanned": len(target_ips),
                "asns_scanned": len(target_asns),
                "cve_keywords": cve_keywords,
            },
        )

    async def _gather_all(
        self,
        *,
        target_ips: List[str],
        target_asns: List[str],
        cve_keywords: List[str],
        days_back: int,
    ) -> tuple:
        import asyncio

        coros = [
            self._query_shodan(target_ips, target_asns),
            self._query_greynoise(target_ips),
            self._query_cves(cve_keywords, days_back),
        ]
        results = await asyncio.gather(*coros, return_exceptions=True)
        return [
            r if not isinstance(r, Exception) else {"error": str(r)}
            for r in results
        ]

    async def _query_shodan(
        self, target_ips: List[str], target_asns: List[str]
    ) -> Dict[str, Any]:
        if not self._shodan_api_key:
            return {"status": "unconfigured", "detail": "no_api_key"}

        results: Dict[str, Any] = {"hosts": {}}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for ip in target_ips:
                try:
                    resp = await client.get(
                        f"{_SHODAN_BASE_URL}/shodan/host/{ip}",
                        params={"key": self._shodan_api_key},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results["hosts"][ip] = {
                            "ports": data.get("ports", []),
                            "vulns": list(data.get("vulns", {}).keys()),
                            "org": data.get("org"),
                            "os": data.get("os"),
                            "country": data.get("country_code"),
                        }
                    else:
                        results["hosts"][ip] = {"error": f"HTTP {resp.status_code}"}
                except Exception as exc:
                    logger.warning("CyberSentinel: Shodan host %s failed: %s", ip, exc)
                    results["hosts"][ip] = {"error": str(exc)}

            for asn in target_asns:
                try:
                    resp = await client.get(
                        f"{_SHODAN_BASE_URL}/shodan/host/search",
                        params={
                            "key": self._shodan_api_key,
                            "query": f"asn:{asn}",
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results[f"asn_{asn}"] = {
                            "total": data.get("total", 0),
                            "matches": [
                                {
                                    "ip": m.get("ip_str"),
                                    "port": m.get("port"),
                                    "product": m.get("product"),
                                }
                                for m in data.get("matches", [])[:50]
                            ],
                        }
                    else:
                        results[f"asn_{asn}"] = {"error": f"HTTP {resp.status_code}"}
                except Exception as exc:
                    logger.warning("CyberSentinel: Shodan ASN %s failed: %s", asn, exc)
                    results[f"asn_{asn}"] = {"error": str(exc)}

        return results

    async def _query_greynoise(self, target_ips: List[str]) -> Dict[str, Any]:
        if not self._greynoise_api_key:
            return {"status": "unconfigured", "detail": "no_api_key"}

        results: Dict[str, Any] = {"ips": {}}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for ip in target_ips:
                try:
                    resp = await client.get(
                        f"{_GREYNOISE_BASE_URL}/noise/{ip}",
                        headers={"key": self._greynoise_api_key},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        results["ips"][ip] = {
                            "seen": data.get("seen", False),
                            "classification": data.get("classification"),
                            "name": data.get("name"),
                            "last_seen": data.get("last_seen"),
                            "link": data.get("link"),
                        }
                    else:
                        results["ips"][ip] = {"error": f"HTTP {resp.status_code}"}
                except Exception as exc:
                    logger.warning("CyberSentinel: GreyNoise IP %s failed: %s", ip, exc)
                    results["ips"][ip] = {"error": str(exc)}

        return results

    async def _query_cves(
        self, keywords: List[str], days_back: int
    ) -> Dict[str, Any]:
        pub_start = (
            datetime.now(timezone.utc) - timedelta(days=days_back)
        ).strftime("%Y-%m-%dT00:00:00.000")

        results: Dict[str, Any] = {"critical_cves": [], "high_cves": []}

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            for keyword in keywords:
                try:
                    resp = await client.get(
                        _NVD_BASE_URL,
                        params={
                            "keywordSearch": keyword,
                            "pubStartDate": pub_start,
                            "resultsPerPage": 20,
                        },
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        for vuln in data.get("vulnerabilities", []):
                            cve = vuln.get("cve", {})
                            cve_id = cve.get("id", "UNKNOWN")
                            metrics = cve.get("metrics", {})
                            score = self._extract_cvss_score(metrics)
                            entry = {
                                "id": cve_id,
                                "description": self._extract_description(cve),
                                "cvss_score": score,
                                "keyword": keyword,
                            }
                            if score is not None and score >= 9.0:
                                results["critical_cves"].append(entry)
                            elif score is not None and score >= 7.0:
                                results["high_cves"].append(entry)
                    else:
                        results[f"error_{keyword}"] = f"HTTP {resp.status_code}"
                except Exception as exc:
                    logger.warning(
                        "CyberSentinel: CVE query for %s failed: %s", keyword, exc
                    )
                    results[f"error_{keyword}"] = str(exc)

        return results

    async def _analyze_findings(self, findings: Dict[str, Any]) -> str:
        prompt = (
            f"Analyze these cyber threat intelligence findings and provide "
            f"a prioritized risk assessment with actionable recommendations.\n\n"
            f"Findings: {findings}"
        )
        llm_task = LLMTask(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            classification=ClassificationLevel.CONFIDENTIAL,
            metadata={"agent": self.name},
        )
        result = await llm_router.generate(llm_task)
        return result.text

    @staticmethod
    def _extract_cvss_score(metrics: Dict[str, Any]) -> Optional[float]:
        for version_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            entries = metrics.get(version_key, [])
            if entries:
                cvss_data = entries[0].get("cvssData", {})
                score = cvss_data.get("baseScore")
                if score is not None:
                    return float(score)
        return None

    @staticmethod
    def _extract_description(cve: Dict[str, Any]) -> str:
        descriptions = cve.get("descriptions", [])
        for desc in descriptions:
            if desc.get("lang") == "en":
                return desc.get("value", "")
        if descriptions:
            return descriptions[0].get("value", "")
        return ""


cyber_sentinel_agent = CyberSentinelAgent()


__all__ = ["CyberSentinelAgent", "cyber_sentinel_agent"]
