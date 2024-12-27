"""Initial database schema

Revision ID: 20240124_initial
Revises: 
Create Date: 2024-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = '20240124_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create recipients table
    op.create_table(
        'recipients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )

    # Create user_configs table
    op.create_table(
        'user_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('preferences', sa.JSON(), nullable=False, default={}),
        sa.Column('personal_info', sa.JSON(), nullable=False, default={}),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('updated_at', sa.DateTime(), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'])
    )

    # Create message_logs table
    op.create_table(
        'message_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('twilio_sid', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('price', sa.Float(), nullable=True),
        sa.Column('price_unit', sa.String(length=10), nullable=True),
        sa.Column('direction', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'])
    )

    # Create scheduled_messages table
    op.create_table(
        'scheduled_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, default='pending'),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=datetime.utcnow),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'])
    )

    # Create indexes
    op.create_index('idx_recipient_phone', 'recipients', ['phone_number'])
    op.create_index('idx_message_logs_recipient', 'message_logs', ['recipient_id'])
    op.create_index('idx_message_logs_status', 'message_logs', ['status'])
    op.create_index('idx_scheduled_messages_status', 'scheduled_messages', ['status'])
    op.create_index('idx_scheduled_messages_time', 'scheduled_messages', ['scheduled_time'])


def downgrade() -> None:
    op.drop_table('scheduled_messages')
    op.drop_table('message_logs')
    op.drop_table('user_configs')
    op.drop_table('recipients')
