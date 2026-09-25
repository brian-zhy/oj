"""Refresh-token model.

We store the SHA-256 hash of the raw refresh JWT (never the raw token), so we
can revoke tokens, detect reuse of a rotated token, and bulk-invalidate on
breach — none of which a purely stateless refresh JWT allows.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("false"), nullable=False
    )
    # 仅由「轮换」写入：本令牌已换成新对的时刻。并发/多标签页重放同一个已轮换
    # 令牌时，只有在 rotated_at 之后极短窗口内的重放才被当作合法续期放行。
    # 主动吊销（封禁、改密码踢全端、超量裁剪）保持为 NULL —— 这类令牌一律立即
    # 失效，否则「改密码即登出所有会话」的保证会被宽限期窗口绕过。
    rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")
