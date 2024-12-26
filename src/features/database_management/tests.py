"""
Tests for database management functionality.
Covers typical and edge cases for database operations.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from datetime import datetime
from .code import DatabaseManager, migrate_database

# Test data
TEST_ADMIN_URL = "postgresql://admin:password@localhost:5432/postgres"
TEST_SOURCE_URL = "postgresql://user:password@localhost:5432/source_db"
TEST_TARGET_URL = "postgresql://user:password@localhost:5432/target_db"
TEST_DB_NAME = "test_db"
TEST_BACKUP_FILE = "test_backup.dump"

@pytest.fixture
def db_manager():
    """Create a DatabaseManager instance for testing."""
    return DatabaseManager(
        TEST_ADMIN_URL,
        connect_timeout=5,  # Lower timeout for testing
        command_timeout=30
    )

def test_database_manager_init():
    """Test DatabaseManager initialization with custom timeouts."""
    manager = DatabaseManager(
        TEST_ADMIN_URL,
        connect_timeout=10,
        command_timeout=300
    )
    assert manager.connect_timeout == 10
    assert manager.command_timeout == 300

def test_backup_database_success(db_manager):
    """Test successful database backup."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = db_manager.backup_database(TEST_SOURCE_URL, TEST_BACKUP_FILE)
        
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'pg_dump'
        assert args[1] == '-Fc'
        assert TEST_BACKUP_FILE in args
        assert '--statement-timeout=30000' in args  # 30 seconds in milliseconds
        assert mock_run.call_args[1]['timeout'] == 30

def test_backup_database_failure(db_manager):
    """Test database backup failure."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, 'pg_dump')
        
        result = db_manager.backup_database(TEST_SOURCE_URL, TEST_BACKUP_FILE)
        
        assert result is False

def test_restore_database_success(db_manager):
    """Test successful database restore."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        
        result = db_manager.restore_database(TEST_TARGET_URL, TEST_BACKUP_FILE)
        
        assert result is True
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == 'pg_restore'
        assert '--clean' in args
        assert TEST_BACKUP_FILE in args
        assert '--statement-timeout=30000' in args  # 30 seconds in milliseconds
        assert mock_run.call_args[1]['timeout'] == 30

def test_restore_database_failure(db_manager):
    """Test database restore failure."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, 'pg_restore')
        
        result = db_manager.restore_database(TEST_TARGET_URL, TEST_BACKUP_FILE)
        
        assert result is False

def test_create_database_success(db_manager):
    """Test successful database creation."""
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    
    with patch('psycopg2.connect', return_value=mock_conn) as mock_connect:
        result = db_manager.create_database(TEST_DB_NAME)
        
        assert result is True
        mock_cursor.execute.assert_called_once()
        # Verify parameterized query was used
        args = mock_cursor.execute.call_args[0]
        assert 'CREATE DATABASE %s' in args[0]
        assert TEST_DB_NAME in args[1]
        # Verify timeout settings
        connect_args = mock_connect.call_args[1]
        assert connect_args['connect_timeout'] == 5
        assert 'statement_timeout=30000' in connect_args['options']

def test_create_database_failure(db_manager):
    """Test database creation failure."""
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.side_effect = psycopg2.Error("Connection failed")
        
        result = db_manager.create_database(TEST_DB_NAME)
        
        assert result is False
        # Verify timeout settings were attempted
        connect_args = mock_connect.call_args[1]
        assert connect_args['connect_timeout'] == 5
        assert 'statement_timeout=30000' in connect_args['options']

def test_create_database_timeout(db_manager):
    """Test database creation timeout."""
    with patch('psycopg2.connect') as mock_connect:
        mock_connect.side_effect = psycopg2.OperationalError("Connection timed out")
        
        result = db_manager.create_database(TEST_DB_NAME)
        
        assert result is False

def test_migrate_database_success():
    """Test successful complete migration process."""
    with patch('subprocess.run') as mock_run, \
         patch('psycopg2.connect') as mock_connect:
        
        mock_run.return_value.returncode = 0
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value = mock_conn
        
        result = migrate_database(
            TEST_SOURCE_URL,
            TEST_TARGET_URL,
            TEST_ADMIN_URL,
            TEST_DB_NAME
        )
        
        assert result is True
        # Verify all steps were called
        assert mock_run.call_count == 2  # backup and restore
        assert mock_connect.call_count == 1  # create database

def test_migrate_database_backup_failure():
    """Test migration failure during backup."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, 'pg_dump')
        
        result = migrate_database(
            TEST_SOURCE_URL,
            TEST_TARGET_URL,
            TEST_ADMIN_URL,
            TEST_DB_NAME
        )
        
        assert result is False
        assert mock_run.call_count == 1  # Only backup attempted

def test_migrate_database_create_failure():
    """Test migration failure during database creation."""
    with patch('subprocess.run') as mock_run, \
         patch('psycopg2.connect') as mock_connect:
        
        mock_run.return_value.returncode = 0
        mock_connect.side_effect = psycopg2.Error("Connection failed")
        
        result = migrate_database(
            TEST_SOURCE_URL,
            TEST_TARGET_URL,
            TEST_ADMIN_URL,
            TEST_DB_NAME
        )
        
        assert result is False
        assert mock_run.call_count == 1  # Only backup completed
