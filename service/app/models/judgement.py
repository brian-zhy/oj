"""Judgement log model (陶片放逐日志)."""

from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class JudgementLog(Base, TimestampMixin):
    __tablename__ = "judgement_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 执行操作的管理员
    admin_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    # 被操作的目标用户
    target_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )

    # 操作类型：grant_normal / revoke_normal / ostracism / admin_rotation /
    # brown_penalty / unbrown / ban / unban / grant_perm / revoke_perm ...
    action_type: Mapped[str] = mapped_column(String(50), index=True, nullable=False)

    # 操作详情：{ changes: [{permission, new_value}], category }
    action_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 操作原因
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    admin: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[admin_id], lazy="joined"
    )
    target_user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[target_user_id], lazy="joined"
    )
