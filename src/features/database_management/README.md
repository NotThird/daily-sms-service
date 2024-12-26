# Database Management Feature

This feature provides robust database management capabilities for handling Render's PostgreSQL database migrations and maintenance operations.

## Purpose

The database management feature is designed to handle the required 90-day database recreation process for Render's free tier PostgreSQL databases. It provides secure and efficient tools for:

- Database backup using pg_dump
- Database restoration using pg_restore
- New database creation
- Complete migration workflow

## Usage

### Basic Migration

```python
from features.database_management.code import migrate_database

# Perform database migration
success = migrate_database(
    source_url="postgresql://user:pass@source-db:5432/db",
    target_url="postgresql://user:pass@target-db:5432/db",
    admin_url="postgresql://admin:pass@admin-db:5432/postgres",
    db_name="new_database"
)
```

### Using DatabaseManager Directly

```python
from features.database_management.code import DatabaseManager

# Initialize manager with custom timeouts
manager = DatabaseManager(
    admin_url="postgresql://admin:pass@admin-db:5432/postgres",
    connect_timeout=30,  # Connection timeout in seconds
    command_timeout=600  # Command execution timeout in seconds
)

# Backup database
manager.backup_database(
    source_url="postgresql://user:pass@source-db:5432/db",
    backup_file="backup.dump"
)

# Create new database
manager.create_database("new_database")

# Restore from backup
manager.restore_database(
    target_url="postgresql://user:pass@target-db:5432/new_database",
    backup_file="backup.dump"
)
```

## Logic

The feature implements a three-step migration process:

1. **Backup**: Creates a backup of the source database using pg_dump with custom format (-Fc) for better performance
2. **Create**: Creates a new target database with proper security checks
3. **Restore**: Restores the backup to the new database using pg_restore

### Security Practices

1. **SQL Injection Prevention**: Uses parameterized database operations for all SQL queries
2. **Strict Permission Control**: Implements admin credential checks through dedicated admin connection URL

### Performance & Reliability Features

1. **Efficient Transfer Format**: Uses PostgreSQL's custom format (-Fc) for faster backup and restore operations
2. **Timeout Controls**: Implements configurable timeouts for improved reliability
   - Connection timeout: Controls database connection attempts (default: 30s)
   - Command timeout: Limits long-running operations (default: 600s)
   - Applied to all database operations and CLI commands

## Testing

The feature includes comprehensive tests covering both typical usage and edge cases:

```bash
# Run tests
pytest src/features/database_management/tests.py
```

Test coverage includes:
- Successful backup/restore operations
- Failed operations handling
- Database creation scenarios
- Complete migration workflow
- Edge cases and error conditions

### Test Requirements

- pytest
- unittest.mock for mocking database operations
- PostgreSQL client tools (pg_dump, pg_restore) for integration tests

## Dependencies

- psycopg2: PostgreSQL database adapter for Python
- subprocess: For executing PostgreSQL client tools
- Python 3.6+ for type hints support

## Configuration

### Timeout Settings

The DatabaseManager supports two types of timeouts:

1. **Connection Timeout** (connect_timeout):
   - Controls how long to wait for database connections
   - Default: 30 seconds
   - Adjust for slow network conditions

2. **Command Timeout** (command_timeout):
   - Limits duration of database operations
   - Default: 600 seconds (10 minutes)
   - Increase for large databases
   - Applied to:
     * pg_dump operations
     * pg_restore operations
     * Database creation
     * General queries
