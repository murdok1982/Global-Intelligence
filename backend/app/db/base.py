from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models here so Alembic autogenerate can detect them
from app.models.user import User  # noqa: F401, E402
from app.models.geography import Continent, Country, CountryProfile  # noqa: F401, E402
from app.models.intelligence import IntelligenceCategory, IntelligenceItem, SourceRegistry  # noqa: F401, E402
from app.models.reports import DailyReport, PremiumReport, ReportCitation  # noqa: F401, E402
from app.models.interactions import ChatSession, ChatMessage, ScenarioRun, ContributorSubmission  # noqa: F401, E402
from app.models.auth import MFARecoveryCode, WebAuthnCredential  # noqa: F401, E402
from app.models.audit import AuditEvent  # noqa: F401, E402
