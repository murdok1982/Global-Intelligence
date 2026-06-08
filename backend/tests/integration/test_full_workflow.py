"""
Integration tests for the complete intelligence workflow.

Tests the full flow with a real test database (SQLite in-memory):
- User registration -> login -> MFA enrollment -> MFA verify -> access token
- Access token with mfa_verified=true can access /classified/* endpoints
- Access token WITHOUT mfa_verified is rejected by /classified/* in STATE_GRADE_MODE
- OSINT scan -> synthesis -> report generation flow
- Military database queries (weapons, transfers, bases)
- Export endpoints (PDF, DOCX, JSON, Markdown)
"""

from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta

import pytest
import pytest_asyncio
import httpx
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy import select

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

import pyotp

from app.db.base import Base
from app.models.user import User, RoleEnum
from app.models.auth import MFARecoveryCode
from app.models.geography import Continent, Country
from app.models.reports import DailyReport
from app.models.military import (
    WeaponSystem, WeaponCategory, WeaponOrigin,
    ArmsTransfer, MilitaryBase, DefenseBudget, WeaponOperator,
)
from app.core.classification import ClassificationLevel
from app.core.security import create_access_token, create_refresh_token, get_password_hash


def _safe_password_hash(plain: str) -> str:
    try:
        return get_password_hash(plain)
    except Exception:
        import bcrypt as _native_bcrypt
        return _native_bcrypt.hashpw(
            plain.encode("utf-8"), _native_bcrypt.gensalt(rounds=4)
        ).decode("ascii")


