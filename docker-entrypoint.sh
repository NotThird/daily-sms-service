#!/bin/bash
set -e

# Parse DATABASE_URL into PgBouncer environment variables
parse_db_url() {
    if [[ -z "${DATABASE_URL}" ]]; then
        echo "ERROR: DATABASE_URL is not set"
        exit 1
    fi

    # Extract components from DATABASE_URL
    if [[ "${DATABASE_URL}" =~ ^postgres(ql)?://([^:]+):([^@]+)@([^:/]+)(:([0-9]+))?/([^?[:space:]]+) ]]; then
        export DB_USER="${BASH_REMATCH[2]}"
        export DB_PASSWORD="${BASH_REMATCH[3]}"
        export DB_HOST="${BASH_REMATCH[4]}"
        export DB_PORT="${BASH_REMATCH[6]:-5432}"  # Default to 5432 if port not specified
        export DB_NAME="${BASH_REMATCH[7]}"
        
        # Debug: Print extracted components (without password)
        echo "DEBUG: Successfully parsed DATABASE_URL"
        echo "  User: ${DB_USER}"
        echo "  Host: ${DB_HOST}"
        echo "  Port: ${DB_PORT}"
        echo "  Database: ${DB_NAME}"
    else
        echo "ERROR: Invalid DATABASE_URL format"
        echo "Expected format: postgresql://user:password@host:port/database"
        exit 1
    fi
}

# Start PgBouncer
start_pgbouncer() {
    echo "Starting PgBouncer..."
    
    # Create userlist.txt with proper permissions
    echo "\"${DB_USER}\" \"${DB_PASSWORD}\"" > /etc/pgbouncer/userlist.txt
    chmod 600 /etc/pgbouncer/userlist.txt
    
    # Replace environment variables in config
    envsubst < /etc/pgbouncer/pgbouncer.ini > /etc/pgbouncer/pgbouncer.ini.tmp
    mv /etc/pgbouncer/pgbouncer.ini.tmp /etc/pgbouncer/pgbouncer.ini
    chmod 600 /etc/pgbouncer/pgbouncer.ini
    
    echo "Starting PgBouncer daemon..."
    # Start PgBouncer in background with verbose logging
    pgbouncer -v -u app /etc/pgbouncer/pgbouncer.ini &
    
    # Wait for PgBouncer to start and verify it's listening
    local max_attempts=10
    local attempt=1
    while [ $attempt -le $max_attempts ]; do
        if nc -z localhost 5432; then
            echo "PgBouncer is listening on port 5432"
            return 0
        fi
        echo "Waiting for PgBouncer to start (attempt $attempt/$max_attempts)..."
        sleep 1
        attempt=$((attempt + 1))
    done
    
    echo "ERROR: PgBouncer failed to start"
    return 1
}

# Function to wait for database with increased timeout and PgBouncer support
wait_for_db() {
    echo "Waiting for database..."
    local max_attempts=30
    local attempt=1
    local wait_time=2
    
    # Set connection string to use PgBouncer
    local PGBOUNCER_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"
    
    while [ $attempt -le $max_attempts ]; do
        echo "Database connection attempt $attempt of $max_attempts..."
        if poetry run python -c "
import sys
import psycopg2
import os
from time import sleep

try:
    conn = psycopg2.connect(
        '${PGBOUNCER_URL}',
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

# Function to run migrations with improved retry logic and PgBouncer support
run_migrations() {
    local max_attempts=5
    local attempt=1
    local wait_time=5
    local reset_attempted=false
    
    # Set DATABASE_URL to use PgBouncer
    local original_db_url="${DATABASE_URL}"
    export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@localhost:5432/${DB_NAME}"
    
    while [ $attempt -le $max_attempts ]; do
        echo "Running database migrations (attempt $attempt of $max_attempts)..."
        
        # Try running migrations
        if poetry run flask db upgrade; then
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
        # Parse DATABASE_URL and setup PgBouncer environment
        parse_db_url
        
        # Start PgBouncer
        start_pgbouncer
        
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
            "src.app:app"
        ;;
        
    test)
        # Parse DATABASE_URL and setup PgBouncer environment
        parse_db_url
        
        # Start PgBouncer
        start_pgbouncer
        
        # Wait for database before running tests
        wait_for_db
        
        echo "Running tests..."
        exec poetry run pytest "${@:2}"
        ;;
        
    shell)
        # Parse DATABASE_URL and setup PgBouncer environment
        parse_db_url
        
        # Start PgBouncer
        start_pgbouncer
        
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
