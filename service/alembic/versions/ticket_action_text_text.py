"""ticket_replies.action_text -> Text (标题修改记录含新旧标题全文)

Revision ID: ticket_action_txt
Revises: add_ticket_att
Create Date: 2026-09-26
"""
from alembic import op
import sqlalchemy as sa

revision = "ticket_action_txt"
down_revision = "add_ticket_att"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("ticket_replies") as batch_op:
        batch_op.alter_column(
            "action_text",
            existing_type=sa.String(length=100),
            type_=sa.Text(),
            existing_nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table("ticket_replies") as batch_op:
        batch_op.alter_column(
            "action_text",
            existing_type=sa.Text(),
            type_=sa.String(length=100),
            existing_nullable=True,
        )
