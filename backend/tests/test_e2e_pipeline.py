"""
End-to-end pipeline tests — verifies the complete intelligence workflow.

Tests the full flow:
1. OSINT collection (9 providers)
2. Multi-agent analysis (8 agents)
3. Synthesis and reporting
4. Classification enforcement
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from app.agents.orchestrator import OpenClawOrchestrator
from app.agents.osint import OSINTAgent
from app.agents.synthesis import SynthesisAgent
from app.agents.base import AgentResult, AgentTask
from app.agents.providers.osint import OSINTSignal
from app.core.classification import ClassificationLevel, TLP


class TestEndToEndPipeline:
    """Test complete intelligence pipeline from collection to synthesis."""

    @pytest.fixture
    def mock_osint_signals(self):
        """Create mock OSINT signals for testing."""
        return [
            OSINTSignal(
                country="UA",
                category="defense",
                title="Military exercise near border",
                url="https://example.com/1",
                summary="Troop movements detected",
                source_name="Jane's",
                published_at=datetime.now(timezone.utc),
                language="en",
                admiralty_reliability="A",
                admiralty_credibility=1,
                confidence_score=0.9,
            ),
            OSINTSignal(
                country="UA",
                category="security",
                title="Cyber attack on infrastructure",
                url="https://example.com/2",
                summary="Power grid targeted",
                source_name="CISA",
                published_at=datetime.now(timezone.utc),
                language="en",
                admiralty_reliability="A",
                admiralty_credibility=1,
                confidence_score=0.85,
            ),
        ]

    @pytest.mark.asyncio
    async def test_full_intelligence_cycle(self, mock_osint_signals):
        """Test complete cycle: collection → analysis → synthesis."""
        orchestrator = OpenClawOrchestrator()
        
        # Mock all agent responses
        osint_result = AgentResult(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content=[vars(s) for s in mock_osint_signals],
            metadata={"providers": {"gdelt": 5, "rss": 10}},
        )
        
        geoint_result = AgentResult(
            kind="geoint_analysis",
            classification=ClassificationLevel.RESTRICTED,
            tlp=TLP.AMBER,
            content={"satellite_products": [{"type": "sentinel2", "coverage": "90%"}]},
            metadata={},
        )
        
        financial_result = AgentResult(
            kind="financial_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content={"sanctions": [], "commodities": {"oil_brent": {"price": 85.5}}},
            metadata={},
        )
        
        cyber_result = AgentResult(
            kind="cyber_intelligence",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content={"threats": [{"type": "apt", "origin": "unknown"}]},
            metadata={},
        )
        
        narrative_result = AgentResult(
            kind="narrative_analysis",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={"narratives": ["escalation", "defense"]},
            metadata={},
        )
        
        warning_result = AgentResult(
            kind="early_warning",
            classification=ClassificationLevel.SECRET,
            tlp=TLP.RED,
            content={"risk_score": 78, "risk_level": "HIGH"},
            metadata={},
        )
        
        synthesis_result = AgentResult(
            kind="synthesis_brief",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content="# Intelligence Brief\n\n## Key Findings\n- High risk detected",
            metadata={},
        )
        
        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=osint_result), \
             patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=geoint_result), \
             patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=financial_result), \
             patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=cyber_result), \
             patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=narrative_result), \
             patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=warning_result), \
             patch.object(orchestrator._synthesis, 'run', new_callable=AsyncMock, return_value=synthesis_result):
            
            # Step 1: Full multi-agent analysis
            analysis_results = await orchestrator.dispatch_full_analysis(
                "UA",
                classification=ClassificationLevel.PUBLIC,
            )
            
            assert len(analysis_results) == 6
            assert analysis_results["early_warning"].content["risk_level"] == "HIGH"
            
            # Step 2: Synthesis
            synthesis = await orchestrator.dispatch_synthesis(
                raw_events=osint_result.content,
                topic="UA",
                classification=ClassificationLevel.CONFIDENTIAL,
            )
            
            assert "Intelligence Brief" in synthesis

    @pytest.mark.asyncio
    async def test_classification_propagation(self):
        """Test that classification is properly enforced through the pipeline."""
        orchestrator = OpenClawOrchestrator()
        
        # Test PUBLIC classification
        result = await orchestrator.dispatch_osint_scan(
            "US",
            classification=ClassificationLevel.PUBLIC,
        )
        # OSINT agent should enforce PUBLIC max
        assert result.classification == ClassificationLevel.PUBLIC
        
        # Test that CONFIDENTIAL+ requires local LLM (state-grade mode)
        # This is tested in test_classification_gate.py but we verify the orchestrator passes it through

    @pytest.mark.asyncio
    async def test_provider_failure_resilience(self):
        """Test that pipeline continues even when some providers fail."""
        agent = OSINTAgent()
        
        # Mock some providers to fail
        with patch.object(agent.providers[0], 'execute', side_effect=Exception("Provider 1 failed")), \
             patch.object(agent.providers[1], 'execute', return_value=[]), \
             patch.object(agent.providers[2], 'execute', return_value=[]):
            
            task = AgentTask(
                kind="osint_scan",
                classification=ClassificationLevel.PUBLIC,
                tlp=TLP.CLEAR,
                payload={"country_iso": "US"},
            )
            
            result = await agent.execute(task)
            
            # Should not crash, should return empty or partial results
            assert result.kind == "osint_scan"


class TestMultiAgentCoordination:
    """Test coordination between multiple agents."""

    @pytest.mark.asyncio
    async def test_parallel_agent_execution(self):
        """Test that multiple agents can run in parallel."""
        orchestrator = OpenClawOrchestrator()
        
        mock_result = AgentResult(
            kind="test",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={},
            metadata={},
        )
        
        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=mock_result) as osint_mock, \
             patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=mock_result) as geoint_mock, \
             patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=mock_result) as financial_mock, \
             patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=mock_result) as cyber_mock, \
             patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=mock_result) as narrative_mock, \
             patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=mock_result) as warning_mock:
            
            results = await orchestrator.dispatch_full_analysis(
                "CN",
                classification=ClassificationLevel.PUBLIC,
            )
            
            # All agents should have been called
            osint_mock.assert_called_once()
            geoint_mock.assert_called_once()
            financial_mock.assert_called_once()
            cyber_mock.assert_called_once()
            narrative_mock.assert_called_once()
            warning_mock.assert_called_once()
            
            assert len(results) == 6

    @pytest.mark.asyncio
    async def test_agent_error_isolation(self):
        """Test that one agent's failure doesn't crash the pipeline."""
        orchestrator = OpenClawOrchestrator()
        
        mock_result = AgentResult(
            kind="test",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={},
            metadata={},
        )
        
        # Make one agent fail
        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, side_effect=Exception("OSINT failed")), \
             patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=mock_result), \
             patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=mock_result):
            
            results = await orchestrator.dispatch_full_analysis(
                "RU",
                classification=ClassificationLevel.PUBLIC,
            )
            
            # Pipeline should continue despite OSINT failure
            assert len(results) == 6
            assert "osint" in results
            assert results["osint"].metadata.get("error") is not None


class TestDataProviderIntegration:
    """Test integration with real data providers (mocked)."""

    @pytest.mark.asyncio
    async def test_osint_provider_diversity(self):
        """Test that OSINT agent uses diverse provider types."""
        agent = OSINTAgent()
        
        provider_categories = {
            "GDELTProvider": "events",
            "RSSProvider": "news",
            "YouTubeProvider": "video",
            "SIPRIProvider": "arms",
            "ACLEDProvider": "conflict",
            "FININTProvider": "financial",
            "GEOINTProvider": "geospatial",
            "SIGINTProvider": "signals",
            "CYBINTProvider": "cyber",
        }
        
        provider_types = {type(p).__name__ for p in agent.providers}
        
        # Verify we have providers from multiple categories
        categories_covered = {
            provider_categories[pt] 
            for pt in provider_types 
            if pt in provider_categories
        }
        
        assert len(categories_covered) >= 5, "OSINT agent should use diverse provider types"
