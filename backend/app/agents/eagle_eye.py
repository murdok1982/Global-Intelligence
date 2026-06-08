"""
Eagle Eye Agent — satellite imagery analysis for geopolitical intelligence.

Queries the Copernicus Data Space Ecosystem (Sentinel-2) to detect
changes in military infrastructure, troop concentrations, and other
geospatial indicators. Imagery metadata and change-detection results
are enriched through LLM-based analysis before being returned as
structured findings.

All external HTTP calls go through ``httpx`` with bounded timeouts.
Errors are captured and surfaced in the result metadata — the agent
never raises.
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

_SENTINEL_CATALOGUE_URL = (
    "https://catalogue.dataspace.copernicus.eu/odata/v1"
)

_SYSTEM_PROMPT = (
    "You are a geospatial intelligence analyst specializing in satellite "
    "imagery interpretation. Identify military infrastructure changes, "
    "troop movement indicators, and strategic developments. Use precise "
    "coordinates and timestamps. Flag uncertainty explicitly."
)

_HTTP_TIMEOUT = 30.0


class EagleEyeAgent(BaseAgent):
    """Satellite imagery analysis agent powered by Sentinel-2 data."""

    name = "EagleEye-Zeta"
    max_classification = ClassificationLevel.RESTRICTED

    async def execute(self, task: AgentTask) -> AgentResult:
        region: str = task.payload.get("region", "UNKNOWN")
        coordinates: Optional[Dict[str, float]] = task.payload.get("coordinates")
        days_back: int = int(task.payload.get("days_back", 14))
        cloud_cover_max: float = float(task.payload.get("cloud_cover_max", 30.0))

        try:
            products = await self._query_sentinel_catalogue(
                coordinates=coordinates,
                region=region,
                days_back=days_back,
                cloud_cover_max=cloud_cover_max,
            )
        except Exception as exc:
            logger.warning("EagleEye: Sentinel catalogue query failed: %s", exc)
            return AgentResult(
                kind="satellite_analysis",
                classification=ClassificationLevel.RESTRICTED,
                tlp=TLP.GREEN,
                content=[],
                metadata={
                    "error": "sentinel_catalogue_unavailable",
                    "detail": str(exc),
                    "region": region,
                },
            )

        if not products:
            return AgentResult(
                kind="satellite_analysis",
                classification=ClassificationLevel.RESTRICTED,
                tlp=TLP.GREEN,
                content=[],
                metadata={
                    "products_found": 0,
                    "region": region,
                },
            )

        try:
            analysis = await self._analyze_products(products, region)
        except Exception as exc:
            logger.warning("EagleEye: LLM analysis failed: %s", exc)
            return AgentResult(
                kind="satellite_analysis",
                classification=ClassificationLevel.RESTRICTED,
                tlp=TLP.GREEN,
                content=products,
                metadata={
                    "error": "llm_analysis_failed",
                    "detail": str(exc),
                    "products_found": len(products),
                    "region": region,
                },
            )

        return AgentResult(
            kind="satellite_analysis",
            classification=ClassificationLevel.RESTRICTED,
            tlp=TLP.GREEN,
            content=analysis,
            metadata={
                "products_found": len(products),
                "region": region,
                "analysis": "llm_enriched",
            },
        )

    async def _query_sentinel_catalogue(
        self,
        *,
        coordinates: Optional[Dict[str, float]],
        region: str,
        days_back: int,
        cloud_cover_max: float,
    ) -> List[Dict[str, Any]]:
        acquired_after = (
            datetime.now(timezone.utc) - timedelta(days=days_back)
        ).strftime("%Y-%m-%dT%H:%M:%S.000Z")

        filters: list[str] = [
            f"Collection/Name eq 'SENTINEL-2'",
            f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud_cover_max})",
            f"ContentDate/Start gt {acquired_after}",
            "Online eq true",
        ]

        if coordinates:
            lon = coordinates.get("longitude", 0.0)
            lat = coordinates.get("latitude", 0.0)
            wkt = f"POINT({lon} {lat})"
            filters.append(f"OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')")

        query = "&".join(f"$filter={f}" for f in filters)
        url = f"{_SENTINEL_CATALOGUE_URL}/Products?{query}&$top=20&$orderby=ContentDate/Start desc"

        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        products: list[dict[str, Any]] = []
        for item in data.get("value", []):
            products.append({
                "id": item.get("Id"),
                "name": item.get("Name"),
                "acquisition_date": item.get("ContentDate", {}).get("Start"),
                "cloud_cover": self._extract_cloud_cover(item),
                "footprint": item.get("Footprint"),
                "download_url": (
                    f"{_SENTINEL_CATALOGUE_URL}/Products({item.get('Id')})/$value"
                ),
            })
        return products

    @staticmethod
    def _extract_cloud_cover(product: Dict[str, Any]) -> Optional[float]:
        attributes = product.get("Attributes", {}).get("Values", [])
        for attr in attributes:
            if attr.get("Name") == "cloudCover":
                try:
                    return float(attr.get("Value"))
                except (TypeError, ValueError):
                    return None
        return None

    async def _analyze_products(
        self,
        products: List[Dict[str, Any]],
        region: str,
    ) -> Dict[str, Any]:
        prompt = (
            f"Analyze these {len(products)} Sentinel-2 products for the region "
            f"'{region}'. Identify potential military infrastructure changes, "
            f"troop movement indicators, new construction, vehicle concentrations, "
            f"or other strategic developments.\n\n"
            f"Products: {products}"
        )
        llm_task = LLMTask(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            classification=ClassificationLevel.RESTRICTED,
            metadata={"agent": self.name, "region": region},
        )
        result = await llm_router.generate(llm_task)
        return {
            "region": region,
            "product_count": len(products),
            "products": products,
            "analysis": result.text,
            "llm_provider": result.provider,
            "llm_model": result.model,
            "latency_ms": result.latency_ms,
        }


eagle_eye_agent = EagleEyeAgent()


__all__ = ["EagleEyeAgent", "eagle_eye_agent"]
