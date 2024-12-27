from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

import os
import sys
from pathlib import Path

# Add the project root directory to the Python path
sys.path.append(str(Path(__file__).parents[1]))

# this is the Alembic Config object
config = context.config

# Set up logging manually
import logging
logging.basicConfig(
    format='%(levelname)-5.5s [%(name)s] %(message)s',
    level=logging.INFO
)
logger = logging.getLogger('alembic.env')

try:
    # Import the Flask application
    from src.features.web_app.code import app, db
    logger.info("Successfully imported Flask app and db")
except Exception as e:
    logger.error(f"Failed to import Flask app: {str(e)}")
    raise

try:
    # Get the database URL from the Flask app config
    with app.app_context():
        db_url = app.config['SQLALCHEMY_DATABASE_URI']
        logger.info(f"Got database URL from config")
        
        # Handle SQLite URLs specially
        if db_url.startswith('sqlite:'):
            from sqlalchemy.engine import url as sa_url
            url = sa_url.make_url(db_url)
            if not url.database or url.database == ':memory:':
                db_url = 'sqlite:///app.db'
                logger.info("Using SQLite database")
        
        config.set_main_option('sqlalchemy.url', db_url)
        logger.info("Set database URL in Alembic config")
        
        # Ensure we can get the metadata
        if not hasattr(db, 'metadata'):
            logger.error("Database instance has no metadata attribute")
            raise AttributeError("Database instance has no metadata attribute")
        logger.info("Successfully accessed database metadata")
except Exception as e:
    logger.error(f"Failed to configure database: {str(e)}")
    raise

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = db.metadata
logger.info("Set target metadata for migrations")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    logger.info("Running offline migrations")
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    logger.info("Running online migrations")
    
    try:
        # Get database URL from app config
        db_url = config.get_main_option('sqlalchemy.url')
        logger.info(f"Using database URL from config")
        
        # Create engine with proper configuration
        engine_config = config.get_section(config.config_ini_section, {})
        engine_config['sqlalchemy.url'] = db_url
        
        # Handle multiple heads by using the merge revision
        from alembic.script import ScriptDirectory
        script = ScriptDirectory.from_config(config)
        heads = script.get_heads()
        logger.info(f"Found migration heads: {heads}")
        
        if len(heads) > 1:
            logger.info("Multiple heads detected, using merge revision")
            target_revision = "20240124_merge_heads"
        else:
            logger.info("Single head detected, using head")
            target_revision = "head"
            
        connectable = engine_from_config(
            engine_config,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
        
        with connectable.connect() as connection:
            logger.info(f"Running migration to target: {target_revision}")
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,  # Compare column types
                compare_server_default=True,  # Compare default values
                transaction_per_migration=True,  # Run each migration in its own transaction
                render_as_batch=True,  # Enable batch mode for SQLite compatibility
            )
            
            logger.info("Starting migration transaction")
            with context.begin_transaction():
                try:
                    context.run_migrations()
                    logger.info("Migrations completed successfully")
                except Exception as e:
                    logger.error("Error during migrations:")
                    logger.error(str(e))
                    import traceback
                    logger.error(traceback.format_exc())
                    raise
                
    except Exception as e:
        logger.error("Error setting up migration environment:")
        logger.error(str(e))
        import traceback
        logger.error(traceback.format_exc())
        raise

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
