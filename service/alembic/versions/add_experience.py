"""add experience

Revision ID: add_experience
Revises: create_submissions
Create Date: 2026-09-09

用户经验值字段（首次 AC 按难度获得经验）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_experience"
down_revision = "create_submissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("experience", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "experience")
