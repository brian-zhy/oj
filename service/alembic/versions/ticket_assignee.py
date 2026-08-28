"""tickets add assignee_id

Revision ID: ticket_assignee
Revises: ticket_action_text
Create Date: 2026-08-28

责任人字段。
"""
from alembic import op
import sqlalchemy as sa

revision = "ticket_assignee"
down_revision = "ticket_action_text"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("assignee_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_tickets_assignee", "tickets", "users", ["assignee_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_tickets_assignee", "tickets", type_="foreignkey")
    op.drop_column("tickets", "assignee_id")
