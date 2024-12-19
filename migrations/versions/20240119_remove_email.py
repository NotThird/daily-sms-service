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
    """Remove email column from user_configs table with existence check."""
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy import inspect
    
    # Check if column exists before trying to remove it
    inspector = inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    
    if 'email' in columns:
        try:
            # Try direct column drop first
            op.drop_column('user_configs', 'email')
        except ProgrammingError as e:
            if 'does not exist' not in str(e):
                # If it's not a "column doesn't exist" error, try batch operations
                with op.batch_alter_table('user_configs') as batch_op:
                    batch_op.drop_column('email')

def downgrade():
    """Add back email column if it doesn't exist."""
    from sqlalchemy.exc import ProgrammingError
    from sqlalchemy import inspect
    
    # Check if column already exists
    inspector = inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('user_configs')]
    
    if 'email' not in columns:
        try:
            # Try direct column add first
            op.add_column('user_configs', sa.Column('email', sa.String(255), nullable=True))
        except ProgrammingError as e:
            if 'already exists' not in str(e):
                # If it's not a "column exists" error, try batch operations
                with op.batch_alter_table('user_configs') as batch_op:
                    batch_op.add_column(sa.Column('email', sa.String(255), nullable=True))
