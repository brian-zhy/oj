"""create home carousel ads

Revision ID: create_home_ads
Revises: add_tag_cards
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "create_home_ads"
down_revision = "add_tag_cards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "home_ads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("image", sa.String(length=500), nullable=False),
        sa.Column("link", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("home_ads")