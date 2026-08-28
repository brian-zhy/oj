"""ticket_replies add action_text

Revision ID: ticket_action_text
Revises: create_tickets
Create Date: 2026-08-28

状态变更动作记录字段。
"""
from alembic import op
import sqlalchemy as sa

revision = "ticket_action_text"
down_revision = "create_tickets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ticket_replies", sa.Column("action_text", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("ticket_replies", "action_text")
