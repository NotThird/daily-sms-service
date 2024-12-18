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

# Load AWS secrets if in production
if [ "$FLASK_ENV" = "production" ] && [ -n "$AWS_SECRETS_ARN" ]; then
    echo "Loading secrets from AWS Secrets Manager..."
    # AWS CLI is installed in the container and credentials are provided via IAM role
    secrets=$(aws secretsmanager get-secret-value --secret-id "$AWS_SECRETS_ARN" --query SecretString --output text)
    
    # Parse secrets and export as environment variables
    eval "$(echo "$secrets" | jq -r 'to_entries | .[] | "export \(.key)=\(.value)"')"
fi

case "$1" in
    web)
        # Wait for database before starting web server
        wait_for_db
        
        # Run migrations
        echo "Running database migrations..."
        poetry run alembic upgrade head
        
        # Start Gunicorn
        echo "Starting web server..."
        exec poetry run gunicorn \
            --bind 0.0.0.0:${PORT:-5000} \
            --workers ${GUNICORN_WORKERS:-2} \
            --threads ${GUNICORN_THREADS:-4} \
            --timeout ${GUNICORN_TIMEOUT:-30} \
            --access-logfile - \
            --error-logfile - \
            --log-level ${LOG_LEVEL:-info} \
            "src.app:app"
        ;;
        
    scheduler)
        # Wait for database before running scheduler
        wait_for_db
        
        echo "Running message scheduler..."
        exec poetry run python -m src.cli schedule_messages
        ;;
        
    processor)
        # Wait for database before running processor
        wait_for_db
        
        echo "Running message processor..."
        exec poetry run python -m src.cli process_messages
        ;;
        
    cleanup)
        # Wait for database before running cleanup
        wait_for_db
        
        echo "Running database cleanup..."
        exec poetry run python -m src.cli cleanup
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
