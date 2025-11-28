"""add_user_setting_table.

Revision ID: 8c2262511833
Revises: f1e2d3c4b5a6
Create Date: 2025-11-28 21:56:47.585768
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '8c2262511833'
down_revision = 'f1e2d3c4b5a6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Perform the upgrade."""
    op.create_table(
        "user_setting",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("user_id", "key"),
    )
    op.create_index(op.f("ix_user_setting_key"), "user_setting", ["key"], unique=False)
    op.create_index(op.f("ix_user_setting_user_id"), "user_setting", ["user_id"], unique=False)


def downgrade() -> None:
    """Perform the downgrade."""
    op.drop_index(op.f("ix_user_setting_user_id"), table_name="user_setting")
    op.drop_index(op.f("ix_user_setting_key"), table_name="user_setting")
    op.drop_table("user_setting")
