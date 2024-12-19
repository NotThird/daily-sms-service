import logging
from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from flask import current_app, Flask
from src.models import db

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Setup logging
logger = logging.getLogger('alembic.env')
logging.basicConfig(level=logging.INFO)

def get_url():
    """Get database URL from environment variable."""
    return os.getenv("DATABASE_URL")

def get_app():
    """Get Flask application."""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = get_url()
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

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
        target_metadata=db.metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with improved error handling and retry logic."""
    from time import sleep
    from sqlalchemy.exc import OperationalError, ProgrammingError
    
    max_attempts = 5
    attempt = 1
    wait_time = 5  # Initial wait time in seconds

    while attempt <= max_attempts:
        try:
            # Handle the case where we're running migrations through flask db migrate
            # vs. through alembic directly
            try:
                # Try to get the app from current_app
                app = current_app
            except RuntimeError:
                # If not in application context, create a new app
                app = get_app()

            with app.app_context():
                db_config = config.get_section(config.config_ini_section)
                if db_config:
                    db_config["sqlalchemy.url"] = get_url()

                # Configure the engine with a longer timeout
                engine_config = {
                    'pool_pre_ping': True,  # Enable connection health checks
                    'pool_recycle': 300,    # Recycle connections every 5 minutes
                    'connect_args': {
                        'connect_timeout': 10,  # Connection timeout in seconds
                        'options': '-c statement_timeout=30000'  # Statement timeout (30s)
                    }
                }
                connectable = db.create_engine(get_url(), **engine_config)

                with connectable.connect() as connection:
                    context.configure(
                        connection=connection,
                        target_metadata=db.metadata,
                        compare_type=True  # Enable column type comparison
                    )

                    with context.begin_transaction():
                        context.run_migrations()
                        logger.info("Migrations completed successfully")
                        return  # Exit on success

        except (OperationalError, ProgrammingError) as e:
            logger.error(f"Migration attempt {attempt} failed: {str(e)}")
            if attempt < max_attempts:
                logger.info(f"Waiting {wait_time} seconds before retry...")
                sleep(wait_time)
                # Exponential backoff up to 30 seconds
                wait_time = min(wait_time * 2, 30)
            attempt += 1
        except Exception as e:
            logger.error(f"Unexpected error during migration: {str(e)}")
            raise

    logger.error(f"Migration failed after {max_attempts} attempts")
    raise RuntimeError("Failed to complete migrations after multiple attempts")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
