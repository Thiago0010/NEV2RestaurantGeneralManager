from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # App
    APP_NAME: str = "NEV2 Restaurant Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_nev2",
        validation_alias="DATABASE_URL"
    )
    
    # Redis
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        validation_alias="REDIS_URL"
    )
    
    # Security
    SECRET_KEY: str = Field(
        default="your-super-secret-key-change-in-production-min-32-chars",
        validation_alias="SECRET_KEY"
    )
    SECRET_KEY_REGISTER: str = Field(
        default="123",
        validation_alias="SECRET_KEY_REGISTER"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "http://192.168.15.183:3000", "http://192.168.15.183:5173"]
    
    # Base URL for QR codes
    BASE_URL: str = Field(
        default="http://localhost:5173",
        validation_alias="BASE_URL"
    )
    
    # Pagination
    DEFAULT_PAGE_SIZE: int = 50
    MAX_PAGE_SIZE: int = 500
    
    class Config:
        env_file = str(Path(__file__).resolve().parents[2] / ".env")
        case_sensitive = True
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()