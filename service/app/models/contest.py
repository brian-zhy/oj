"""比赛模型（ACM 赛制 MVP）。

- Contest：标题/简介/起止时间/创建者
- ContestProblem：比赛题目（按 sort_order 显示为 A/B/C/D…）
- ContestParticipant：报名记录
- 比赛内提交复用 Submission，新增 contest_id 列（NULL=常规提交）
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # 创建者（可编辑/删除比赛）
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[owner_id], lazy="joined"
    )
    problems: Mapped[list["ContestProblem"]] = relationship(
        back_populates="contest", cascade="all, delete-orphan",
        order_by="ContestProblem.sort_order", lazy="selectin",
    )
    participants: Mapped[list["ContestParticipant"]] = relationship(
        back_populates="contest", cascade="all, delete-orphan", lazy="selectin"
    )


class ContestProblem(Base):
    __tablename__ = "contest_problems"
    __table_args__ = (
        UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id"), index=True, nullable=False
    )
    # 显示顺序 0,1,2… → 别名 A/B/C/D
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    contest: Mapped["Contest"] = relationship(back_populates="problems")
    problem: Mapped["Problem"] = relationship("Problem", lazy="joined")  # noqa: F821


class ContestParticipant(Base):
    __tablename__ = "contest_participants"
    __table_args__ = (
        UniqueConstraint("contest_id", "user_id", name="uq_contest_participant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contest: Mapped["Contest"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")  # noqa: F821
