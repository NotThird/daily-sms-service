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
    POETRY_VIRTUALENVS_CREATE=false \
    PYTHONPATH=/app

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

# Copy the entire project
COPY . .

# Generate fresh poetry.lock and install dependencies
RUN poetry lock && poetry install --only main --no-interaction --no-ansi

# Create non-root user
RUN useradd -m -u 1000 app \
    && chown -R app:app /app
USER app

# Make entrypoint script executable
RUN chmod +x docker-entrypoint.sh

# Default command (can be overridden)
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["web"]
