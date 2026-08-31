"""ticket identity snapshot columns

Revision ID: ticket_identity_snapshot
Revises: user_cover_url
Create Date: 2026-08-30

工单/回复的身份快照：用户改名后历史记录仍显示当时身份。
"""
from alembic import op
import sqlalchemy as sa

revision = "ticket_identity_snapshot"
down_revision = "user_cover_url"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("creator_username", sa.String(length=50), nullable=True))
    op.add_column("tickets", sa.Column("creator_tag", sa.String(length=100), nullable=True))
    op.add_column("ticket_replies", sa.Column("user_username", sa.String(length=50), nullable=True))
    op.add_column("ticket_replies", sa.Column("user_tag", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_replies", "user_tag")
    op.drop_column("ticket_replies", "user_username")
    op.drop_column("tickets", "creator_tag")
    op.drop_column("tickets", "creator_username")
