from functools import lru_cache
from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


def _resolve_env_file() -> str:
    """Decide qual arquivo .env carregar.

    Comportamento:
      - Se ENV_FILE estiver setado: usa esse caminho (modo teste produção)
      - Se NÃO estiver setado: usa backend/.env (modo dev normal, igual era antes)
    """
    backend_dir = Path(__file__).resolve().parents[2]
    default_env = backend_dir / ".env"

    # Se ENV_FILE foi setado explicitamente, usa ele
    explicit = os.environ.get("ENV_FILE")
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = (backend_dir / explicit).resolve()
        if path.exists():
            return str(path)
        print(f"[config] AVISO: ENV_FILE={explicit} não existe, usando backend/.env")

    # Modo padrão (dev): sempre backend/.env
    return str(default_env)


class Settings(BaseSettings):
    """Centralised application settings.

    Carregado de ``backend/.env`` por padrão (modo dev).
    Para forçar outro arquivo (ex: ``.env.test``), sete a variável
    de ambiente ``ENV_FILE=/caminho/do/.env.test`` antes de rodar o backend.
    """

    model_config = SettingsConfigDict(
        env_file=_resolve_env_file(),
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------------------------------------------------------- App
    APP_NAME: str = "[NEV]2 Restaurant Management System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ---------------------------------------------------------- Database
    DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./restaurant_nev2.db",
        validation_alias="DATABASE_URL",
    )

    # ---------------------------------------------------------------- Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL",
    )

    # ---------------------------------------------------------- Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production-min-32-chars",
        validation_alias="SECRET_KEY",
    )
    SECRET_KEY_REGISTER: str = Field(default="123", validation_alias="SECRET_KEY_REGISTER")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    MAX_CONCURRENT_SESSIONS: int = Field(default=5, validation_alias="MAX_CONCURRENT_SESSIONS")

    # ---------------------------------------------------------------- CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # ---------------------------------------------------------- Backend URL
    BACKEND_URL: str = Field(
        default="http://localhost:8000", validation_alias="BACKEND_URL"
    )

    # ----------------------------------------------------- Mercado Pago
    # Access token is server-side only. Public key is shared with the
    # frontend but is *safe* to expose (the MP docs are clear about this).
    MP_ACCESS_TOKEN: str = Field(default="", validation_alias="MP_ACCESS_TOKEN")
    MP_PUBLIC_KEY: str = Field(default="", validation_alias="MP_PUBLIC_KEY")
    MP_WEBHOOK_SECRET: str = Field(
        default="", validation_alias="MP_WEBHOOK_SECRET"
    )
    MP_ENVIRONMENT: str = Field(
        default="sandbox", validation_alias="MP_ENVIRONMENT"
    )  # "sandbox" or "production"

    # Plan pricing — stored in cents (R$ * 100). Override via env if you
    # want to change the SaaS pricing without redeploying.
    MP_PRICE_ESSENCIAL: int = Field(default=9900, validation_alias="MP_PRICE_ESSENCIAL")
    MP_PRICE_PROFISSIONAL: int = Field(
        default=19900, validation_alias="MP_PRICE_PROFISSIONAL"
    )
    MP_PRICE_ESCALA: int = Field(default=39900, validation_alias="MP_PRICE_ESCALA")

    # ---------------------------------------------------------- SMTP
    SMTP_HOST: str = Field(default="seu_smtp_host", validation_alias="SMTP_HOST")
    SMTP_PORT: int = Field(default=587, validation_alias="SMTP_PORT")
    SMTP_USER: str = Field(default="seu_usuario_smtp", validation_alias="SMTP_USER")
    SMTP_PASS: str = Field(default="sua_senha_smtp", validation_alias="SMTP_PASS")
    SMTP_TLS: bool = Field(default=True, validation_alias="SMTP_TLS")
    FROM_EMAIL: str = Field(default="nao-responda@seudominio.com", validation_alias="FROM_EMAIL")

    # Trial: any newly created restaurant gets this many days of free access
    # before being forced to subscribe. Set to 0 to disable.
    TRIAL_DAYS: int = Field(default=7, validation_alias="TRIAL_DAYS")

    # ---------------------------------------------------------- Frontend
    FRONTEND_URL: str = Field(
        default="http://localhost:5173", validation_alias="FRONTEND_URL"
    )

    # ---------------------------------------------------------- Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
