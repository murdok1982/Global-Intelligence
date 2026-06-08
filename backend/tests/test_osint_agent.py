"""
Tests for OSINT Agent — verifies all 10 providers are wired.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.agents.osint import OSINTAgent, _default_providers
from app.agents.base import AgentTask
from app.agents.providers.osint import (
    GDELTProvider,
    RSSProvider,
    YouTubeProvider,
    NewsAPIProvider,
    SIPRIProvider,
    ACLEDProvider,
    FININTProvider,
    GEOINTProvider,
    SIGINTProvider,
    CYBINTProvider,
    OSINTSignal,
)
from app.core.classification import ClassificationLevel, TLP
from datetime import datetime, timezone


class TestOSINTAgentProviders:
    """Test OSINT Agent initializes all providers."""

    def test_default_providers_count(self):
        """Verify default providers list has 9 always-on providers."""
        providers = _default_providers()
        # 9 always-on + NewsAPI only if key is set
        assert len(providers) >= 9

    def test_default_providers_types(self):
        """Verify all expected provider types are present."""
        providers = _default_providers()
        provider_types = {type(p).__name__ for p in providers}
        
        expected = {
            "GDELTProvider",
            "RSSProvider", 
            "YouTubeProvider",
            "SIPRIProvider",
            "ACLEDProvider",
            "FININTProvider",
            "GEOINTProvider",
            "SIGINTProvider",
            "CYBINTProvider",
        }
        
        assert expected.issubset(provider_types), f"Missing providers: {expected - provider_types}"

    def test_custom_providers_override(self):
        """Verify OSINTAgent accepts custom provider list."""
        custom_providers = [GDELTProvider(), RSSProvider()]
        agent = OSINTAgent(providers=custom_providers)
        
        assert len(agent.providers) == 2
        assert all(isinstance(p, (GDELTProvider, RSSProvider)) for p in agent.providers)


class TestOSINTAgentExecution:
    """Test OSINT Agent execution with all providers."""

    @pytest.mark.asyncio
    async def test_execute_calls_all_providers(self):
        """Verify execute() calls all configured providers."""
        mock_signal = OSINTSignal(
            country="US",
            category="defense",
            title="Test Signal",
            url="https://example.com/test",
            summary="Test summary",
            source_name="Test Source",
            published_at=datetime.now(timezone.utc),
            language="en",
            admiralty_reliability="A",
            admiralty_credibility=1,
            confidence_score=0.9,
        )
        
        mock_providers = [
            AsyncMock(execute=AsyncMock(return_value=[mock_signal])),
            AsyncMock(execute=AsyncMock(return_value=[mock_signal])),
            AsyncMock(execute=AsyncMock(return_value=[mock_signal])),
        ]
        
        agent = OSINTAgent(providers=mock_providers)
        
        task = AgentTask(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            payload={"country_iso": "US", "days_back": 7, "limit": 25},
        )
        
        result = await agent.execute(task)
        
        # Verify all providers were called
        for provider in mock_providers:
            provider.execute.assert_called_once()
        
        # Verify result structure
        assert result.kind == "osint_scan"
        assert result.classification == ClassificationLevel.PUBLIC
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_execute_handles_provider_failure(self):
        """Verify execute() handles provider failures gracefully."""
        mock_signal = OSINTSignal(
            country="US",
            category="defense",
            title="Test Signal",
            url="https://example.com/test",
            summary="Test summary",
            source_name="Test Source",
            published_at=datetime.now(timezone.utc),
            language="en",
            admiralty_reliability="A",
            admiralty_credibility=1,
            confidence_score=0.9,
        )
        
        working_provider = AsyncMock(execute=AsyncMock(return_value=[mock_signal]))
        failing_provider = AsyncMock(execute=AsyncMock(side_effect=Exception("Provider failed")))
        
        agent = OSINTAgent(providers=[working_provider, failing_provider])
        
        task = AgentTask(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            payload={"country_iso": "US"},
        )
        
        result = await agent.execute(task)
        
        # Should still return results from working provider
        assert result.kind == "osint_scan"
        assert len(result.content) > 0

    @pytest.mark.asyncio
    async def test_execute_rejects_non_public_classification(self):
        """Verify execute() rejects classification above PUBLIC."""
        agent = OSINTAgent()
        
        task = AgentTask(
            kind="osint_scan",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            payload={"country_iso": "US"},
        )
        
        result = await agent.execute(task)
        
        assert result.kind == "osint_scan"
        assert result.content == []
        assert result.metadata.get("error") == "classification_above_public"


class TestProviderIntegration:
    """Test that all provider types can be instantiated."""

    def test_instantiate_all_providers(self):
        """Verify all provider classes can be instantiated."""
        providers = [
            GDELTProvider(),
            RSSProvider(),
            YouTubeProvider(),
            SIPRIProvider(),
            ACLEDProvider(),
            FININTProvider(),
            GEOINTProvider(),
            SIGINTProvider(),
            CYBINTProvider(),
        ]
        
        assert len(providers) == 9
        
        # Verify each has required attributes
        for provider in providers:
            assert hasattr(provider, 'name')
            assert hasattr(provider, 'execute')
            assert callable(provider.execute)

    def test_provider_names_unique(self):
        """Verify all providers have unique names."""
        providers = [
            GDELTProvider(),
            RSSProvider(),
            YouTubeProvider(),
            SIPRIProvider(),
            ACLEDProvider(),
            FININTProvider(),
            GEOINTProvider(),
            SIGINTProvider(),
            CYBINTProvider(),
        ]
        
        names = [p.name for p in providers]
        assert len(names) == len(set(names)), f"Duplicate provider names: {names}"
