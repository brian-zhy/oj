"""add tag cards

Revision ID: add_tag_cards
Revises: add_contest_team
Create Date: 2026-09-13

Tag 卡系统：users.can_manage_tags 权限 + user_tag_cards 卡表。
存量非空 user_tag 直接生成一张已启用的卡（显示效果不变）。
"""
from alembic import op
import sqlalchemy as sa

revision = "add_tag_cards"
down_revision = "add_contest_team"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("can_manage_tags", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
    )
    op.create_table(
        "user_tag_cards",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  index=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False,
                  server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_user_tag_card"),
    )
    # 存量：现有 tag 直接变成一张已启用的卡
    op.execute(
        "INSERT INTO user_tag_cards (user_id, name, enabled, created_at) "
        "SELECT id, user_tag, true, CURRENT_TIMESTAMP FROM users "
        "WHERE user_tag IS NOT NULL AND user_tag != ''"
    )


def downgrade() -> None:
    op.drop_table("user_tag_cards")
    op.drop_column("users", "can_manage_tags")
