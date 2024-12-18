"""add user config

Revision ID: add_user_config
Revises: add_message_details
Create Date: 2024-01-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_user_config'
down_revision = 'add_message_details'
branch_labels = None
depends_on = None

def upgrade():
    # Create user_configs table
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

def downgrade():
    # Drop user_configs table
    op.drop_table('user_configs')
