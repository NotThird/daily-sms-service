"""
Tests for core functionality.
Covers database models, CLI utilities, and shared functionality.
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from click.testing import CliRunner
from .code import User, Message, db_session, Base
from .cli import base_command

# Test data
TEST_USER_DATA = {
    "name": "Test User",
    "email": "test@example.com"
}

TEST_MESSAGE_DATA = {
    "content": "Test message",
    "user_id": 1
}

@pytest.fixture
def db():
    """Create a test database session."""
    # Create all tables in test database
    Base.metadata.create_all()
    
    with db_session() as session:
        yield session
    
    # Clean up after tests
    Base.metadata.drop_all()

@pytest.fixture
def test_user(db):
    """Create a test user."""
    user = User(**TEST_USER_DATA)
    db.add(user)
    db.commit()
    return user

def test_user_creation(db):
    """Test creating a new user."""
    user = User(**TEST_USER_DATA)
    db.add(user)
    db.commit()
    
    assert user.id is not None
    assert user.name == TEST_USER_DATA["name"]
    assert user.email == TEST_USER_DATA["email"]

def test_user_retrieval(db, test_user):
    """Test retrieving a user."""
    retrieved_user = db.query(User).filter_by(id=test_user.id).first()
    
    assert retrieved_user is not None
    assert retrieved_user.name == test_user.name
    assert retrieved_user.email == test_user.email

def test_message_creation(db, test_user):
    """Test creating a new message."""
    message = Message(user_id=test_user.id, **TEST_MESSAGE_DATA)
    db.add(message)
    db.commit()
    
    assert message.id is not None
    assert message.content == TEST_MESSAGE_DATA["content"]
    assert message.user_id == test_user.id

def test_user_messages_relationship(db, test_user):
    """Test user-messages relationship."""
    message = Message(user_id=test_user.id, **TEST_MESSAGE_DATA)
    db.add(message)
    db.commit()
    
    assert len(test_user.messages) == 1
    assert test_user.messages[0].content == TEST_MESSAGE_DATA["content"]

def test_db_session_context_manager():
    """Test database session context manager."""
    with db_session() as session:
        assert isinstance(session, Session)
        # Session should be active
        assert session.is_active

    # Session should be closed after context
    assert not session.is_active

def test_db_session_error_handling():
    """Test database session error handling."""
    with pytest.raises(Exception):
        with db_session() as session:
            raise Exception("Test error")
    
    # Session should be rolled back and closed
    assert not session.is_active

@pytest.fixture
def cli_runner():
    """Create a CLI test runner."""
    return CliRunner()

def test_base_command_decorator(cli_runner):
    """Test base command decorator."""
    @base_command()
    def test_command(ctx):
        """Test command."""
        return "Command executed"
    
    result = cli_runner.invoke(test_command)
    assert result.exit_code == 0
    assert "Command executed" in result.output

def test_base_command_error_handling(cli_runner):
    """Test base command error handling."""
    @base_command()
    def error_command(ctx):
        """Command that raises an error."""
        raise Exception("Test error")
    
    result = cli_runner.invoke(error_command)
    assert result.exit_code != 0
    assert "Test error" in result.output

def test_user_validation():
    """Test user data validation."""
    # Test invalid email
    with pytest.raises(ValueError):
        User(name="Test", email="invalid-email")
    
    # Test missing required field
    with pytest.raises(ValueError):
        User(email="test@example.com")

def test_message_validation():
    """Test message data validation."""
    # Test empty content
    with pytest.raises(ValueError):
        Message(content="", user_id=1)
    
    # Test missing user_id
    with pytest.raises(ValueError):
        Message(content="Test message")

def test_base_model_timestamps(db):
    """Test automatic timestamp handling."""
    user = User(**TEST_USER_DATA)
    db.add(user)
    db.commit()
    
    assert user.created_at is not None
    assert user.updated_at is not None
    
    # Test update
    original_updated_at = user.updated_at
    user.name = "Updated Name"
    db.commit()
    
    assert user.updated_at > original_updated_at
