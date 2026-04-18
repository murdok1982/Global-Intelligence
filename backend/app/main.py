from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.limiter import limiter
from app.core.telemetry import SecurityHeadersMiddleware
from app.api.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for the Global Intelligence OSINT Platform",
    version=settings.VERSION,
    docs_url="/docs" if settings.ENV != "production" else None,
    redoc_url="/redoc" if settings.ENV != "production" else None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Configure CORS
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Mount versioned API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health", tags=["health"])
def read_health():
    return {"status": "healthy", "service": "global-intelligence-api"}
