"""add problem author

Revision ID: add_problem_author
Revises: add_contest_visibility
Create Date: 2026-09-12

题目出题人：problems.author_id（存量题为 NULL，前端不显示）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_problem_author"
down_revision = "add_contest_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "problems",
        sa.Column("author_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"),
                  nullable=True),
    )
    op.create_index("ix_problems_author_id", "problems", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_problems_author_id", table_name="problems")
    op.drop_column("problems", "author_id")
