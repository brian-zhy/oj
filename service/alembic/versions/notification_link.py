"""notification: 增加 link 跳转字段（帖子/犇犇等非工单来源）

原来 notifications 只有 ticket_id 一个跳转字段，论坛回复、@提及这类
通知没有地方存目标地址。加一个通用 link 存前端路由（如 /discuss/12）。
ticket_id 保留不动，老数据继续可用。

Revision ID: notification_link
Revises: add_contest_team
Create Date: 2026-09-13

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'notification_link'
down_revision = 'add_contest_team'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'notifications',
        sa.Column('link', sa.String(length=200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('notifications', 'link')
