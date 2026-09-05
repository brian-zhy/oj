"""perf indexes

Revision ID: perf_indexes
Revises: ticket_identity_snapshot
Create Date: 2026-09-05

列表排序字段索引补全。
"""
from alembic import op

revision = "perf_indexes"
down_revision = "ticket_identity_snapshot"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_forum_posts_created_at", "forum_posts", ["created_at"])
    op.create_index("ix_tickets_last_reply_at", "tickets", ["last_reply_at"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_index("ix_benben_user_created", "benben", ["user_number", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_benben_user_created", table_name="benben")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_last_reply_at", table_name="tickets")
    op.drop_index("ix_forum_posts_created_at", table_name="forum_posts")
