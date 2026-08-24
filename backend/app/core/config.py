from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Centralised application settings.

    Loaded from ``backend/.env`` (see ``.env.example`` for the full list of
    supported variables). All values are cached via :func:`get_settings` so
    importing ``settings`` anywhere in the codebase is cheap.
    """

    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[2] / ".env"),
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

    # ---------------------------------------------------------------- CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # ---------------------------------------------------------- Base URL
    BASE_URL: str = Field(
        default="http://localhost:5173", validation_alias="BASE_URL"
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
