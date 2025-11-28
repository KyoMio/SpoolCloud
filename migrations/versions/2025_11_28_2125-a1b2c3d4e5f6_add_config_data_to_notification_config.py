"""add_config_data_to_notification_config

Revision ID: a1b2c3d4e5f6
Revises: 37293a96c8a9
Create Date: 2025-11-28 21:25:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '37293a96c8a9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('notification_config') as batch_op:
        batch_op.add_column(sa.Column('config_data', sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('notification_config') as batch_op:
        batch_op.drop_column('config_data')
