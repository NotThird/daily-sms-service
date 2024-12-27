#!/bin/bash
set -eo pipefail

echo "Starting build process..."

# Function to retry commands
retry() {
    local n=1
    local max=3
    local delay=2
    while true; do
        echo "Attempt $n/$max: $@"
        if "$@"; then
            break
        else
            if [[ $n -lt $max ]]; then
                ((n++))
                echo "Command failed. Attempt $n/$max:"
                sleep $delay;
            else
                echo "The command has failed after $n attempts."
                return 1
            fi
        fi
    done
}

echo "Setting up apt and PostgreSQL repository..."
export DEBIAN_FRONTEND=noninteractive

# Install certificates and gnupg
retry apt-get update
retry apt-get install -y --no-install-recommends ca-certificates gnupg

# Add PostgreSQL repository
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt bullseye-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /etc/apt/trusted.gpg.d/postgresql.gpg

echo "Installing system dependencies..."
retry apt-get clean
retry rm -rf /var/lib/apt/lists/*
retry apt-get update
retry apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    python3-dev \
    git \
    procps \
    gettext-base \
    netcat \
    pgbouncer

echo "Cleaning up apt..."
retry apt-get clean
retry rm -rf /var/lib/apt/lists/*

echo "Installing Poetry..."
retry curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="/root/.local/bin:$PATH"
export POETRY_HOME="/opt/poetry"
export POETRY_VERSION=1.6.1
export POETRY_VIRTUALENVS_CREATE=false
export POETRY_NO_INTERACTION=1

echo "Installing Python dependencies..."
retry poetry install --only main --no-interaction --no-ansi

echo "Setting up permissions..."
chmod +x docker-entrypoint.sh

echo "Build completed successfully!"
