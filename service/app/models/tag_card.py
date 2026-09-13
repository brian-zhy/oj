"""Tag 卡模型：用户可佩戴的称号卡（参照洛谷勋章）。

显示优先级见 User.display_tag：启用中的卡 > user_tag（管理后台设置）
> 管理员默认「管理员」；作弊者（非管理员）强制显示「作弊者」不被卡掩盖。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserTagCard(Base):
    __tablename__ = "user_tag_cards"
    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_tag_card"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 是否佩戴（同一用户同时只有一张启用：开启一张会自动停用其他）
    enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
