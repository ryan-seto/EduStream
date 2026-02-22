"""Initial migration - create all tables

Revision ID: 001
Revises:
Create Date: 2024-01-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('role', sa.Enum('admin', 'editor', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_id', 'users', ['id'])
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Topics table
    op.create_table(
        'topics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_topics_id', 'topics', ['id'])

    # Contents table
    op.create_table(
        'contents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('topic_id', sa.Integer(), nullable=False),
        sa.Column('script_text', sa.Text(), nullable=True),
        sa.Column('diagram_path', sa.String(500), nullable=True),
        sa.Column('audio_path', sa.String(500), nullable=True),
        sa.Column('video_path', sa.String(500), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('draft', 'generating', 'ready', 'published', 'failed', name='contentstatus'), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['topic_id'], ['topics.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_contents_id', 'contents', ['id'])

    # Schedules table
    op.create_table(
        'schedules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content_id', sa.Integer(), nullable=False),
        sa.Column('platform', sa.Enum('youtube', 'tiktok', 'instagram', 'twitter', name='platform'), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('published_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.Enum('pending', 'published', 'failed', name='schedulestatus'), nullable=False),
        sa.Column('platform_post_id', sa.String(200), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['content_id'], ['contents.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_schedules_id', 'schedules', ['id'])


def downgrade() -> None:
    op.drop_index('ix_schedules_id', table_name='schedules')
    op.drop_table('schedules')
    op.drop_index('ix_contents_id', table_name='contents')
    op.drop_table('contents')
    op.drop_index('ix_topics_id', table_name='topics')
    op.drop_table('topics')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS contentstatus')
    op.execute('DROP TYPE IF EXISTS platform')
    op.execute('DROP TYPE IF EXISTS schedulestatus')
