"""add user theme_brightness (主题商店：背景亮度可调)

Revision ID: add_theme_brightness
Revises: add_user_theme
Create Date: 2026-10-08

背景亮度 0~100，越大越亮（叠加在背景图上的暗色遮罩越淡）。
带 server_default，存量行直接落到 50，与原固定遮罩观感一致。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_theme_brightness"
down_revision = "add_user_theme"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("theme_brightness", sa.Integer(), nullable=False,
                  server_default=sa.text("50")),
    )


def downgrade() -> None:
    op.drop_column("users", "theme_brightness")
