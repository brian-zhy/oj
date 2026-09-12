"""add team join requests

Revision ID: add_team_join_requests
Revises: create_teams
Create Date: 2026-09-12

加入团队审核：申请表（行存在即待审核，通过/拒绝后删除）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_team_join_requests"
down_revision = "create_teams"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_join_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer(),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_join_request"),
    )
    op.create_index("ix_team_join_requests_team_id", "team_join_requests", ["team_id"])
    op.create_index("ix_team_join_requests_user_id", "team_join_requests", ["user_id"])


def downgrade() -> None:
    op.drop_table("team_join_requests")
