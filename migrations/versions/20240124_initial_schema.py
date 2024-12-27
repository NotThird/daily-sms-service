"""Initial database schema

Revision ID: 20240124_initial
Revises: 
Create Date: 2024-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime
import logging

# revision identifiers, used by Alembic.
revision = '20240124_initial'
down_revision = None
branch_labels = None
depends_on = None

logger = logging.getLogger('alembic.env')

def table_exists(table_name):
    """Check if a table exists."""
    from sqlalchemy.engine import reflection
    inspector = reflection.Inspector.from_engine(op.get_bind())
    return table_name in inspector.get_table_names()

def upgrade() -> None:
    """Create initial database schema."""
    logger.info("Starting table creation")
    
    # Create recipients table
    if not table_exists('recipients'):
        logger.info("Creating recipients table")
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
        logger.info("Recipients table created")
    else:
        logger.info("Recipients table already exists")

    # Create user_configs table
    if not table_exists('user_configs'):
        logger.info("Creating user_configs table")
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
        logger.info("User_configs table created")
    else:
        logger.info("User_configs table already exists")

    # Create message_logs table
    if not table_exists('message_logs'):
        logger.info("Creating message_logs table")
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
        logger.info("Message_logs table created")
    else:
        logger.info("Message_logs table already exists")

    # Create scheduled_messages table
    if not table_exists('scheduled_messages'):
        logger.info("Creating scheduled_messages table")
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
        logger.info("Scheduled_messages table created")
    else:
        logger.info("Scheduled_messages table already exists")

    # Create indexes if they don't exist
    logger.info("Creating indexes")
    from sqlalchemy.engine import reflection
    inspector = reflection.Inspector.from_engine(op.get_bind())
    
    def create_index_if_not_exists(index_name, table_name, columns):
        existing_indexes = [idx['name'] for idx in inspector.get_indexes(table_name)]
        if index_name not in existing_indexes:
            logger.info(f"Creating index {index_name}")
            op.create_index(index_name, table_name, columns)
            logger.info(f"Index {index_name} created")
        else:
            logger.info(f"Index {index_name} already exists")

    create_index_if_not_exists('idx_recipient_phone', 'recipients', ['phone_number'])
    create_index_if_not_exists('idx_message_logs_recipient', 'message_logs', ['recipient_id'])
    create_index_if_not_exists('idx_message_logs_status', 'message_logs', ['status'])
    create_index_if_not_exists('idx_scheduled_messages_status', 'scheduled_messages', ['status'])
    create_index_if_not_exists('idx_scheduled_messages_time', 'scheduled_messages', ['scheduled_time'])
    logger.info("Index creation completed")

def downgrade() -> None:
    """Remove all tables in reverse order."""
    try:
        # Drop tables in reverse dependency order
        for table in ['scheduled_messages', 'message_logs', 'user_configs', 'recipients']:
            if table_exists(table):
                logger.info(f"Dropping table {table}")
                op.drop_table(table)
                logger.info(f"Table {table} dropped")
            else:
                logger.info(f"Table {table} does not exist")
    except Exception as e:
        logger.error(f"Error in downgrade: {str(e)}")
        raise
