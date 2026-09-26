"""add ticket_attachments (工单附件)

Revision ID: add_ticket_att
Revises: add_user_theme
Create Date: 2026-09-26

工单附件表：挂回复上（创建工单时的描述附件挂首条回复）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_ticket_att"
down_revision = "add_theme_brightness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_attachments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ticket_id", sa.Integer(),
                  sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reply_id", sa.Integer(),
                  sa.ForeignKey("ticket_replies.id", ondelete="CASCADE"), nullable=False),
        sa.Column("uploader_id", sa.Integer(),
                  sa.ForeignKey("users.id"), nullable=False),
        sa.Column("orig_name", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False, unique=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
    )
    op.create_index("ix_ticket_attachments_ticket_id", "ticket_attachments", ["ticket_id"])
    op.create_index("ix_ticket_attachments_reply_id", "ticket_attachments", ["reply_id"])
    op.create_index("ix_ticket_attachments_uploader_id", "ticket_attachments", ["uploader_id"])


def downgrade() -> None:
    op.drop_table("ticket_attachments")
