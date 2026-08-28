"""create judgement_logs table

Revision ID: judgement_logs
Revises: add_super_admin_fields
Create Date: 2026-08-27

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'judgement_logs'
down_revision = 'add_super_admin_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'judgement_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('admin_id', sa.Integer(), nullable=False),
        sa.Column('target_user_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=50), nullable=False),
        sa.Column('action_detail', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['admin_id'], ['users.id']),
        sa.ForeignKeyConstraint(['target_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_judgement_logs_admin_id'), 'judgement_logs', ['admin_id'])
    op.create_index(op.f('ix_judgement_logs_target_user_id'), 'judgement_logs', ['target_user_id'])
    op.create_index(op.f('ix_judgement_logs_action_type'), 'judgement_logs', ['action_type'])


def downgrade() -> None:
    op.drop_index(op.f('ix_judgement_logs_action_type'), table_name='judgement_logs')
    op.drop_index(op.f('ix_judgement_logs_target_user_id'), table_name='judgement_logs')
    op.drop_index(op.f('ix_judgement_logs_admin_id'), table_name='judgement_logs')
    op.drop_table('judgement_logs')
