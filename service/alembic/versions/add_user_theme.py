"""add user theme (主题商店：自定义背景)

Revision ID: add_user_theme
Revises: refresh_grace
Create Date: 2026-09-25

用户主题字段：自定义背景图/预设渐变 + 启用开关。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_user_theme"
down_revision = "refresh_grace"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_background", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("theme_enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("users", "theme_enabled")
    op.drop_column("users", "theme_background")
