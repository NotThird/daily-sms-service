"""remove email field

Revision ID: 20240119_remove_email
Revises: 20240118_add_user_config
Create Date: 2024-01-19

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240119_remove_email'
down_revision = '20240118_add_user_config'
branch_labels = None
depends_on = None

def upgrade():
    # Remove email column from user_configs table
    op.drop_column('user_configs', 'email')

def downgrade():
    # Add back email column if needed to rollback
    op.add_column('user_configs', sa.Column('email', sa.String(255), nullable=True))
