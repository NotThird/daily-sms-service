"""add message details

Revision ID: 20240117_add_message_details
Revises: 1a2b3c4d5e6f
Create Date: 2024-01-17 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240117_add_message_details'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None

def upgrade():
    """Add new columns to message_logs table with proper transaction handling."""
    from sqlalchemy.exc import ProgrammingError, InternalError
    from sqlalchemy import text, inspect
    
    # Get current columns
    connection = op.get_bind()
    inspector = inspect(connection)
    existing_columns = {col['name'] for col in inspector.get_columns('message_logs')}
    
    # List of columns to add with their definitions
    columns = [
        ('delivered_at', sa.DateTime(), True),
        ('price', sa.Float(), True),
        ('price_unit', sa.String(length=10), True),
        ('direction', sa.String(length=20), True)
    ]
    
    # Add each column if it doesn't exist
    for col_name, col_type, nullable in columns:
        if col_name not in existing_columns:
            try:
                # Start a new transaction for each column
                with connection.begin() as trans:
                    op.add_column('message_logs', sa.Column(col_name, col_type, nullable=nullable))
                    trans.commit()
            except (ProgrammingError, InternalError) as e:
                if 'already exists' not in str(e):
                    raise  # Re-raise if it's not a "column exists" error

def downgrade():
    """Remove columns if they exist."""
    from sqlalchemy.exc import ProgrammingError
    
    # List of columns to remove
    columns = ['delivered_at', 'price', 'price_unit', 'direction']
    
    # Remove each column if it exists
    for col_name in columns:
        try:
            op.drop_column('message_logs', col_name)
        except ProgrammingError as e:
            if 'does not exist' in str(e):
                pass  # Column doesn't exist, skip it
            else:
                raise  # Re-raise if it's a different error
