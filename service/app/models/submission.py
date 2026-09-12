"""Submission & test case models（提交记录与题目测试点）."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    # Integer PK → SQLite rowid-alias autoincrement + Postgres SERIAL
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )

    code: Mapped[str] = mapped_column(Text, nullable=False)
    # cpp / c / python3
    language: Mapped[str] = mapped_column(String(20), nullable=False)

    # pending / judging / accepted / wrong_answer / time_limit_exceeded /
    # memory_limit_exceeded / runtime_error / compile_error / system_error
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending",
        server_default=text("'pending'"), index=True,
    )
    # 0-100（当前为二值判题：AC=100 其余=0）
    score: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    # 全部测试点的最大耗时 (ms) / 最大内存 (KB)
    time_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 编译错误 / 运行错误的 stderr 摘要
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 逐测试点结果：[{case, status, time, memory}]
    test_results: Mapped[list | None] = mapped_column(JSON, nullable=True)

    judged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 比赛内提交（NULL=常规提交）；比赛删除时置空
    contest_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="SET NULL"),
        index=True, nullable=True,
    )

    # 提交者（selectin：async 下自动随查询加载，避免懒加载炸绿票）
    user: Mapped["User"] = relationship("User", lazy="selectin")  # noqa: F821

    __table_args__ = (
        Index("ix_submissions_problem_user", "problem_id", "user_id"),
    )


class TestCase(Base, TimestampMixin):
    __tablename__ = "problem_test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("problems.id", ondelete="CASCADE"), index=True, nullable=False
    )
    input_data: Mapped[str] = mapped_column(Text, nullable=False, default="")
    expected_output: Mapped[str] = mapped_column(Text, nullable=False, default="")
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
