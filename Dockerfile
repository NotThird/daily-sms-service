# Use Python 3.9 slim image as base
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.4.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:${PATH}"

# Copy only pyproject.toml first to leverage Docker cache
COPY pyproject.toml ./

# Generate fresh poetry.lock
RUN poetry lock

# Install dependencies
RUN poetry install --only main --no-interaction --no-ansi

# Copy the rest of the application
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 app \
    && chown -R app:app /app
USER app

# Set up entrypoint script
COPY --chown=app:app docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Default command (can be overridden)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
