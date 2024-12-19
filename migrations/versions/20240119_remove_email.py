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
    """Remove email column from user_configs table with retry logic."""
    try:
        # Try direct column drop first
        op.drop_column('user_configs', 'email')
    except Exception as e:
        # If direct drop fails, try with batch operations
        with op.batch_alter_table('user_configs') as batch_op:
            batch_op.drop_column('email')

def downgrade():
    """Add back email column if needed to rollback."""
    try:
        # Try direct column add first
        op.add_column('user_configs', sa.Column('email', sa.String(255), nullable=True))
    except Exception as e:
        # If direct add fails, try with batch operations
        with op.batch_alter_table('user_configs') as batch_op:
            batch_op.add_column(sa.Column('email', sa.String(255), nullable=True))
