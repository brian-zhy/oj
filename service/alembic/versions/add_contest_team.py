"""add contest team

Revision ID: add_contest_team
Revises: add_contest_visibility
Create Date: 2026-09-13

团队办赛：contests.team_id（举办团队，NULL=站方比赛）。
visibility 扩展四种：public 公开庭 / private 邀请赛 /
team 团队内部赛 / team_private 团队邀请赛。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_contest_team"
down_revision = "add_contest_visibility"
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
