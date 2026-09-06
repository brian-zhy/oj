"""create problem bank

Revision ID: create_problem_bank
Revises: forum_pin_lock
Create Date: 2026-09-06

题库表 + 题目管理权限（users.can_manage_problems）。
"""
from alembic import op
import sqlalchemy as sa

revision = "create_problem_bank"
down_revision = "forum_pin_lock"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "problems",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False,
                  server_default=sa.text("'暂无评定'")),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("time_limit", sa.Integer(), nullable=False,
                  server_default=sa.text("1000")),
        sa.Column("memory_limit", sa.Integer(), nullable=False,
                  server_default=sa.text("128")),
        sa.Column("submit_count", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("solved_count", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
        sa.Column("is_public", sa.Boolean(), nullable=False,
                  server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_problems_title", "problems", ["title"])
    op.create_index("ix_problems_difficulty", "problems", ["difficulty"])
    op.create_index("ix_problems_source", "problems", ["source"])

    op.add_column(
        "users",
        sa.Column("can_manage_problems", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "can_manage_problems")
    op.drop_index("ix_problems_source", table_name="problems")
    op.drop_index("ix_problems_difficulty", table_name="problems")
    op.drop_index("ix_problems_title", table_name="problems")
    op.drop_table("problems")
