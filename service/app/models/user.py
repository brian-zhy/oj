"""User model."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    # Integer (not BigInteger) so the PK auto-increments on SQLite
    # (INTEGER PRIMARY KEY -> rowid alias) as well as PostgreSQL (SERIAL).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # 用户编号 (UID)
    user_number: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, nullable=False
    )

    # 手机号
    phone: Mapped[str | None] = mapped_column(
        String(20), unique=True, index=True, nullable=True
    )

    # 用户状态
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    is_banned: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    is_cheater: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    # 管理员权限
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    can_speak: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("true"), nullable=False
    )
    can_manage_users: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    can_manage_posts: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )

    # 用户个性化信息
    avatar_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    user_tag: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    username_color: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )
    bio: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Forward-ref string target is resolved from the Base registry; no import
    # needed here, which keeps user <-> refresh_token free of import cycles.
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
