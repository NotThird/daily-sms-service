#!/bin/bash
set -e

# Function to wait for database with increased timeout
wait_for_db() {
    echo "Waiting for database..."
    local max_attempts=30
    local attempt=1
    local wait_time=2
    
    while [ $attempt -le $max_attempts ]; do
        echo "Database connection attempt $attempt of $max_attempts..."
        if poetry run python -c "
import sys
import psycopg2
import os
from time import sleep

try:
    conn = psycopg2.connect(
        os.environ['DATABASE_URL'],
        connect_timeout=10,
        application_name='health_check'
    )
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
    local max_attempts=5
    local attempt=1
    local wait_time=5
    local reset_attempted=false
    
    local original_db_url="${DATABASE_URL}"
    
    while [ $attempt -le $max_attempts ]; do
        echo "Running database migrations (attempt $attempt of $max_attempts)..."
        
        # Try running migrations with explicit Flask app path
        if FLASK_APP=src.features.web_app.code poetry run flask db upgrade; then
            echo "Migrations completed successfully!"
            export DATABASE_URL="${original_db_url}"
            return 0
        else
            echo "Migration attempt $attempt failed"
            
            # If we haven't tried resetting and this isn't our last attempt
            if [ "$reset_attempted" = false ] && [ $attempt -lt $max_attempts ]; then
                echo "Attempting to reset migration state..."
                
                # Try to reset the alembic version to initial state
                if poetry run python -c "
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    # Check if table exists
    result = conn.execute(text(\"\"\"
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'alembic_version'
        )
    \"\"\")).scalar()
    
    if result:
        # Reset to initial revision
        conn.execute(text('DELETE FROM alembic_version'))
        conn.execute(text(\"INSERT INTO alembic_version VALUES ('1a2b3c4d5e6f')\"))
        conn.commit()
        print('Successfully reset migration state')
    else:
        print('No alembic_version table found - fresh database')
"; then
                    echo "Migration state reset successfully"
                    reset_attempted=true
                    attempt=1
                    continue
                else
                    echo "Failed to reset migration state"
                fi
            fi
            
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
    
    export DATABASE_URL="${original_db_url}"
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
        
        # Configure Gunicorn for Render
        echo "Starting web server with Render optimizations..."
        exec poetry run gunicorn \
            --bind 0.0.0.0:${PORT:-5000} \
            --workers ${GUNICORN_WORKERS:-2} \
            --threads ${GUNICORN_THREADS:-4} \
            --timeout ${GUNICORN_TIMEOUT:-30} \
            --access-logfile - \
            --error-logfile - \
            --log-level ${LOG_LEVEL:-info} \
            --preload \
            --worker-class gthread \
            --max-requests 1000 \
            --max-requests-jitter 50 \
            --keep-alive 5 \
            --worker-tmp-dir /dev/shm \
            "src.features.web_app.code:app"
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
