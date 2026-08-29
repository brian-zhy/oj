"""讨论区模型（参照原站：站务版/题目总版/学术版/灌水区）。"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ForumPost(Base, TimestampMixin):
    __tablename__ = "forum_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # siteaffairs 站务版 / problem 题目总版 / academics 学术版 / relevantaffairs 灌水区
    forum: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )

    author: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[author_id], lazy="joined"
    )
    comments: Mapped[list["ForumComment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="ForumComment.id"
    )


class ForumComment(Base, TimestampMixin):
    __tablename__ = "forum_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("forum_posts.id", ondelete="CASCADE"), index=True, nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    author: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[author_id], lazy="joined"
    )
    post: Mapped["ForumPost"] = relationship(back_populates="comments")
