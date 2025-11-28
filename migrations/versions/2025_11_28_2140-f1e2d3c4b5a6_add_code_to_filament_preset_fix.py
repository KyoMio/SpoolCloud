"""add_code_to_filament_preset_fix

Revision ID: f1e2d3c4b5a6
Revises: a1b2c3d4e5f6
Create Date: 2025-11-28 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1e2d3c4b5a6'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table('filament_preset') as batch_op:
        batch_op.add_column(sa.Column('code', sa.String(length=32), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table('filament_preset') as batch_op:
        batch_op.drop_column('code')
