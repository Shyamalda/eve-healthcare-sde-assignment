from __future__ import annotations

import os
from dataclasses import dataclass


def normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value[len("postgres://"):]
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value[len("postgresql://"):]
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "EVE Healthcare Diagnostic Booking API")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = normalize_database_url(os.getenv("DATABASE_URL", "sqlite:///./eve_healthcare.db"))
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "dev-only-secret-change-me-please-use-a-strong-key")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    webhook_secret: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret")
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


settings = Settings()
