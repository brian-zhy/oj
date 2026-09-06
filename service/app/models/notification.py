"""站内通知模型（工单回复/状态变更等）。"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Notification(Base, TimestampMixin):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 接收者
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    # 通知类型：reply 工单被回复 / status 工单状态变更 / assign 责任人指派
    type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    # 展示文案（如：你的「test」工单被 brian_zheng 回复了，快来看看吧）
    content: Mapped[str] = mapped_column(String(200), nullable=False)
    # 关联工单（点击通知跳转）
    ticket_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    # 操作者（谁触发的通知）
    actor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False, index=True
    )

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[user_id], lazy="joined"
    )
    ticket: Mapped["Ticket | None"] = relationship(  # noqa: F821
        "Ticket", foreign_keys=[ticket_id]
    )
