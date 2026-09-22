"""add contribution

Revision ID: add_contribution
Revises: create_home_ads
Create Date: 2026-09-22

用户贡献值字段（出题按难度获得，贡献商店货币）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_contribution"
down_revision = "create_home_ads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("contribution", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "contribution")
