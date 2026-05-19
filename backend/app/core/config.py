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


def _bool_env(var: str, default: bool) -> bool:
    raw = os.getenv(var)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseSettings):
    PROJECT_NAME: str = "Global Intelligence API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = os.getenv("ENV", "development")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # PostgreSQL Database
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
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # ------------------------------------------------------------------
    # LLM providers — see app/services/llm/router.py
    # ------------------------------------------------------------------
    # Primary local provider (sovereign by default).
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b-instruct-q4_K_M")
    OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    # Optional second local provider — empty disables it.
    VLLM_BASE_URL: str = os.getenv("VLLM_BASE_URL", "")
    VLLM_MODEL: str = os.getenv("VLLM_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")
    VLLM_TIMEOUT: int = int(os.getenv("VLLM_TIMEOUT", "120"))

    # External fallback. Allowed ONLY for PUBLIC tasks. Disabled by
    # default in state-grade deployments.
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    ENABLE_OPENROUTER_FALLBACK: bool = _bool_env("ENABLE_OPENROUTER_FALLBACK", False)
    OPENROUTER_DEFAULT_MODEL: str = os.getenv(
        "OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3-haiku"
    )

    # When true, any task with classification >= CONFIDENTIAL is
    # rejected if no local provider is reachable. Default: true.
    STATE_GRADE_MODE: bool = _bool_env("STATE_GRADE_MODE", True)

    # ------------------------------------------------------------------
    # MFA / second factor
    # ------------------------------------------------------------------
    # AES-GCM key used to encrypt MFA TOTP secrets at rest. Hex-encoded,
    # 32 bytes (64 hex chars). Generate with `openssl rand -hex 32`.
    # REQUIRED when STATE_GRADE_MODE=true.
    MFA_ENCRYPTION_KEY: str = os.getenv("MFA_ENCRYPTION_KEY", "")
    # Secret used to sign the short-lived MFA challenge token issued by
    # /auth/login when the user has two_factor_enabled=True. Must be
    # distinct from SECRET_KEY / REFRESH_SECRET_KEY so a leak of either
    # cannot mint challenge tokens. Generate with `openssl rand -hex 32`.
    MFA_CHALLENGE_SECRET: str = os.getenv("MFA_CHALLENGE_SECRET", "")
    # TTL of the MFA challenge token (seconds). The user must complete
    # /auth/mfa/verify within this window or re-authenticate.
    MFA_CHALLENGE_TTL_SECONDS: int = int(os.getenv("MFA_CHALLENGE_TTL_SECONDS", "300"))
    # Number of recovery codes generated on enrollment.
    MFA_RECOVERY_CODES_COUNT: int = int(os.getenv("MFA_RECOVERY_CODES_COUNT", "10"))
    # Issuer label shown by authenticator apps.
    MFA_ISSUER: str = os.getenv("MFA_ISSUER", "Global Intelligence")

    # ------------------------------------------------------------------
    # Report signing — Ed25519
    # ------------------------------------------------------------------
    # PEM PKCS#8 files. In state-grade deployments these MUST point at
    # a path mounted from an encrypted volume or HSM/KMS-backed file.
    # If absent and STATE_GRADE_MODE=true, the publication endpoint
    # refuses to mark reports as published.
    SIGNING_PRIVATE_KEY_PATH: str = os.getenv(
        "SIGNING_PRIVATE_KEY_PATH", "/var/lib/gi/signing/ed25519_private.pem"
    )
    SIGNING_PUBLIC_KEY_PATH: str = os.getenv(
        "SIGNING_PUBLIC_KEY_PATH", "/var/lib/gi/signing/ed25519_public.pem"
    )

    # ------------------------------------------------------------------
    # OSINT providers
    # ------------------------------------------------------------------
    # Free-tier NewsAPI key. Empty disables NewsAPIProvider.
    NEWSAPI_API_KEY: str = os.getenv("NEWSAPI_API_KEY", "")
    # GDELT 2.0 document API base URL. The default is the public
    # endpoint — change only for self-hosted mirrors.
    GDELT_BASE_URL: str = os.getenv(
        "GDELT_BASE_URL", "https://api.gdeltproject.org/api/v2/doc/doc"
    )
    # Per-provider HTTP timeout in seconds.
    OSINT_HTTP_TIMEOUT: int = int(os.getenv("OSINT_HTTP_TIMEOUT", "30"))
    # Hard cap on records pulled from any single source. Belt-and-braces
    # for upstreams that ignore our explicit limit parameter.
    OSINT_MAX_PER_SOURCE: int = int(os.getenv("OSINT_MAX_PER_SOURCE", "25"))

    def validate_secrets(self) -> None:
        """Validar que los secrets críticos están configurados en producción."""
        env = os.getenv("ENV", "development")
        if env == "production":
            _require("SECRET_KEY")
            _require("POSTGRES_PASSWORD")
        if self.STATE_GRADE_MODE:
            # State-grade requires MFA at-rest encryption and a separate
            # challenge secret. Fail closed at startup rather than at
            # the first enrollment.
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
