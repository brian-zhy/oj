"""create user_images table (图床)

Revision ID: create_user_images
Revises: add_problem_author
Create Date: 2026-09-13

图床功能：记录用户上传的图片及其占用情况。
"""
from alembic import op
import sqlalchemy as sa

revision = "create_user_images"
down_revision = "add_problem_author"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_images",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(300), nullable=False),
        sa.Column("original_name", sa.String(200), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=True),
        sa.Column("watermark", sa.String(20), nullable=False,
                  server_default="none"),
        sa.Column("is_premium", sa.Boolean(), nullable=False,
                  server_default=sa.true()),
        sa.Column("is_locked", sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_user_images_user_id", "user_images", ["user_id"])
    op.create_index("ix_user_images_created_at", "user_images", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_user_images_created_at", table_name="user_images")
    op.drop_index("ix_user_images_user_id", table_name="user_images")
    op.drop_table("user_images")
