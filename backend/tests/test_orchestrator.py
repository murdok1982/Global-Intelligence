"""
Tests for the OpenClaw Orchestrator — verifies all 8 agents are wired.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.orchestrator import OpenClawOrchestrator
from app.agents.base import AgentResult
from app.core.classification import ClassificationLevel, TLP


@pytest.fixture
def orchestrator():
    """Create orchestrator instance."""
    return OpenClawOrchestrator()


class TestOrchestratorInitialization:
    """Test orchestrator initializes all 8 agents."""

    def test_has_all_agents(self, orchestrator):
        """Verify orchestrator has references to all 8 agents."""
        agents = orchestrator.agents
        assert len(agents) == 8
        assert "osint" in agents
        assert "synthesis" in agents
        assert "scenario" in agents
        assert "eagle_eye" in agents
        assert "money_trail" in agents
        assert "cyber_sentinel" in agents
        assert "narrative_watch" in agents
        assert "early_warning" in agents

    def test_agents_are_not_none(self, orchestrator):
        """Verify all agent references are instantiated."""
        for name, agent in orchestrator.agents.items():
            assert agent is not None, f"Agent {name} is None"


class TestOrchestratorDispatch:
    """Test orchestrator dispatch methods."""

    @pytest.mark.asyncio
    async def test_dispatch_osint_scan(self, orchestrator):
        """Test OSINT scan dispatch."""
        mock_result = AgentResult(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content=[],
            metadata={"providers": {"gdelt": 5, "rss": 10}},
        )
        
        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_osint_scan(
                "US",
                classification=ClassificationLevel.PUBLIC,
            )
            
            assert result.kind == "osint_scan"
            assert result.classification == ClassificationLevel.PUBLIC

    @pytest.mark.asyncio
    async def test_dispatch_geoint_analysis(self, orchestrator):
        """Test GEOINT analysis dispatch (EagleEye agent)."""
        mock_result = AgentResult(
            kind="geoint_analysis",
            classification=ClassificationLevel.RESTRICTED,
            tlp=TLP.AMBER,
            content={"satellite_products": []},
            metadata={},
        )
        
        with patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_geoint_analysis(
                "UA",
                classification=ClassificationLevel.RESTRICTED,
            )
            
            assert result.kind == "geoint_analysis"

    @pytest.mark.asyncio
    async def test_dispatch_financial_intel(self, orchestrator):
        """Test financial intelligence dispatch (MoneyTrail agent)."""
        mock_result = AgentResult(
            kind="financial_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content={"sanctions": [], "commodities": {}},
            metadata={},
        )
        
        with patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_financial_intel(
                entity_name="Test Entity",
                country_iso="RU",
                classification=ClassificationLevel.CONFIDENTIAL,
            )
            
            assert result.kind == "financial_intelligence"

    @pytest.mark.asyncio
    async def test_dispatch_cyber_intel(self, orchestrator):
        """Test cyber intelligence dispatch (CyberSentinel agent)."""
        mock_result = AgentResult(
            kind="cyber_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content={"shodan": {}, "greynoise": {}},
            metadata={},
        )
        
        with patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_cyber_intel(
                target_ip="1.2.3.4",
                classification=ClassificationLevel.CONFIDENTIAL,
            )
            
            assert result.kind == "cyber_intelligence"

    @pytest.mark.asyncio
    async def test_dispatch_narrative_analysis(self, orchestrator):
        """Test narrative analysis dispatch (NarrativeWatch agent)."""
        mock_result = AgentResult(
            kind="narrative_analysis",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={"narratives": []},
            metadata={},
        )
        
        with patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_narrative_analysis(
                country_iso="CN",
                topic="trade",
                classification=ClassificationLevel.PUBLIC,
            )
            
            assert result.kind == "narrative_analysis"

    @pytest.mark.asyncio
    async def test_dispatch_early_warning(self, orchestrator):
        """Test early warning dispatch (EarlyWarning agent)."""
        mock_result = AgentResult(
            kind="early_warning",
            classification=ClassificationLevel.SECRET,
            tlp=TLP.RED,
            content={"risk_score": 75, "risk_level": "HIGH"},
            metadata={},
        )
        
        with patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=mock_result):
            result = await orchestrator.dispatch_early_warning(
                country_iso="KP",
                classification=ClassificationLevel.SECRET,
            )
            
            assert result.kind == "early_warning"

    @pytest.mark.asyncio
    async def test_dispatch_full_analysis(self, orchestrator):
        """Test full analysis dispatches to all 6 collection agents + early warning."""
        mock_result = AgentResult(
            kind="test",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={},
            metadata={},
        )
        
        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=mock_result):
            
            results = await orchestrator.dispatch_full_analysis(
                "RU",
                classification=ClassificationLevel.PUBLIC,
            )
            
            assert "osint" in results
            assert "geoint" in results
            assert "financial" in results
            assert "cyber" in results
            assert "narrative" in results
            assert "early_warning" in results
            assert len(results) == 6


class TestOrchestratorClassificationEnforcement:
    """Test orchestrator enforces classification requirements."""

    def test_requires_classification(self, orchestrator):
        """Verify orchestrator rejects None classification."""
        with pytest.raises(ValueError, match="requires an explicit classification"):
            orchestrator._require_classification(None)

    def test_accepts_valid_classification(self, orchestrator):
        """Verify orchestrator accepts valid classification levels."""
        assert orchestrator._require_classification(ClassificationLevel.PUBLIC) == ClassificationLevel.PUBLIC
        assert orchestrator._require_classification(ClassificationLevel.RESTRICTED) == ClassificationLevel.RESTRICTED
        assert orchestrator._require_classification(ClassificationLevel.CONFIDENTIAL) == ClassificationLevel.CONFIDENTIAL
        assert orchestrator._require_classification(ClassificationLevel.SECRET) == ClassificationLevel.SECRET
