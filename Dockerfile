# Use Python 3.9 slim image as base
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
    PYTHONPATH=/app \
    PGBOUNCER_VERSION=1.18.0

# Install system dependencies and PgBouncer
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        libpq-dev \
        git \
        procps \
        gettext-base \
        netcat \
        pgbouncer \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Copy the project files
COPY . .

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-interaction --no-ansi

# Create PgBouncer configuration
RUN mkdir -p /etc/pgbouncer \
    && echo "[databases]" > /etc/pgbouncer/pgbouncer.ini \
    && echo "* = host=\${DB_HOST} port=\${DB_PORT} user=\${DB_USER} password=\${DB_PASSWORD} dbname=\${DB_NAME}" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "[pgbouncer]" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "pool_mode = transaction" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "listen_port = 5432" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "listen_addr = 127.0.0.1" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "unix_socket_dir = /tmp" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "max_client_conn = 1000" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "default_pool_size = 20" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "min_pool_size = 5" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "reserve_pool_size = 5" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "reserve_pool_timeout = 3" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "max_db_connections = 50" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "max_user_connections = 50" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "auth_type = md5" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "auth_file = /etc/pgbouncer/userlist.txt" >> /etc/pgbouncer/pgbouncer.ini \
    && echo "ignore_startup_parameters = extra_float_digits" >> /etc/pgbouncer/pgbouncer.ini

# Create non-root user
RUN useradd -m -u 1000 app \
    && chown -R app:app /app /etc/pgbouncer
USER app

# Make scripts executable
RUN chmod +x docker-entrypoint.sh

# Health check with improved parameters for Render
HEALTHCHECK --interval=30s --timeout=30s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT:-5000}/health || exit 1

# Default command (can be overridden)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