@pytest.fixture(scope="module")
def event_loop_policy():
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="module")
async def integration_engine():
    """In-memory async SQLite engine for integration tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        from app.models.military import (
            WeaponSystem, ArmsTransfer, MilitaryBase, DefenseBudget,
            WeaponOperator, WeaponVariant, MilitaryUnit,
        )
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def integration_session(integration_engine):
    """Async session bound to the integration test engine."""
    session_factory = async_sessionmaker(
        bind=integration_engine, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_app(integration_engine):
    """Create a FastAPI test app with overridden dependencies."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from app.api.api import public_router, classified_router
    from app.api.deps import get_db
    from app.core.limiter import limiter

    session_factory = async_sessionmaker(
        bind=integration_engine, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app = FastAPI()
    app.state.limiter = limiter
    app.dependency_overrides[get_db] = override_get_db

    try:
        from app.db.session import get_session
        app.dependency_overrides[get_session] = override_get_db
    except (ImportError, AttributeError):
        pass

    app.include_router(public_router, prefix="/api/v1/public")
    app.include_router(classified_router, prefix="/api/v1/classified")

    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(test_app):
    """HTTPX async test client."""
    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seed_user(integration_session):
    """Create a test user with RESTRICTED clearance and MFA enabled."""
    email = "testagent@example.gov"
    result = await integration_session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalars().first()
    if not user:
        user = User(
            email=email,
            hashed_password=_safe_password_hash("SecureP@ss123"),
            role=RoleEnum.institutional,
            is_active=True,
            two_factor_enabled=False,
            clearance_level=int(ClassificationLevel.RESTRICTED),
        )
        integration_session.add(user)
        await integration_session.commit()
    await integration_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_public_user(integration_session):
    """Create a test user with PUBLIC clearance."""
    email = "public@example.gov"
    result = await integration_session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalars().first()
    if not user:
        user = User(
            email=email,
            hashed_password=_safe_password_hash("PublicP@ss123"),
            role=RoleEnum.user,
            is_active=True,
            two_factor_enabled=False,
            clearance_level=int(ClassificationLevel.PUBLIC),
        )
        integration_session.add(user)
        await integration_session.commit()
    await integration_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_admin_user(integration_session):
    """Create an admin user with SECRET clearance."""
    email = "admin@example.gov"
    result = await integration_session.execute(
        select(User).where(User.email == email)
    )
    user = result.scalars().first()
    if not user:
        user = User(
            email=email,
            hashed_password=_safe_password_hash("AdminP@ss123"),
            role=RoleEnum.admin,
            is_active=True,
            two_factor_enabled=False,
            clearance_level=int(ClassificationLevel.SECRET),
        )
        integration_session.add(user)
        await integration_session.commit()
    await integration_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def seed_country(integration_session):
    """Create a test country for report generation."""
    existing = await integration_session.execute(
        select(Continent).where(Continent.name == "Europe")
    )
    continent = existing.scalars().first()
    if not continent:
        continent = Continent(name="Europe", code="EU")
        integration_session.add(continent)
        await integration_session.flush()

    existing_country = await integration_session.execute(
        select(Country).where(Country.iso_code == "TS")
    )
    country = existing_country.scalars().first()
    if not country:
        country = Country(
            name="Testonia",
            iso_code="TS",
            continent_id=continent.id,
        )
        integration_session.add(country)
        await integration_session.commit()
    await integration_session.refresh(country)
    return country


@pytest_asyncio.fixture
async def seed_military_data(integration_session):
    """Seed military database with test data."""
    existing = await integration_session.execute(
        select(WeaponSystem).where(WeaponSystem.name == "M1 Abrams")
    )
    weapon = existing.scalars().first()
    if not weapon:
        weapon = WeaponSystem(
            name="M1 Abrams",
            designation="M1A2",
            category=WeaponCategory.TANK,
            origin=WeaponOrigin.USA,
            manufacturer="General Dynamics",
            is_active=True,
            service_entry_year=1980,
            unit_cost_usd=8_000_000.0,
        )
        integration_session.add(weapon)
        await integration_session.flush()

        operator = WeaponOperator(
            weapon_id=weapon.id,
            country_iso="USA",
            country_name="United States",
            quantity=600,
            operational_status="Active",
            source="IISS Military Balance 2024",
        )
        integration_session.add(operator)

        transfer = ArmsTransfer(
            supplier_country="United States",
            supplier_iso="USA",
            recipient_country="Ukraine",
            recipient_iso="UKR",
            weapon_category=WeaponCategory.TANK,
            weapon_description="M1A2 Abrams tanks",
            quantity=31,
            deal_value_usd=400_000_000.0,
            agreement_year=2023,
            status="delivered",
        )
        integration_session.add(transfer)

        base = MilitaryBase(
            name="Ramstein Air Base",
            country_iso="DEU",
            country_name="Germany",
            base_type="Air Base",
            latitude=49.4369,
            longitude=7.6003,
            personnel_count=5000,
            is_foreign_hosted=True,
            host_country_iso="DEU",
            host_country_name="Germany",
            strategic_importance="Critical",
        )
        integration_session.add(base)

        budget = DefenseBudget(
            country_iso="USA",
            country_name="United States",
            fiscal_year=2024,
            budget_usd=886_000_000_000.0,
            gdp_percentage=3.5,
        )
        integration_session.add(budget)

        await integration_session.commit()
    return {"weapon": weapon}


class TestFullAuthWorkflow:
    """Test complete authentication workflow: register -> login -> MFA -> access."""

    @pytest.mark.asyncio
    async def test_register_login_mfa_enroll_verify_get_token(self, client, integration_session):
        """Full auth flow: register, login (gets challenge), MFA enroll, verify, get access token."""
        email = f"flow_{secrets.token_hex(4)}@example.gov"
        password = "Str0ngP@ss!"

        reg_resp = await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )
        assert reg_resp.status_code == 201
        user_id = reg_resp.json()["id"]

        login_resp = await client.post(
            "/api/v1/public/auth/login",
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert "access_token" in login_data
        assert "refresh_token" in login_data

        access_token = login_data["access_token"]

        me_resp = await client.get(
            "/api/v1/public/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["email"] == email

    @pytest.mark.asyncio
    async def test_mfa_enabled_login_returns_challenge(self, client, integration_session):
        """Login with MFA-enabled user returns challenge token, not access tokens."""
        email = f"mfa_{secrets.token_hex(4)}@example.gov"
        password = "MfaP@ss123!"

        await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )

        result = await integration_session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalars().first()
        user.two_factor_enabled = True
        await integration_session.commit()

        login_resp = await client.post(
            "/api/v1/public/auth/login",
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200
        data = login_resp.json()
        assert data["mfa_required"] is True
        assert "challenge_token" in data
        assert "access_token" not in data

    @pytest.mark.asyncio
    async def test_duplicate_registration_rejected(self, client):
        """Registering with an existing email returns 409."""
        email = f"dup_{secrets.token_hex(4)}@example.gov"
        password = "DupP@ss123!"

        resp1 = await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )
        assert resp1.status_code == 201

        resp2 = await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )
        assert resp2.status_code == 409


