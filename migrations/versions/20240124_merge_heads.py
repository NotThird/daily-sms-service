"""Merge multiple heads

Revision ID: 20240124_merge_heads
Revises: 20240120_add_message_content, 20240124_initial
Create Date: 2024-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import logging

# revision identifiers, used by Alembic.
revision = '20240124_merge_heads'
# List both parent revisions
down_revision = ('20240120_add_message_content', '20240124_initial')
branch_labels = None
depends_on = None

logger = logging.getLogger('alembic.env')

def upgrade() -> None:
    """Merge multiple heads."""
    try:
        logger.info("Starting merge of migration heads")
        logger.info("Parent revisions: %s", str(down_revision))
        # No operations needed for merge
        logger.info("Merge completed successfully")
    except Exception as e:
        logger.error("Error during merge: %s", str(e))
        import traceback
        logger.error(traceback.format_exc())
        raise

def downgrade() -> None:
    """No downgrade needed for merge."""
    pass
