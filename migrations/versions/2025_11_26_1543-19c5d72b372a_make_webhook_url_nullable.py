"""make_webhook_url_nullable

Revision ID: 19c5d72b372a
Revises: 38804b7861aa
Create Date: 2025-11-26 15:43:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19c5d72b372a'
down_revision = '38804b7861aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('notification_config') as batch_op:
        batch_op.alter_column('webhook_url',
               existing_type=sa.VARCHAR(length=512),
               type_=sa.Text(),
               nullable=True)


def downgrade() -> None:
    with op.batch_alter_table('notification_config') as batch_op:
        batch_op.alter_column('webhook_url',
               existing_type=sa.Text(),
               type_=sa.VARCHAR(length=512),
               nullable=False)
