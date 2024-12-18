"""Initial migration

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2023-09-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
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
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone_number')
    )

    # Create message_logs table
    op.create_table(
        'message_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('twilio_sid', sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create scheduled_messages table
    op.create_table(
        'scheduled_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recipient_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        'ix_message_logs_sent_at',
        'message_logs',
        ['sent_at']
    )
    op.create_index(
        'ix_scheduled_messages_scheduled_time',
        'scheduled_messages',
        ['scheduled_time']
    )
    op.create_index(
        'ix_scheduled_messages_status',
        'scheduled_messages',
        ['status']
    )

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('scheduled_messages')
    op.drop_table('message_logs')
    op.drop_table('recipients')
