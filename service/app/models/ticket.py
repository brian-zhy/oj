"""工单系统模型（参照洛谷工单设计适配）。

类别：consult 一般咨询 / suggestion 建议反馈 / bug Bug反馈 / appeal 账号申诉
状态：pending 待处理 / replied 待补充 / processing 处理中 /
      suspended 挂起 / resolved 已完成 / closed 已关闭 / deleted 已删除
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Ticket(Base, TimestampMixin):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 展示编号（如 #1001），随自增 id 生成
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    creator_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    # 综合类工单默认公开（登录用户可见），申诉类私密
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_reply_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # 最后回复方：user 用户 / staff 管理
    last_reply_by: Mapped[str | None] = mapped_column(String(10), nullable=True)

    creator: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[creator_id], lazy="joined"
    )
    replies: Mapped[list["TicketReply"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan",
        order_by="TicketReply.id",
    )


class TicketReply(Base, TimestampMixin):
    __tablename__ = "ticket_replies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 是否为管理员（处理者）回复
    is_staff: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[user_id], lazy="joined"
    )
    ticket: Mapped["Ticket"] = relationship(back_populates="replies")
