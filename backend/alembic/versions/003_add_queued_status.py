"""Add queued status to content status enum

Revision ID: 003
Revises: 002
Create Date: 2026-02-21

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'queued' value to the contentstatus enum
    op.execute("ALTER TYPE contentstatus ADD VALUE IF NOT EXISTS 'queued' AFTER 'ready'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values easily.
    # In practice this would require recreating the enum type.
    pass
