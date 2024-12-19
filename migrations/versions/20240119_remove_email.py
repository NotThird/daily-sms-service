"""remove email field

Revision ID: 20240119_remove_email
Revises: 20240118_add_user_config
Create Date: 2024-01-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240119_remove_email'  # Keep this shorter ID
down_revision = '20240118_add_user_config'
branch_labels = None
depends_on = None

def upgrade():
    """Remove email column from user_configs table."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect
    
    # Get database connection
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Check if table exists first
    if 'user_configs' not in inspector.get_table_names():
        return  # Nothing to do if table doesn't exist
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    if 'email' in columns:
        try:
            # Try direct column drop first
            op.drop_column('user_configs', 'email')
        except (ProgrammingError, InternalError) as e:
            if 'does not exist' not in str(e):
                # If direct drop fails, try with batch operations
                with op.batch_alter_table('user_configs') as batch_op:
                    batch_op.drop_column('email')

def downgrade():
    """Add back email column if it doesn't exist."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect
    
    # Get database connection
    connection = op.get_bind()
    inspector = inspect(connection)
    
    # Check if table exists first
    if 'user_configs' not in inspector.get_table_names():
        return  # Nothing to do if table doesn't exist
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    if 'email' not in columns:
        try:
            # Try direct column add first
            op.add_column('user_configs', sa.Column('email', sa.String(255), nullable=True))
        except (ProgrammingError, InternalError) as e:
            if 'already exists' not in str(e):
                # If direct add fails, try with batch operations
                with op.batch_alter_table('user_configs') as batch_op:
                    batch_op.add_column(sa.Column('email', sa.String(255), nullable=True))
