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
    # Add new columns to message_logs table
    op.add_column('message_logs', sa.Column('delivered_at', sa.DateTime(), nullable=True))
    op.add_column('message_logs', sa.Column('price', sa.Float(), nullable=True))
    op.add_column('message_logs', sa.Column('price_unit', sa.String(length=10), nullable=True))
    op.add_column('message_logs', sa.Column('direction', sa.String(length=20), nullable=True))

def downgrade():
    # Remove the new columns
    op.drop_column('message_logs', 'delivered_at')
    op.drop_column('message_logs', 'price')
    op.drop_column('message_logs', 'price_unit')
    op.drop_column('message_logs', 'direction')
