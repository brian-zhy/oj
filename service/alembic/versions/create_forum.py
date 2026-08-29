"""create forum tables

Revision ID: create_forum
Revises: ticket_assignee
Create Date: 2026-08-29

讨论区：forum_posts 帖子表 + forum_comments 回复表。
"""
from alembic import op
import sqlalchemy as sa

revision = "create_forum"
down_revision = "ticket_assignee"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "forum_posts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("forum", sa.String(length=30), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forum_posts_forum", "forum_posts", ["forum"])
    op.create_index("ix_forum_posts_author_id", "forum_posts", ["author_id"])

    op.create_table(
        "forum_comments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("post_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["forum_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_forum_comments_post_id", "forum_comments", ["post_id"])
    op.create_index("ix_forum_comments_author_id", "forum_comments", ["author_id"])


def downgrade() -> None:
    op.drop_index("ix_forum_comments_author_id", table_name="forum_comments")
    op.drop_index("ix_forum_comments_post_id", table_name="forum_comments")
    op.drop_table("forum_comments")
    op.drop_index("ix_forum_posts_author_id", table_name="forum_posts")
    op.drop_index("ix_forum_posts_forum", table_name="forum_posts")
    op.drop_table("forum_posts")
