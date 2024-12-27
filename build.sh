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

echo "Setting up apt sources..."
export DEBIAN_FRONTEND=noninteractive
echo 'deb http://deb.debian.org/debian bullseye main' > /etc/apt/sources.list
echo 'deb http://security.debian.org/debian-security bullseye-security main' >> /etc/apt/sources.list
echo 'deb http://deb.debian.org/debian bullseye-updates main' >> /etc/apt/sources.list

echo "Installing system dependencies..."
retry apt-get clean
retry rm -rf /var/lib/apt/lists/*
retry apt-get update -y
retry apt-get install -y --no-install-recommends \
    curl=7.74.0-1.3+deb11u11 \
    build-essential \
    libpq-dev=13.12-0+deb11u1 \
    python3-dev \
    git=1:2.30.2-1+deb11u2 \
    procps=2:3.3.17-5 \
    gettext-base=0.21-4 \
    netcat=1.10-46 \
    pgbouncer=1.15.0-1+b1

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
