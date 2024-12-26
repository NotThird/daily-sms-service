# Core Feature

This feature provides the foundational database models and CLI utilities used throughout the application.

## Purpose

The core feature serves as the backbone of the application, providing:

- Database models using SQLAlchemy ORM
- Common CLI utilities and base commands
- Shared database operations and utilities

## Components

### Database Models (code.py)
- Defines SQLAlchemy models for all database entities
- Implements base model with common functionality
- Provides database session management

### CLI Utilities (cli.py)
- Implements common CLI commands
- Provides base CLI functionality
- Handles CLI configuration and setup

## Usage

### Using Database Models

```python
from features.core.code import User, Message, db_session

# Create a new user
with db_session() as session:
    user = User(name="John Doe", email="john@example.com")
    session.add(user)
    session.commit()
```

### Using CLI Utilities

```python
from features.core.cli import base_command

@base_command()
def my_command(ctx):
    """My custom command."""
    # Command implementation
```

## Dependencies

### Internal Dependencies
- None (core feature)

### External Dependencies
- SQLAlchemy: Database ORM and models
- Click: CLI framework (optional)

## Testing

The feature includes comprehensive tests covering:
- Database model operations
- CLI functionality
- Edge cases and error handling

```bash
# Run core feature tests
pytest src/features/core/tests.py
