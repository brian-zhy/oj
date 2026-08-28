"""Benben (Social Media Post) model."""

from __future__ import annotations

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from typing import TYPE_CHECKING

from app.models.base import Base, TimestampMixin

# 前向引用User类型（避免循环导入）
if TYPE_CHECKING:
    from app.models.user import User


class Benben(Base, TimestampMixin):
    __tablename__ = "benben"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_number: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.user_number"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    reply_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("benben.id"), nullable=True, index=True
    )
    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="benben_posts")
    replies: Mapped[list["Benben"]] = relationship(
        "Benben", back_populates="parent_post", remote_side=[id]
    )
    parent_post: Mapped["Benben | None"] = relationship(
        "Benben", remote_side=[id], foreign_keys=[reply_to]
    )