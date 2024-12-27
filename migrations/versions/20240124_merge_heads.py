"""Merge multiple heads

Revision ID: 20240124_merge_heads
Revises: 20240124_initial
Create Date: 2024-01-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import logging

# revision identifiers, used by Alembic.
revision = '20240124_merge_heads'
# List parent revision
down_revision = '20240124_initial'  # Only depend on our initial schema
branch_labels = None
depends_on = None

# Set up logging
logger = logging.getLogger('alembic.env')

def upgrade() -> None:
    """Merge multiple heads."""
    try:
        logger.info("Starting merge of migration heads")
        logger.info("Using initial schema as base")
        
        # Re-create content column if it doesn't exist
        from sqlalchemy.engine import reflection
        from alembic import op
        import sqlalchemy as sa
        
        # Get inspector
        bind = op.get_bind()
        inspector = reflection.Inspector.from_engine(bind)
        
        # Check if content column exists
        columns = [col['name'] for col in inspector.get_columns('scheduled_messages')]
        if 'content' not in columns:
            logger.info("Adding content column to scheduled_messages")
            op.add_column('scheduled_messages',
                sa.Column('content', sa.Text(), nullable=True)
            )
        
        logger.info("Merge completed successfully")
    except Exception as e:
        logger.error("Error during merge: %s", str(e))
        import traceback
        logger.error(traceback.format_exc())
        raise

def downgrade() -> None:
    """No downgrade needed for merge."""
    pass
