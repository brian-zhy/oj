"""users add cover_url

Revision ID: user_cover_url
Revises: create_forum
Create Date: 2026-08-29

个人主页封面字段。
"""
from alembic import op
import sqlalchemy as sa

revision = "user_cover_url"
down_revision = "create_forum"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("cover_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "cover_url")
