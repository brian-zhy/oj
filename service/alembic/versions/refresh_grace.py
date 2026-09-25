"""refresh rotation grace

Revision ID: refresh_grace
Revises: add_contribution
Create Date: 2026-09-25

refresh_tokens 增加 rotated_at，支撑令牌轮换宽限期：
多标签页并发提交同一个 refresh 令牌时，输掉的一方不应把用户踢回登录页。
该列只由轮换写入，主动吊销（改密/封禁/超出数量上限）保持为空，
以保证这类作废立即生效。
"""
from alembic import op
import sqlalchemy as sa

revision = "refresh_grace"
down_revision = "add_contribution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("refresh_tokens", "rotated_at")
