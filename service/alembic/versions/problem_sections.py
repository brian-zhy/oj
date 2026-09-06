"""problem sections

Revision ID: problem_sections
Revises: create_problem_bank
Create Date: 2026-09-06

题面分节字段：背景 / 输入格式 / 输出格式 / 提示 / 样例组。
"""
from alembic import op
import sqlalchemy as sa

revision = "problem_sections"
down_revision = "create_problem_bank"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "problems",
        sa.Column("background", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "problems",
        sa.Column("input_format", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "problems",
        sa.Column("output_format", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column(
        "problems",
        sa.Column("hint", sa.Text(), nullable=False, server_default=sa.text("''")),
    )
    op.add_column("problems", sa.Column("samples", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("problems", "samples")
    op.drop_column("problems", "hint")
    op.drop_column("problems", "output_format")
    op.drop_column("problems", "input_format")
    op.drop_column("problems", "background")
