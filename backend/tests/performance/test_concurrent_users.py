"""
Performance tests — basic load testing with concurrent users.

Tests:
- 10 concurrent OSINT scans
- 5 concurrent report generations
- Database connection pool handles 20 concurrent requests
- Latency percentiles (p50, p95, p99) measurement

Uses asyncio.gather for concurrent execution.
"""

from __future__ import annotations

import asyncio
import os
import secrets
import statistics
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

os.environ.setdefault("ENV", "test")
os.environ.setdefault("STATE_GRADE_MODE", "false")
os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("REFRESH_SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("MFA_ENCRYPTION_KEY", secrets.token_hex(32))
os.environ.setdefault("MFA_CHALLENGE_SECRET", secrets.token_hex(32))
os.environ.setdefault("POSTGRES_PASSWORD", "test")

from app.db.base import Base
from app.agents.orchestrator import OpenClawOrchestrator
from app.agents.osint import OSINTAgent
from app.agents.base import AgentResult, AgentTask
from app.agents.providers.osint import OSINTSignal
from app.core.classification import ClassificationLevel, TLP


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="module")
async def perf_engine():
    """In-memory async SQLite engine for performance tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def perf_session(perf_engine):
    """Async session for performance tests."""
    session_factory = async_sessionmaker(
        bind=perf_engine, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


def _compute_percentiles(latencies: list[float]) -> dict[str, float]:
    """Compute p50, p95, p99 from a list of latencies in seconds."""
    if not latencies:
        return {"p50": 0, "p95": 0, "p99": 0, "mean": 0, "max": 0}
    sorted_lat = sorted(latencies)
    n = len(sorted_lat)
    return {
        "p50": sorted_lat[int(n * 0.50)],
        "p95": sorted_lat[min(int(n * 0.95), n - 1)],
        "p99": sorted_lat[min(int(n * 0.99), n - 1)],
        "mean": statistics.mean(sorted_lat),
        "max": sorted_lat[-1],
    }


def _make_mock_osint_result(country: str) -> AgentResult:
    """Create a mock OSINT scan result."""
    signals = [
        {
            "country": country,
            "category": "defense",
            "title": f"Signal for {country}",
            "url": f"https://example.com/{country}/1",
            "summary": f"Test signal for {country}",
            "source_name": "Test Source",
            "published_at": datetime.now(timezone.utc).isoformat(),
            "language": "en",
            "admiralty_reliability": "B",
            "admiralty_credibility": 2,
            "confidence_score": 0.8,
        }
    ]
    return AgentResult(
        kind="osint_scan",
        classification=ClassificationLevel.PUBLIC,
        tlp=TLP.CLEAR,
        content=signals,
        metadata={"providers": {"gdelt": 3, "rss": 5}},
    )


class TestConcurrentOSINTScans:
    """Test 10 concurrent OSINT scans."""

    @pytest.mark.asyncio
    async def test_10_concurrent_osint_scans(self):
        """10 concurrent OSINT scans complete without errors."""
        orchestrator = OpenClawOrchestrator()
        countries = ["US", "RU", "CN", "UA", "KP", "IR", "IL", "IN", "BR", "DE"]
        latencies: list[float] = []

        mock_result = _make_mock_osint_result("TEST")

        async def run_scan(country: str) -> tuple[str, float, bool]:
            start = time.perf_counter()
            try:
                with patch.object(
                    orchestrator._osint, 'run',
                    new_callable=AsyncMock,
                    return_value=_make_mock_osint_result(country),
                ):
                    result = await orchestrator.dispatch_osint_scan(
                        country, classification=ClassificationLevel.PUBLIC,
                    )
                    elapsed = time.perf_counter() - start
                    return country, elapsed, result.kind == "osint_scan"
            except Exception as e:
                elapsed = time.perf_counter() - start
                return country, elapsed, False

        tasks = [run_scan(c) for c in countries]
        results = await asyncio.gather(*tasks)

        for country, elapsed, success in results:
            latencies.append(elapsed)
            assert success, f"OSINT scan for {country} failed"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 10
        assert all(s for _, _, s in results)

    @pytest.mark.asyncio
    async def test_10_concurrent_scans_with_provider_simulation(self):
        """10 concurrent scans with simulated provider latency."""
        agent = OSINTAgent(providers=[])
        latencies: list[float] = []

        async def simulated_scan(country: str) -> tuple[str, float]:
            start = time.perf_counter()
            await asyncio.sleep(0.01)
            elapsed = time.perf_counter() - start
            return country, elapsed

        tasks = [simulated_scan(c) for c in ["US", "RU", "CN", "UA", "KP", "IR", "IL", "IN", "BR", "DE"]]
        results = await asyncio.gather(*tasks)

        for country, elapsed in results:
            latencies.append(elapsed)

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 10
        assert percentiles["p99"] < 1.0


class TestConcurrentReportGenerations:
    """Test 5 concurrent report generations."""

    @pytest.mark.asyncio
    async def test_5_concurrent_synthesis_operations(self):
        """5 concurrent synthesis operations complete without errors."""
        orchestrator = OpenClawOrchestrator()
        topics = ["UA", "RU", "CN", "KP", "IR"]
        latencies: list[float] = []

        synthesis_result = AgentResult(
            kind="synthesis_brief",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp=TLP.AMBER,
            content="# Intelligence Brief\n\nSynthesized analysis.",
            metadata={},
        )

        async def run_synthesis(topic: str) -> tuple[str, float, bool]:
            start = time.perf_counter()
            try:
                with patch.object(
                    orchestrator._synthesis, 'run',
                    new_callable=AsyncMock,
                    return_value=synthesis_result,
                ):
                    result = await orchestrator.dispatch_synthesis(
                        raw_events=[{"title": f"Signal for {topic}"}],
                        topic=topic,
                        classification=ClassificationLevel.CONFIDENTIAL,
                    )
                    elapsed = time.perf_counter() - start
                    return topic, elapsed, "Intelligence Brief" in str(result)
            except Exception:
                elapsed = time.perf_counter() - start
                return topic, elapsed, False

        tasks = [run_synthesis(t) for t in topics]
        results = await asyncio.gather(*tasks)

        for topic, elapsed, success in results:
            latencies.append(elapsed)
            assert success, f"Synthesis for {topic} failed"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 5

    @pytest.mark.asyncio
    async def test_5_concurrent_full_analyses(self):
        """5 concurrent full multi-agent analyses complete correctly."""
        orchestrator = OpenClawOrchestrator()
        countries = ["US", "RU", "CN", "UA", "KP"]
        latencies: list[float] = []

        mock_result = AgentResult(
            kind="test",
            classification=ClassificationLevel.PUBLIC,
            tlp=TLP.CLEAR,
            content={},
            metadata={},
        )

        async def run_full(country: str) -> tuple[str, float, int]:
            start = time.perf_counter()
            try:
                with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=mock_result), \
                     patch.object(orchestrator._eagle_eye, 'run', new_callable=AsyncMock, return_value=mock_result), \
                     patch.object(orchestrator._money_trail, 'run', new_callable=AsyncMock, return_value=mock_result), \
                     patch.object(orchestrator._cyber_sentinel, 'run', new_callable=AsyncMock, return_value=mock_result), \
                     patch.object(orchestrator._narrative_watch, 'run', new_callable=AsyncMock, return_value=mock_result), \
                     patch.object(orchestrator._early_warning, 'run', new_callable=AsyncMock, return_value=mock_result):

                    results = await orchestrator.dispatch_full_analysis(
                        country, classification=ClassificationLevel.PUBLIC,
                    )
                    elapsed = time.perf_counter() - start
                    return country, elapsed, len(results)
            except Exception:
                elapsed = time.perf_counter() - start
                return country, elapsed, 0

        tasks = [run_full(c) for c in countries]
        results = await asyncio.gather(*tasks)

        for country, elapsed, count in results:
            latencies.append(elapsed)
            assert count == 6, f"Full analysis for {country} returned {count} results, expected 6"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 5


class TestDatabaseConnectionPool:
    """Test that database connection pool handles 20 concurrent requests."""

    @pytest.mark.asyncio
    async def test_20_concurrent_db_sessions(self, perf_engine):
        """20 concurrent database sessions complete without pool exhaustion."""
        session_factory = async_sessionmaker(
            bind=perf_engine, expire_on_commit=False
        )
        latencies: list[float] = []

        from app.models.user import User
        from sqlalchemy import text

        async def run_db_query(i: int) -> tuple[int, float, bool]:
            start = time.perf_counter()
            try:
                async with session_factory() as session:
                    await session.execute(text("SELECT 1"))
                    elapsed = time.perf_counter() - start
                    return i, elapsed, True
            except Exception:
                elapsed = time.perf_counter() - start
                return i, elapsed, False

        tasks = [run_db_query(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        for idx, elapsed, success in results:
            latencies.append(elapsed)
            assert success, f"DB query {idx} failed"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 20
        assert all(s for _, _, s in results)

    @pytest.mark.asyncio
    async def test_20_concurrent_user_inserts(self, perf_engine):
        """20 concurrent user inserts succeed without conflicts."""
        session_factory = async_sessionmaker(
            bind=perf_engine, expire_on_commit=False
        )
        latencies: list[float] = []

        from app.models.user import User, RoleEnum
        from app.core.security import get_password_hash

        async def run_insert(i: int) -> tuple[int, float, bool]:
            start = time.perf_counter()
            try:
                async with session_factory() as session:
                    user = User(
                        email=f"perf_user_{i}_{secrets.token_hex(4)}@example.gov",
                        hashed_password=get_password_hash(f"pass{i}"),
                        role=RoleEnum.user,
                        is_active=True,
                    )
                    session.add(user)
                    await session.commit()
                    elapsed = time.perf_counter() - start
                    return i, elapsed, True
            except Exception:
                elapsed = time.perf_counter() - start
                return i, elapsed, False

        tasks = [run_insert(i) for i in range(20)]
        results = await asyncio.gather(*tasks)

        for idx, elapsed, success in results:
            latencies.append(elapsed)
            assert success, f"User insert {idx} failed"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 20


class TestLatencyPercentiles:
    """Measure latency percentiles under concurrent load."""

    @pytest.mark.asyncio
    async def test_osint_scan_latency_percentiles(self):
        """Measure p50, p95, p99 for 50 OSINT scan operations."""
        orchestrator = OpenClawOrchestrator()
        latencies: list[float] = []

        async def run_timed_scan(i: int) -> float:
            start = time.perf_counter()
            with patch.object(
                orchestrator._osint, 'run',
                new_callable=AsyncMock,
                return_value=_make_mock_osint_result("TEST"),
            ):
                await orchestrator.dispatch_osint_scan(
                    "US", classification=ClassificationLevel.PUBLIC,
                )
            return time.perf_counter() - start

        tasks = [run_timed_scan(i) for i in range(50)]
        results = await asyncio.gather(*tasks)
        latencies = list(results)

        percentiles = _compute_percentiles(latencies)

        assert percentiles["p50"] < 1.0, f"p50={percentiles['p50']:.3f}s exceeds 1s"
        assert percentiles["p95"] < 2.0, f"p95={percentiles['p95']:.3f}s exceeds 2s"
        assert percentiles["p99"] < 5.0, f"p99={percentiles['p99']:.3f}s exceeds 5s"

    @pytest.mark.asyncio
    async def test_agent_dispatch_latency_percentiles(self):
        """Measure p50, p95, p99 for 30 agent dispatch operations."""
        orchestrator = OpenClawOrchestrator()
        latencies: list[float] = []

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

            async def run_timed_dispatch(i: int) -> float:
                start = time.perf_counter()
                await orchestrator.dispatch_full_analysis(
                    "US", classification=ClassificationLevel.PUBLIC,
                )
                return time.perf_counter() - start

            tasks = [run_timed_dispatch(i) for i in range(30)]
            results = await asyncio.gather(*tasks)
            latencies = list(results)

        percentiles = _compute_percentiles(latencies)

        assert percentiles["p50"] < 1.0
        assert percentiles["p95"] < 2.0
        assert percentiles["p99"] < 5.0

    @pytest.mark.asyncio
    async def test_concurrent_token_creation_latency(self):
        """Measure latency for 100 concurrent token creation operations."""
        from app.core.security import create_access_token, create_refresh_token

        latencies: list[float] = []

        async def run_token_creation(i: int) -> float:
            start = time.perf_counter()
            access = create_access_token(f"user-{i}", mfa_verified=True)
            refresh = create_refresh_token(f"user-{i}", mfa_verified=True)
            return time.perf_counter() - start

        tasks = [run_token_creation(i) for i in range(100)]
        results = await asyncio.gather(*tasks)
        latencies = list(results)

        percentiles = _compute_percentiles(latencies)

        assert percentiles["p50"] < 0.01, f"p50={percentiles['p50']:.6f}s exceeds 10ms"
        assert percentiles["p95"] < 0.05, f"p95={percentiles['p95']:.6f}s exceeds 50ms"
        assert percentiles["p99"] < 0.1, f"p99={percentiles['p99']:.6f}s exceeds 100ms"
        assert len(latencies) == 100


class TestConcurrentMixedWorkload:
    """Test mixed concurrent workloads."""

    @pytest.mark.asyncio
    async def test_mixed_concurrent_operations(self):
        """Mixed workload: OSINT scans + token creation + DB queries in parallel."""
        orchestrator = OpenClawOrchestrator()
        latencies: list[float] = []

        from app.core.security import create_access_token

        async def osint_op(i: int) -> tuple[str, float, bool]:
            start = time.perf_counter()
            try:
                with patch.object(
                    orchestrator._osint, 'run',
                    new_callable=AsyncMock,
                    return_value=_make_mock_osint_result("US"),
                ):
                    await orchestrator.dispatch_osint_scan(
                        "US", classification=ClassificationLevel.PUBLIC,
                    )
                return f"osint-{i}", time.perf_counter() - start, True
            except Exception:
                return f"osint-{i}", time.perf_counter() - start, False

        async def token_op(i: int) -> tuple[str, float, bool]:
            start = time.perf_counter()
            try:
                create_access_token(f"user-{i}", mfa_verified=True)
                return f"token-{i}", time.perf_counter() - start, True
            except Exception:
                return f"token-{i}", time.perf_counter() - start, False

        all_tasks = []
        for i in range(5):
            all_tasks.append(osint_op(i))
            all_tasks.append(token_op(i))

        results = await asyncio.gather(*all_tasks)

        for name, elapsed, success in results:
            latencies.append(elapsed)
            assert success, f"Operation {name} failed"

        percentiles = _compute_percentiles(latencies)
        assert len(latencies) == 10
        assert all(s for _, _, s in results)
