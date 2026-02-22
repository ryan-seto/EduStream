"""Add content type and script data

Revision ID: 002
Revises: 001
Create Date: 2024-01-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create content type enum
    content_type_enum = sa.Enum('problem', 'concept', name='contenttype')
    content_type_enum.create(op.get_bind(), checkfirst=True)

    # Add content_type column
    op.add_column(
        'contents',
        sa.Column('content_type', content_type_enum, nullable=True)
    )

    # Set default value for existing rows
    op.execute("UPDATE contents SET content_type = 'problem' WHERE content_type IS NULL")

    # Make column non-nullable with default
    op.alter_column(
        'contents',
        'content_type',
        existing_type=content_type_enum,
        nullable=False,
        server_default='problem'
    )

    # Add script_data JSON column
    op.add_column(
        'contents',
        sa.Column('script_data', sa.JSON(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('contents', 'script_data')
    op.drop_column('contents', 'content_type')

    # Drop the enum type
    content_type_enum = sa.Enum('problem', 'concept', name='contenttype')
    content_type_enum.drop(op.get_bind(), checkfirst=True)
