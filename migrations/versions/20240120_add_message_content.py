"""add message content field

Revision ID: 20240120_add_message_content
Revises: 20240119_remove_email
Create Date: 2024-01-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20240120_add_message_content'
down_revision = '20240119_remove_email'
branch_labels = None
depends_on = None

def upgrade():
    # Check if content column exists before adding it
    from sqlalchemy.engine import reflection
    inspector = reflection.Inspector.from_engine(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('scheduled_messages')]
    if 'content' not in columns:
        # Add content column to scheduled_messages table
        op.add_column('scheduled_messages',
            sa.Column('content', sa.Text(), nullable=True)
        )

def downgrade():
    # Check if content column exists before dropping it
    from sqlalchemy.engine import reflection
    inspector = reflection.Inspector.from_engine(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('scheduled_messages')]
    if 'content' in columns:
        # Remove content column from scheduled_messages table
        op.drop_column('scheduled_messages', 'content')
