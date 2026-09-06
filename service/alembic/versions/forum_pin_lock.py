"""forum pin/lock columns

Revision ID: forum_pin_lock
Revises: ticket_identity_snapshot
Create Date: 2026-09-06

帖子置顶与锁定字段。
"""
from alembic import op
import sqlalchemy as sa

revision = "forum_pin_lock"
down_revision = "create_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("forum_posts", sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("forum_posts", sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.create_index("ix_forum_posts_is_pinned", "forum_posts", ["is_pinned"])


def downgrade() -> None:
    op.drop_index("ix_forum_posts_is_pinned", table_name="forum_posts")
    op.drop_column("forum_posts", "is_pinned")
    op.drop_column("forum_posts", "is_locked")
