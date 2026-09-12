"""add contest visibility

Revision ID: add_contest_visibility
Revises: create_contests
Create Date: 2026-09-12

比赛公开程度：public 公开庭（自由报名）/ private 邀请赛（报名需邀请码）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_contest_visibility"
down_revision = "create_contests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contests",
        sa.Column("visibility", sa.String(10), nullable=False,
                  server_default="'public'"),
    )
    op.add_column(
        "contests",
        sa.Column("invite_code", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("contests", "invite_code")
    op.drop_column("contests", "visibility")