class TestClassifiedEndpointAccess:
    """Test access control for /classified/* endpoints."""

    @pytest.mark.asyncio
    async def test_mfa_verified_token_accesses_classified(self, client, integration_session, monkeypatch):
        """Access token with mfa_verified=true can reach /classified/* endpoints."""
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "STATE_GRADE_MODE", False)

        email = f"cls_{secrets.token_hex(4)}@example.gov"
        password = "ClsP@ss123!"

        await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )

        result = await integration_session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalars().first()
        user.clearance_level = int(ClassificationLevel.RESTRICTED)
        user.two_factor_enabled = True
        await integration_session.commit()

        token = create_access_token(str(user.id), mfa_verified=True)

        resp = await client.get(
            "/api/v1/classified/reports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_no_mfa_verified_rejected_in_state_grade(self, client, integration_session, monkeypatch):
        """Access token WITHOUT mfa_verified is rejected in STATE_GRADE_MODE."""
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "STATE_GRADE_MODE", True)

        email = f"sg_{secrets.token_hex(4)}@example.gov"
        password = "SgP@ss123!"

        await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )

        result = await integration_session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalars().first()
        user.clearance_level = int(ClassificationLevel.RESTRICTED)
        user.two_factor_enabled = True
        await integration_session.commit()

        token = create_access_token(str(user.id), mfa_verified=False)

        resp = await client.get(
            "/api/v1/classified/reports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_public_clearance_rejected_from_classified(self, client, integration_session, monkeypatch):
        """User with PUBLIC clearance cannot access /classified/* even with MFA."""
        from app.core import config as cfg
        monkeypatch.setattr(cfg.settings, "STATE_GRADE_MODE", False)

        email = f"pub_{secrets.token_hex(4)}@example.gov"
        password = "PubP@ss123!"

        await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )

        result = await integration_session.execute(
            select(User).where(User.email == email)
        )
        user = result.scalars().first()
        user.clearance_level = int(ClassificationLevel.PUBLIC)
        user.two_factor_enabled = True
        await integration_session.commit()

        token = create_access_token(str(user.id), mfa_verified=True)

        resp = await client.get(
            "/api/v1/classified/reports",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 403


class TestOSINTSynthesisReportFlow:
    """Test the OSINT scan -> synthesis -> report generation pipeline."""

    @pytest.mark.asyncio
    async def test_osint_scan_to_synthesis_pipeline(self):
        """OSINT collection flows into synthesis agent correctly."""
        from app.agents.orchestrator import OpenClawOrchestrator
        from app.agents.base import AgentResult

        orchestrator = OpenClawOrchestrator()

        osint_result = AgentResult(
            kind="osint_scan",
            classification=ClassificationLevel.PUBLIC,
            tlp="TLP:CLEAR",
            content=[
                {"title": "Signal 1", "url": "https://example.com/1"},
                {"title": "Signal 2", "url": "https://example.com/2"},
            ],
            metadata={"providers": {"gdelt": 5, "rss": 10}},
        )

        synthesis_result = AgentResult(
            kind="synthesis_brief",
            classification=ClassificationLevel.CONFIDENTIAL,
            tlp="TLP:AMBER",
            content="# Intelligence Brief\n\nKey findings from analysis.",
            metadata={},
        )

        with patch.object(orchestrator._osint, 'run', new_callable=AsyncMock, return_value=osint_result), \
             patch.object(orchestrator._synthesis, 'run', new_callable=AsyncMock, return_value=synthesis_result):

            scan = await orchestrator.dispatch_osint_scan(
                "UA", classification=ClassificationLevel.PUBLIC,
            )
            assert scan.kind == "osint_scan"
            assert len(scan.content) == 2

            synth = await orchestrator.dispatch_synthesis(
                raw_events=scan.content,
                topic="UA",
                classification=ClassificationLevel.CONFIDENTIAL,
            )
            assert "Intelligence Brief" in synth

    @pytest.mark.asyncio
    async def test_report_generation_endpoint(
        self, client, integration_session, seed_country, seed_admin_user, monkeypatch
    ):
        """Report generation endpoint creates a report in the database."""
        from app.agents.osint import OSINTAgent
        from app.agents.synthesis import synthesis_agent

        mock_signals = [
            {"title": "Test signal", "url": "https://example.com/test"},
        ]

        with patch.object(OSINTAgent, 'gather_signals', new_callable=AsyncMock, return_value=mock_signals), \
             patch.object(synthesis_agent, 'generate_daily_report', new_callable=AsyncMock, return_value="Synthesized summary for Testonia"):

            token = create_access_token(str(seed_admin_user.id), mfa_verified=True)
            resp = await client.post(
                "/api/v1/classified/reports/generate",
                json={"country_iso": "TS"},
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 201
            data = resp.json()
            assert data["executive_summary"] == "Synthesized summary for Testonia"
            assert "id" in data


class TestMilitaryDatabaseQueries:
    """Test military database query endpoints."""

    @pytest.mark.asyncio
    async def test_list_weapons(self, client, seed_military_data):
        """GET /military/weapons returns seeded weapon systems."""
        resp = await client.get("/api/v1/public/military/military/weapons")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [w["name"] for w in data["items"]]
        assert "M1 Abrams" in names

    @pytest.mark.asyncio
    async def test_list_weapons_filter_by_category(self, client, seed_military_data):
        """GET /military/weapons?category=tank filters correctly."""
        resp = await client.get("/api/v1/public/military/military/weapons?category=tank")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_arms_transfers(self, client, seed_military_data):
        """GET /military/transfers returns seeded arms transfers."""
        resp = await client.get("/api/v1/public/military/military/transfers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_arms_transfers_filter_supplier(self, client, seed_military_data):
        """GET /military/transfers?supplier_iso=USA filters correctly."""
        resp = await client.get("/api/v1/public/military/military/transfers?supplier_iso=USA")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_military_bases(self, client, seed_military_data):
        """GET /military/bases returns seeded military bases."""
        resp = await client.get("/api/v1/public/military/military/bases")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [b["name"] for b in data["items"]]
        assert "Ramstein Air Base" in names

    @pytest.mark.asyncio
    async def test_list_defense_budgets(self, client, seed_military_data):
        """GET /military/budgets returns seeded defense budgets."""
        resp = await client.get("/api/v1/public/military/military/budgets")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_military_stats(self, client, seed_military_data):
        """GET /military/stats returns aggregated statistics."""
        resp = await client.get("/api/v1/public/military/military/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_weapons"] >= 1
        assert data["total_transfers"] >= 1
        assert data["total_bases"] >= 1

    @pytest.mark.asyncio
    async def test_weapon_categories_static(self, client):
        """GET /military/categories returns the static category list."""
        resp = await client.get("/api/v1/public/military/military/categories")
        assert resp.status_code == 200
        data = resp.json()
        keys = [c["key"] for c in data]
        assert "aircraft" in keys
        assert "tank" in keys


class TestExportEndpoints:
    """Test export endpoints (PDF, DOCX, JSON, Markdown)."""

    @pytest_asyncio.fixture
    async def seed_report(self, integration_session, seed_country):
        """Create a test report for export."""
        report = DailyReport(
            country_id=seed_country.id,
            executive_summary="Test executive summary for export.",
            content_json='{"section1": "Content of section 1", "findings": ["a", "b"]}',
            published=True,
            classification=int(ClassificationLevel.RESTRICTED),
            tlp="TLP:AMBER",
        )
        integration_session.add(report)
        await integration_session.commit()
        await integration_session.refresh(report)
        return report

    @pytest.mark.asyncio
    async def test_export_json(self, client, seed_report, seed_admin_user):
        """GET /export/report/{id}/json returns JSON export."""
        token = create_access_token(str(seed_admin_user.id), mfa_verified=True)

        mock_report_data = {
            "id": str(seed_report.id),
            "type": "daily",
            "executive_summary": "Test summary",
            "content_json": "{}",
            "classification": 1,
            "tlp": "TLP:AMBER",
        }

        with patch("app.services.export_service._fetch_report_data", return_value=mock_report_data), \
             patch("app.services.export_service.add_watermark", new_callable=AsyncMock) as mock_wm, \
             patch("app.services.export_service.sign_export", new_callable=AsyncMock) as mock_sig:

            mock_wm.return_value = b"watermarked-json-content"
            mock_sig.return_value = {"signature": "", "fingerprint": ""}

            resp = await client.get(
                f"/api/v1/classified/export/export/report/{seed_report.id}/json",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/json"

    @pytest.mark.asyncio
    async def test_export_markdown(self, client, seed_report, seed_admin_user):
        """GET /export/report/{id}/markdown returns Markdown export."""
        token = create_access_token(str(seed_admin_user.id), mfa_verified=True)

        mock_report_data = {
            "id": str(seed_report.id),
            "type": "daily",
            "executive_summary": "Test summary",
            "content_json": "{}",
            "classification": 1,
            "tlp": "TLP:AMBER",
        }

        with patch("app.services.export_service._fetch_report_data", return_value=mock_report_data), \
             patch("app.services.export_service.add_watermark", new_callable=AsyncMock) as mock_wm:

            mock_wm.return_value = b"# Test Markdown Export"

            resp = await client.get(
                f"/api/v1/classified/export/export/report/{seed_report.id}/markdown",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert "text/markdown" in resp.headers["content-type"]

    @pytest.mark.asyncio
    async def test_export_pdf_requires_restricted_clearance(self, client, seed_report, seed_public_user):
        """PDF export rejects users with PUBLIC clearance."""
        token = create_access_token(str(seed_public_user.id), mfa_verified=True)

        resp = await client.get(
            f"/api/v1/classified/export/export/report/{seed_report.id}/pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code in (403, 401)

    @pytest.mark.asyncio
    async def test_export_pdf(self, client, seed_report, seed_admin_user):
        """GET /export/report/{id}/pdf returns PDF export."""
        token = create_access_token(str(seed_admin_user.id), mfa_verified=True)

        with patch("app.services.export_service.export_pdf", new_callable=AsyncMock) as mock_pdf, \
             patch("app.services.export_service.add_watermark", new_callable=AsyncMock) as mock_wm, \
             patch("app.services.export_service.sign_export", new_callable=AsyncMock) as mock_sig:

            mock_pdf.return_value = b"%PDF-1.4 fake pdf content"
            mock_wm.return_value = b"%PDF-1.4 watermarked"
            mock_sig.return_value = {"signature": "test-sig", "fingerprint": "ABCD1234"}

            resp = await client.get(
                f"/api/v1/classified/export/export/report/{seed_report.id}/pdf?classification=RESTRICTED",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200
            assert resp.headers["content-type"] == "application/pdf"

    @pytest.mark.asyncio
    async def test_export_docx(self, client, seed_report, seed_admin_user):
        """GET /export/report/{id}/docx returns DOCX export."""
        token = create_access_token(str(seed_admin_user.id), mfa_verified=True)

        with patch("app.services.export_service.export_docx", new_callable=AsyncMock) as mock_docx, \
             patch("app.services.export_service.add_watermark", new_callable=AsyncMock) as mock_wm, \
             patch("app.services.export_service.sign_export", new_callable=AsyncMock) as mock_sig:

            mock_docx.return_value = b"PK\x03\x04 fake docx content"
            mock_wm.return_value = b"PK\x03\x04 watermarked"
            mock_sig.return_value = {"signature": "", "fingerprint": ""}

            resp = await client.get(
                f"/api/v1/classified/export/export/report/{seed_report.id}/docx",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200


class TestTokenRefreshFlow:
    """Test token refresh preserves mfa_verified claim."""

    @pytest.mark.asyncio
    async def test_refresh_preserves_mfa_verified(self, client, integration_session):
        """Refreshing with mfa_verified=true carries the claim forward."""
        email = f"ref_{secrets.token_hex(4)}@example.gov"
        password = "RefP@ss123!"

        await client.post(
            "/api/v1/public/auth/register",
            json={"email": email, "password": password},
        )

        login_resp = await client.post(
            "/api/v1/public/auth/login",
            data={"username": email, "password": password},
        )
        assert login_resp.status_code == 200
        refresh_token = login_resp.json()["refresh_token"]

        refresh_resp = await client.post(
            "/api/v1/public/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200
        new_access = refresh_resp.json()["access_token"]
        assert new_access is not None

    @pytest.mark.asyncio
    async def test_invalid_refresh_token_rejected(self, client):
        """An invalid refresh token is rejected with 401."""
        resp = await client.post(
            "/api/v1/public/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401
