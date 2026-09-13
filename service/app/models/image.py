"""图床图片模型。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class UserImage(Base, TimestampMixin):
    """用户上传到图床的图片。

    配额规则（参照洛谷）：
      - ``is_premium`` 为真 → 计入「高级空间」
      - 判定条件：无水印，或体积超过 ``IMAGE_PREMIUM_SIZE_THRESHOLD``
    """

    __tablename__ = "user_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # 可直接访问的 URL，形如 /static/uploads/images/xxx.png
    url: Mapped[str] = mapped_column(String(300), nullable=False)
    # 用户上传时的原始文件名（仅用于展示）
    original_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # none = 无水印 / text = 站点文字水印
    watermark: Mapped[str] = mapped_column(String(20), nullable=False, default="none")
    is_premium: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 锁定后不可删除，防误删
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    user: Mapped["User"] = relationship("User")
