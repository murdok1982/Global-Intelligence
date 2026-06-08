from fastapi import FastAPI
import hispan_shield_guardian  # noqa: F401
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.api import classified_router, public_router, api_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.limiter import limiter
from app.core.telemetry import SecurityHeadersMiddleware

# Fail closed at startup if state-grade secrets are missing.
settings.validate_secrets()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the Global Intelligence OSINT Platform",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Append-only audit log middleware for the classified scope.
app.add_middleware(AuditMiddleware)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
origins = [
    o.strip()
    for o in settings.CORS_ORIGINS.split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Mount the public scope (no implicit auth) and the classified scope
# (gated by require_mfa_verified_user).
app.include_router(public_router, prefix=f"{settings.API_V1_STR}/public")
app.include_router(classified_router, prefix=f"{settings.API_V1_STR}/classified")

# Legacy aggregate mount — kept while clients migrate.
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
def read_health():
    return {"status": "healthy", "service": "global-intelligence-api"}
