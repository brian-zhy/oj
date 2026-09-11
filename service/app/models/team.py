"""团队模型（参照 Jason227 站的 teams / team_members 设计适配本站）。

- 团队所有者（owner_id）记录在 teams 表上，不在 team_members 行内，
  成员列表渲染时把 owner 以 role='owner' 拼入（与参考站一致）。
- team_members.role：member 普通成员 / admin 团队管理员（可管理成员）。
- note：团队管理员给成员写的备注名（团队内可见）。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    # 团队简介（可空）
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 团队所有者（创建者）
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    owner: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[owner_id], lazy="joined"
    )
    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team", cascade="all, delete-orphan",
        lazy="selectin",
    )


class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    # member 普通成员 / admin 团队管理员
    role: Mapped[str] = mapped_column(
        String(10), nullable=False, default="member", server_default="'member'"
    )
    # 团队管理员给成员写的备注名
    note: Mapped[str | None] = mapped_column(String(50), nullable=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    team: Mapped["Team"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="joined")  # noqa: F821
