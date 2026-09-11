"""create teams

Revision ID: create_teams
Revises: add_checkin
Create Date: 2026-09-11

团队功能：teams + team_members（参照 Jason227 站设计适配）。
"""
from alembic import op
import sqlalchemy as sa

revision = "create_teams"
down_revision = "add_checkin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("owner_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_teams_owner_id", "teams", ["owner_id"])

    op.create_table(
        "team_members",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("team_id", sa.Integer(),
                  sa.ForeignKey("teams.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(10), nullable=False,
                  server_default="'member'"),
        sa.Column("note", sa.String(50), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("team_id", "user_id", name="uq_team_member"),
    )
    op.create_index("ix_team_members_team_id", "team_members", ["team_id"])
    op.create_index("ix_team_members_user_id", "team_members", ["user_id"])


def downgrade() -> None:
    op.drop_table("team_members")
    op.drop_index("ix_teams_owner_id", table_name="teams")
    op.drop_table("teams")
