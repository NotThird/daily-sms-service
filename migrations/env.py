import logging
from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from flask import current_app

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Setup logging
logger = logging.getLogger('alembic.env')
logging.basicConfig(level=logging.INFO)

def get_url():
    """Get database URL from environment variable."""
    return os.getenv("DATABASE_URL")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=current_app.extensions['migrate'].db.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Handle the case where we're running migrations through flask db migrate
    # vs. through alembic directly
    db_config = config.get_section(config.config_ini_section)
    if db_config:
        db_config["sqlalchemy.url"] = get_url()

    connectable = current_app.extensions['migrate'].db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=current_app.extensions['migrate'].db.metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
