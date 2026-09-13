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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # Runtime mode
    ENV: Literal["dev", "prod"] = "dev"

    # 前端地址：邮件里的链接必须是绝对地址（密码重置等）。
    # 本地开发默认指向前端 dev server；**生产必须改成真实域名**，
    # 否则用户收到的重置链接会指向 localhost（启动时会直接报错拦下）。
    FRONTEND_URL: str = "http://localhost:5173"

    # go-judge 评测沙箱地址（宿主机 systemd 服务）
    GO_JUDGE_URL: str = "http://host.docker.internal:5050"

    # 图床（/images）
    # 「高级空间」与「普通空间」双配额，规则参照洛谷：
    #   无水印 或 体积超过阈值的图 → 占用高级空间；带水印且不超阈值 → 普通空间
    IMAGE_PREMIUM_QUOTA_BYTES: int = 10 * 1024 * 1024   # 高级空间 10MB
    IMAGE_BASIC_QUOTA_BYTES: int = 50 * 1024 * 1024     # 普通空间 50MB
    IMAGE_PREMIUM_SIZE_THRESHOLD: int = 500 * 1024      # 超过 500KB 强制占用高级空间
    IMAGE_MAX_FILE_BYTES: int = 10 * 1024 * 1024        # 单张图片上限 10MB

    # 图床水印：在右下角盖一行站点名文字（参照洛谷，用站点名而不是 logo）
    IMAGE_WATERMARK_TEXT: str = "NLNOJ"
    IMAGE_WATERMARK_FONT: str | None = None             # 自定义字体路径，留空自动查找
    IMAGE_WATERMARK_OPACITY: int = 140                  # 水印不透明度 0-255

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
            if "localhost" in self.FRONTEND_URL or "127.0.0.1" in self.FRONTEND_URL:
                raise RuntimeError(
                    "FRONTEND_URL must be the public site URL when ENV=prod, "
                    "otherwise password-reset emails point users at localhost. "
                    "e.g. FRONTEND_URL=https://nlnoj.gr3yph4ntom.cn"
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
