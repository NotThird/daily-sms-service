"""Merge multiple heads

Revision ID: 20240124_merge_heads
Revises: 20240124_initial, 20240120_add_message_content
Create Date: 2024-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import logging

# revision identifiers, used by Alembic.
revision = '20240124_merge_heads'
# List parent revisions
down_revision = ('20240124_initial', '20240120_add_message_content')
branch_labels = None
depends_on = None

# Set up logging
logger = logging.getLogger('alembic.env')

def upgrade() -> None:
    """Merge multiple heads."""
    logger.info("Starting merge of migration heads")
    # No operations needed for merge migration
    logger.info("Merge completed successfully")

def downgrade() -> None:
    """No downgrade needed for merge."""
    pass
