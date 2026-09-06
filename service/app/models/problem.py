"""Problem model（题库）."""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, JSON, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Problem(Base, TimestampMixin):
    __tablename__ = "problems"

    # Integer (not BigInteger) so the PK auto-increments on SQLite
    # (INTEGER PRIMARY KEY -> rowid alias) as well as PostgreSQL (SERIAL).
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # 洛谷 8 级难度（含「暂无评定」），存字符串便于直接展示/过滤
    difficulty: Mapped[str] = mapped_column(
        String(20), nullable=False, default="暂无评定",
        server_default=text("'暂无评定'"), index=True,
    )
    # 题目来源（NOIP / Codeforces / 自拟 ...）
    source: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    # 算法标签数组（plain JSON 跨 SQLite/Postgres 通用）
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # 题面（Markdown），样例 I/O 以代码块形式写在题面里
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")

    # 限制：时间 ms / 内存 MB
    time_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1000, server_default=text("1000")
    )
    memory_limit: Mapped[int] = mapped_column(
        Integer, nullable=False, default=128, server_default=text("128")
    )

    # 预留统计（评测对接后更新），本轮恒为 0
    submit_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )
    solved_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default=text("0")
    )

    # 下架开关：管理员可先建草稿再完善题面
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=text("true")
    )

    # 题号不落库：P1000 风格，由 id 推导
    @property
    def problem_number(self) -> str:
        return f"P{1000 + self.id}"
