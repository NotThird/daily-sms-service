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
    """Remove email column from user_configs table with proper transaction handling."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect, text
    
    # Get database connection
    connection = op.get_bind()
    
    # Check if table exists first
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    
    if 'user_configs' not in tables:
        return  # Nothing to do if table doesn't exist
    
    # Check if column exists
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    
    if 'email' in columns:
        try:
            # Start a new transaction
            with connection.begin() as trans:
                # Try direct column drop first
                op.drop_column('user_configs', 'email')
                trans.commit()
        except (ProgrammingError, InternalError) as e:
            if 'does not exist' not in str(e):
                try:
                    # If direct drop fails, try with batch operations in a new transaction
                    with connection.begin() as trans:
                        with op.batch_alter_table('user_configs') as batch_op:
                            batch_op.drop_column('email')
                        trans.commit()
                except (ProgrammingError, InternalError) as e2:
                    if 'does not exist' not in str(e2):
                        raise  # Re-raise if it's not a "column doesn't exist" error

def downgrade():
    """Add back email column if it doesn't exist."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import inspect, text
    
    # Get database connection
    connection = op.get_bind()
    
    # Check if table exists first
    inspector = inspect(connection)
    tables = inspector.get_table_names()
    
    if 'user_configs' not in tables:
        return  # Nothing to do if table doesn't exist
    
    # Check if column already exists
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    
    if 'email' not in columns:
        try:
            # Start a new transaction
            with connection.begin() as trans:
                # Try direct column add first
                op.add_column('user_configs', sa.Column('email', sa.String(255), nullable=True))
                trans.commit()
        except (ProgrammingError, InternalError) as e:
            if 'already exists' not in str(e):
                try:
                    # If direct add fails, try with batch operations in a new transaction
                    with connection.begin() as trans:
                        with op.batch_alter_table('user_configs') as batch_op:
                            batch_op.add_column(sa.Column('email', sa.String(255), nullable=True))
                        trans.commit()
                except (ProgrammingError, InternalError) as e2:
                    if 'already exists' not in str(e2):
                        raise  # Re-raise if it's not a "column exists" error
