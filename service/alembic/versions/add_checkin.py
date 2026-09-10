"""add checkin

Revision ID: add_checkin
Revises: add_experience
Create Date: 2026-09-11

打卡数据落库（原先存前端 localStorage，换设备/清缓存即丢失重置）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_checkin"
down_revision = "add_experience"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("last_checkin_date", sa.Date(), nullable=True))
    op.add_column(
        "users",
        sa.Column("checkin_streak", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
    )
    op.add_column(
        "users",
        sa.Column("checkin_total", sa.Integer(), nullable=False,
                  server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("users", "checkin_total")
    op.drop_column("users", "checkin_streak")
    op.drop_column("users", "last_checkin_date")
