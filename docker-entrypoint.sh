#!/bin/bash
set -e

# Function to wait for database with increased timeout
wait_for_db() {
    echo "Waiting for database..."
    local max_attempts=30  # Increased max attempts
    local attempt=1
    local wait_time=2  # Initial wait time in seconds
    
    while [ $attempt -le $max_attempts ]; do
        echo "Database connection attempt $attempt of $max_attempts..."
        if poetry run python -c "
import sys
import psycopg2
import os
from time import sleep

try:
    # Add connection timeout
    conn = psycopg2.connect(os.getenv('DATABASE_URL'), connect_timeout=10)
    conn.close()
    sys.exit(0)
except psycopg2.OperationalError as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
"; then
            echo "Database is ready!"
            return 0
        fi
        
        echo "Waiting ${wait_time} seconds before retry..."
        sleep $wait_time
        
        # Exponential backoff up to 10 seconds
        if [ $wait_time -lt 10 ]; then
            wait_time=$((wait_time * 2))
        fi
        
        attempt=$((attempt + 1))
    done
    
    echo "Failed to connect to database after $max_attempts attempts"
    return 1
}

# Function to run migrations with improved retry logic
run_migrations() {
    local max_attempts=5  # Increased max attempts
    local attempt=1
    local wait_time=5  # Initial wait time in seconds
    
    while [ $attempt -le $max_attempts ]; do
        echo "Running database migrations (attempt $attempt of $max_attempts)..."
        if poetry run flask db upgrade; then
            echo "Migrations completed successfully!"
            return 0
        else
            echo "Migration attempt $attempt failed"
            if [ $attempt -lt $max_attempts ]; then
                echo "Waiting ${wait_time} seconds before retry..."
                sleep $wait_time
                
                # Exponential backoff up to 30 seconds
                if [ $wait_time -lt 30 ]; then
                    wait_time=$((wait_time * 2))
                fi
                
                # Verify database connection before retrying
                if ! wait_for_db; then
                    echo "Lost database connection, attempting to reconnect..."
                    continue
                fi
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
