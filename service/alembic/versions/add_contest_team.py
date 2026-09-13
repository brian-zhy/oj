"""add contest team

Revision ID: add_contest_team
Revises: create_user_images
Create Date: 2026-09-13

团队办赛：contests.team_id（举办团队，NULL=站方比赛）。
visibility 扩展四种：public 公开庭 / private 邀请赛 /
team 团队内部赛 / team_private 团队邀请赛。

注意：本迁移原本写成 Revises: add_contest_visibility，那会让迁移链分叉成
两个 head（add_contest_team 与 create_user_images），`alembic upgrade head`
会直接报 Multiple head revisions。此处改为接在 create_user_images 之后。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_contest_team"
down_revision = "create_user_images"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contests",
        sa.Column("team_id", sa.Integer(),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=True),
    )
    op.create_index("ix_contests_team_id", "contests", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_contests_team_id", table_name="contests")
    op.drop_column("contests", "team_id")
