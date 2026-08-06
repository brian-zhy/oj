"""Application configuration loaded from environment / ``.env``."""

from __future__ import annotations

import secrets
from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values are read from the environment / ``.env``."""

    # Database. Local dev defaults to a zero-config SQLite file; production must
    # override this with a PostgreSQL URL (postgresql+asyncpg://...).
    DATABASE_URL: str = "sqlite+aiosqlite:///./oj.db"

    # Auth
    JWT_SECRET: SecretStr | None = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    BCRYPT_ROUNDS: int = 12

    # Runtime mode
    ENV: Literal["dev", "prod"] = "dev"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @model_validator(mode="after")
    def _enforce_prod_config(self) -> "Settings":
        if self.ENV == "prod":
            # Prod must provide an explicit JWT secret and a non-SQLite database.
            if not (self.JWT_SECRET and self.JWT_SECRET.get_secret_value()):
                raise RuntimeError("JWT_SECRET must be set when ENV=prod")
            if self.DATABASE_URL.startswith("sqlite"):
                raise RuntimeError(
                    "DATABASE_URL must point to PostgreSQL when ENV=prod"
                )
            return self
        # dev: if no secret is provided, generate a stable per-process one
        # (cached once on the instance, NOT re-randomized on every read).
        if not (self.JWT_SECRET and self.JWT_SECRET.get_secret_value()):
            object.__setattr__(self, "JWT_SECRET", SecretStr(secrets.token_urlsafe(32)))
        return self

    @property
    def jwt_secret(self) -> str:
        """Plain-text JWT secret. Safe: the validator guarantees it is set."""
        assert self.JWT_SECRET is not None  # noqa: S101
        return self.JWT_SECRET.get_secret_value()


settings = Settings()
