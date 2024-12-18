#!/bin/bash
set -e

# Function to wait for database
wait_for_db() {
    echo "Waiting for database..."
    while ! poetry run python -c "
import sys
import psycopg2
import os

try:
    psycopg2.connect(os.getenv('DATABASE_URL'))
except psycopg2.OperationalError:
    sys.exit(1)
sys.exit(0)
"; do
        sleep 1
    done
    echo "Database is ready!"
}

case "$1" in
    web)
        # Wait for database before starting web server
        wait_for_db
        
        # Run migrations using Flask-Migrate
        echo "Running database migrations..."
        poetry run flask db upgrade
        
        # Start Gunicorn with the combined web service and scheduler
        echo "Starting web server with integrated scheduler..."
        exec poetry run gunicorn \
            --bind 0.0.0.0:${PORT:-5000} \
            --workers ${GUNICORN_WORKERS:-2} \
            --threads ${GUNICORN_THREADS:-4} \
            --timeout ${GUNICORN_TIMEOUT:-30} \
            --access-logfile - \
            --error-logfile - \
            --log-level ${LOG_LEVEL:-info} \
            --preload \
            "src.app:app"
        ;;
        
    test)
        # Wait for database before running tests
        wait_for_db
        
        echo "Running tests..."
        exec poetry run pytest "${@:2}"
        ;;
        
    shell)
        # Wait for database before starting shell
        wait_for_db
        
        echo "Starting Python shell..."
        exec poetry run python
        ;;
        
    *)
        # Run custom command
        exec "$@"
        ;;
esac
