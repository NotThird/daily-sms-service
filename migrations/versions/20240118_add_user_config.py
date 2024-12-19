"""add user config

Revision ID: 20240118_add_user_config
Revises: 20240117_add_message_details
Create Date: 2024-01-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20240118_add_user_config'
down_revision = '20240117_add_message_details'
branch_labels = None
depends_on = None

def upgrade():
    """Create user_configs table with existence check."""
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy import inspect
    
    # Check if table already exists
    inspector = inspect(op.get_bind())
    tables = inspector.get_table_names()
    
    if 'user_configs' not in tables:
        try:
            op.create_table('user_configs',
                sa.Column('id', sa.Integer(), nullable=False),
                sa.Column('recipient_id', sa.Integer(), nullable=False),
                sa.Column('name', sa.String(length=100), nullable=True),
                sa.Column('email', sa.String(length=255), nullable=True),
                sa.Column('preferences', sa.JSON(), nullable=False, server_default='{}'),
                sa.Column('personal_info', sa.JSON(), nullable=False, server_default='{}'),
                sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
                sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
                sa.PrimaryKeyConstraint('id'),
                sa.ForeignKeyConstraint(['recipient_id'], ['recipients.id'], ondelete='CASCADE')
            )
        except ProgrammingError as e:
            if 'already exists' not in str(e):
                raise  # Re-raise if it's not a "table exists" error

def downgrade():
    """Drop user_configs table if it exists."""
    from sqlalchemy.exc import ProgrammingError
    
    try:
        op.drop_table('user_configs')
    except ProgrammingError as e:
        if 'does not exist' not in str(e):
            raise  # Re-raise if it's not a "table doesn't exist" error
