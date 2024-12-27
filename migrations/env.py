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
    logger.info("Running offline migrations")
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.
    """
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
    logger.info("Running online migrations")
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            compare_type=True,  # Compare column types
            compare_server_default=True,  # Compare default values
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
