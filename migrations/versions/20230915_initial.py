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
    """Create initial tables."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect
    
    # Get database connection
    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()
    
    try:
        # Create recipients table if it doesn't exist
        if 'recipients' not in existing_tables:
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
        
        # Create message_logs table if it doesn't exist
        if 'message_logs' not in existing_tables:
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
        
        # Create scheduled_messages table if it doesn't exist
        if 'scheduled_messages' not in existing_tables:
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
        
        # Create indexes if they don't exist
        def create_index_safely(index_name, table_name, columns):
            try:
                if not any(idx['name'] == index_name for idx in inspector.get_indexes(table_name)):
                    op.create_index(index_name, table_name, columns)
            except (ProgrammingError, InternalError) as e:
                if 'already exists' not in str(e):
                    raise
        
        create_index_safely('ix_message_logs_sent_at', 'message_logs', ['sent_at'])
        create_index_safely('ix_scheduled_messages_scheduled_time', 'scheduled_messages', ['scheduled_time'])
        create_index_safely('ix_scheduled_messages_status', 'scheduled_messages', ['status'])
        
    except (ProgrammingError, InternalError) as e:
        if 'already exists' not in str(e):
            raise

def downgrade() -> None:
    """Drop tables in reverse order."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect
    
    # Get database connection
    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()
    
    def drop_table_safely(table_name):
        if table_name in existing_tables:
            try:
                op.drop_table(table_name)
            except (ProgrammingError, InternalError) as e:
                if 'does not exist' not in str(e):
                    raise
    
    # Drop tables in reverse order
    drop_table_safely('scheduled_messages')
    drop_table_safely('message_logs')
    drop_table_safely('recipients')
