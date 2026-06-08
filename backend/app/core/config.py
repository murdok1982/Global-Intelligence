import os
from pydantic import Field
from pydantic_settings import BaseSettings


def _require(var: str) -> str:
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
    ENV: str = Field(default="development")

    CORS_ORIGINS: str = Field(default="http://localhost:3000,http://127.0.0.1:3000")

    # Security
    SECRET_KEY: str = Field(default="")
    REFRESH_SECRET_KEY: str = Field(default="")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL Database
    POSTGRES_USER: str = Field(default="global_user")
    POSTGRES_PASSWORD: str = Field(default="")
    POSTGRES_SERVER: str = Field(default="localhost")
    POSTGRES_PORT: str = Field(default="5432")
    POSTGRES_DB: str = Field(default="global_intelligence")

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: str = Field(default="")

    # ------------------------------------------------------------------
    # LLM providers
    # ------------------------------------------------------------------
    OLLAMA_BASE_URL: str = Field(default="http://ollama:11434")
    OLLAMA_MODEL: str = Field(default="llama3.1:8b-instruct-q4_K_M")
    OLLAMA_TIMEOUT: int = Field(default=120, ge=1)

    VLLM_BASE_URL: str = Field(default="")
    VLLM_MODEL: str = Field(default="meta-llama/Meta-Llama-3.1-8B-Instruct")
    VLLM_TIMEOUT: int = Field(default=120, ge=1)

    OPENROUTER_API_KEY: str = Field(default="")
    ENABLE_OPENROUTER_FALLBACK: bool = Field(default=False)
    OPENROUTER_DEFAULT_MODEL: str = Field(default="anthropic/claude-3-haiku")

    STATE_GRADE_MODE: bool = Field(default=True)

    # ------------------------------------------------------------------
    # MFA / second factor
    # ------------------------------------------------------------------
    MFA_ENCRYPTION_KEY: str = Field(default="")
    MFA_CHALLENGE_SECRET: str = Field(default="")
    MFA_CHALLENGE_TTL_SECONDS: int = Field(default=300, ge=1)
    MFA_RECOVERY_CODES_COUNT: int = Field(default=10, ge=1)
    MFA_ISSUER: str = Field(default="Global Intelligence")

    # ------------------------------------------------------------------
    # Report signing
    # ------------------------------------------------------------------
    SIGNING_PRIVATE_KEY_PATH: str = Field(default="/var/lib/gi/signing/ed25519_private.pem")
    SIGNING_PUBLIC_KEY_PATH: str = Field(default="/var/lib/gi/signing/ed25519_public.pem")

    # ------------------------------------------------------------------
    # OSINT providers
    # ------------------------------------------------------------------
    NEWSAPI_API_KEY: str = Field(default="")
    GDELT_BASE_URL: str = Field(default="https://api.gdeltproject.org/api/v2/doc/doc")
    OSINT_HTTP_TIMEOUT: int = Field(default=30, ge=1)
    OSINT_MAX_PER_SOURCE: int = Field(default=25, ge=1)
    SHODAN_API_KEY: str = Field(default="")
    GREYNOISE_API_KEY: str = Field(default="")
    COPERNICUS_USERNAME: str = Field(default="")
    COPERNICUS_PASSWORD: str = Field(default="")
    MARINETRAFFIC_API_KEY: str = Field(default="")
    ACLED_API_KEY: str = Field(default="")
    ACLED_EMAIL: str = Field(default="")
    TWITTER_BEARER_TOKEN: str = Field(default="")
    TELEGRAM_API_ID: str = Field(default="")
    TELEGRAM_API_HASH: str = Field(default="")

    ALPHA_VANTAGE_API_KEY: str = Field(default="")
    EIA_API_KEY: str = Field(default="")
    WORLDBANK_COMMODITY_URL: str = Field(
        default="https://api.worldbank.org/v2/country/USA/indicator/FP.CPI.TOTL?format=json"
    )
    METALPRICE_API_KEY: str = Field(default="")

    def validate_secrets(self) -> None:
        env = self.ENV
        if env == "production":
            _require("SECRET_KEY")
            _require("POSTGRES_PASSWORD")
        if self.STATE_GRADE_MODE:
            if not self.MFA_ENCRYPTION_KEY:
                raise ValueError(
                    "MFA_ENCRYPTION_KEY is required when STATE_GRADE_MODE=true. "
                    "Generate with: openssl rand -hex 32"
                )
            try:
                key_bytes = bytes.fromhex(self.MFA_ENCRYPTION_KEY)
            except ValueError as exc:
                raise ValueError(
                    "MFA_ENCRYPTION_KEY must be hex-encoded (64 chars)."
                ) from exc
            if len(key_bytes) != 32:
                raise ValueError(
                    "MFA_ENCRYPTION_KEY must decode to 32 bytes (256-bit AES key)."
                )
            if not self.MFA_CHALLENGE_SECRET:
                raise ValueError(
                    "MFA_CHALLENGE_SECRET is required when STATE_GRADE_MODE=true. "
                    "Generate with: openssl rand -hex 32"
                )
            if self.MFA_CHALLENGE_SECRET in (
                self.SECRET_KEY,
                self.REFRESH_SECRET_KEY,
            ):
                raise ValueError(
                    "MFA_CHALLENGE_SECRET must differ from SECRET_KEY "
                    "and REFRESH_SECRET_KEY."
                )

    class Config:
        case_sensitive = True
        env_file = ".env"


settings = Settings()
