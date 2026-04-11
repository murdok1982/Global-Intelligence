import os
from pydantic_settings import BaseSettings


def _require(var: str) -> str:
    """Falla en startup si una variable de entorno crítica no está definida."""
    value = os.getenv(var)
    if not value:
        raise ValueError(
            f"Variable de entorno requerida no configurada: {var}. "
            "Consulta .env.example para configurarla."
        )
    return value


class Settings(BaseSettings):
    PROJECT_NAME: str = "Global Intelligence API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security — OBLIGATORIO, sin defaults
    SECRET_KEY: str = os.getenv("SECRET_KEY") or ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # PostgreSQL — defaults solo para desarrollo local
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "global_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_SERVER: str = os.getenv("POSTGRES_SERVER", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "global_intelligence")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # AI OpenRouter
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

    # Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    def validate_secrets(self) -> None:
        """Validar que los secrets críticos están configurados en producción."""
        env = os.getenv("ENV", "development")
        if env == "production":
            _require("SECRET_KEY")
            _require("POSTGRES_PASSWORD")

    class Config:
        case_sensitive = True


settings = Settings()

