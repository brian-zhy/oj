"""create contests

Revision ID: create_contests
Revises: add_team_problems
Create Date: 2026-09-12

比赛功能（ACM 赛制 MVP）：contests / contest_problems / contest_participants，
比赛内提交复用 submissions（新增 contest_id 列）。
"""
from alembic import op
import sqlalchemy as sa

revision = "create_contests"
down_revision = "add_team_problems"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column("contest_id", sa.Integer(),
                  sa.ForeignKey("contests.id", ondelete="SET NULL"), nullable=True),
    )

    op.create_table(
        "contests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("owner_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contests_owner_id", "contests", ["owner_id"])

    op.create_table(
        "contest_problems",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contest_id", sa.Integer(),
                  sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("problem_id", sa.Integer(),
                  sa.ForeignKey("problems.id"), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("contest_id", "problem_id", name="uq_contest_problem"),
    )
    op.create_index("ix_contest_problems_contest_id", "contest_problems", ["contest_id"])

    op.create_table(
        "contest_participants",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("contest_id", sa.Integer(),
                  sa.ForeignKey("contests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("contest_id", "user_id", name="uq_contest_participant"),
    )
    op.create_index("ix_contest_participants_contest_id", "contest_participants",
                    ["contest_id"])


def downgrade() -> None:
    op.drop_table("contest_participants")
    op.drop_table("contest_problems")
    op.drop_index("ix_contests_owner_id", table_name="contests")
    op.drop_table("contests")
    op.drop_column("submissions", "contest_id")
