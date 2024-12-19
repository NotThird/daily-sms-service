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
    """Add new columns to message_logs table with column existence check."""
    from sqlalchemy.exc import ProgrammingError
    
    # List of columns to add with their definitions
    columns = [
        ('delivered_at', sa.DateTime(), True),
        ('price', sa.Float(), True),
        ('price_unit', sa.String(length=10), True),
        ('direction', sa.String(length=20), True)
    ]
    
    # Add each column if it doesn't exist
    for col_name, col_type, nullable in columns:
        try:
            op.add_column('message_logs', sa.Column(col_name, col_type, nullable=nullable))
        except ProgrammingError as e:
            if 'already exists' in str(e):
                pass  # Column already exists, skip it
            else:
                raise  # Re-raise if it's a different error

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
