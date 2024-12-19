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

# Function to run migrations with retries
run_migrations() {
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Running database migrations (attempt $attempt of $max_attempts)..."
        if poetry run flask db upgrade; then
            echo "Migrations completed successfully!"
            return 0
        else
            echo "Migration attempt $attempt failed"
            if [ $attempt -lt $max_attempts ]; then
                echo "Waiting before retry..."
                sleep 5
            fi
        fi
        attempt=$((attempt + 1))
    done
    
    echo "All migration attempts failed"
    return 1
}

case "$1" in
    web)
        # Wait for database before starting web server
        wait_for_db
        
        # Run migrations with retries
        if ! run_migrations; then
            echo "Failed to run migrations after multiple attempts"
            exit 1
        fi
        
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
