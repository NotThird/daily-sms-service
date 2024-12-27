#!/bin/bash
set -e

# Install system dependencies
apt-get update && apt-get install -y \
    curl \
    build-essential \
    libpq-dev \
    python3-dev

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
export PATH="/root/.local/bin:$PATH"

# Install dependencies
poetry install --only main --no-interaction --no-ansi

# Make scripts executable
chmod +x docker-entrypoint.sh
