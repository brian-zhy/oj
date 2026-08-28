"""add user remark and last_seen fields

Revision ID: add_user_remark
Revises: judgement_logs
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_user_remark'
down_revision = 'judgement_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('remark', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'last_seen')
    op.drop_column('users', 'remark')
