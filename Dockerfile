# Use Python 3.9 slim image as base (matching Render configuration)
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.6.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1 \
    PYTHONPATH=/app

# Install system dependencies (optimized for Render)
RUN set -ex && \
    echo "Setting up apt..." && \
    export DEBIAN_FRONTEND=noninteractive && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        libpq-dev \
        git \
        procps \
        gettext-base \
        netcat-openbsd \
        postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    echo "Package installation completed."

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Copy the project files
COPY . .

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-interaction --no-ansi && \
    poetry run pip install --no-cache-dir asgiref flask-migrate flask-sqlalchemy

# Create PostgreSQL client configuration directory
RUN mkdir -p /home/app/.postgresql && \
    touch /home/app/.postgresql/pgpass && \
    chmod 600 /home/app/.postgresql/pgpass

# Create non-root user
RUN useradd -m -u 1000 app && \
    chown -R app:app /app /home/app/.postgresql
USER app

# Make scripts executable
RUN chmod +x docker-entrypoint.sh

# Health check with improved parameters for Render
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Default command (can be overridden)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
