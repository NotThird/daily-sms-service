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

echo "Installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive

retry apt-get update
retry apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    build-essential \
    libpq-dev \
    python3-dev \
    git \
    procps \
    gettext-base \
    netcat-openbsd \
    postgresql-client

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
