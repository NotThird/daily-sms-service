"""
Tests for user management functionality.
Covers configuration, onboarding, and CLI operations.
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import pytz
from datetime import datetime
from .config import UserConfig
from .onboarding import OnboardingManager
from .cli import add_user, update_preferences, list_users
from features.core.code import User, db_session

# Test data
TEST_USER_DATA = {
    "name": "Test User",
    "phone_number": "+1234567890",
    "timezone": "America/New_York",
    "delivery_time": "14:00"
}

TEST_PREFERENCES = {
    "topics": ["motivation", "growth"],
    "tone": "uplifting",
    "frequency": "daily"
}

@pytest.fixture
def db():
    """Create test database session."""
    with db_session() as session:
        yield session

@pytest.fixture
def user_config():
    """Create test user configuration."""
    return UserConfig(user_id=1)

@pytest.fixture
def onboarding_manager():
    """Create test onboarding manager."""
    return OnboardingManager()

@pytest.fixture
def cli_runner():
    """Create CLI test runner."""
    return CliRunner()

def test_config_load(user_config, db):
    """Test loading user configuration."""
    # Create test user with preferences
    user = User(id=1, **TEST_USER_DATA)
    db.add(user)
    db.commit()
    
    config = UserConfig.load(user_id=1)
    
    assert config.timezone == TEST_USER_DATA["timezone"]
    assert config.delivery_time == TEST_USER_DATA["delivery_time"]

def test_config_update(user_config):
    """Test updating user preferences."""
    user_config.update_preferences(TEST_PREFERENCES)
    
    assert user_config.topics == TEST_PREFERENCES["topics"]
    assert user_config.tone == TEST_PREFERENCES["tone"]
    assert user_config.frequency == TEST_PREFERENCES["frequency"]

def test_config_validation(user_config):
    """Test configuration validation."""
    # Test invalid timezone
    with pytest.raises(ValueError):
        user_config.update_preferences({"timezone": "Invalid/Zone"})
    
    # Test invalid delivery time
    with pytest.raises(ValueError):
        user_config.update_preferences({"delivery_time": "25:00"})

def test_config_persistence(user_config, db):
    """Test configuration persistence."""
    user_config.update_preferences(TEST_PREFERENCES)
    user_config.save()
    
    # Reload configuration
    new_config = UserConfig.load(user_id=1)
    assert new_config.topics == TEST_PREFERENCES["topics"]

def test_onboarding_start(onboarding_manager, db):
    """Test starting user onboarding."""
    with patch('features.notification_system.sms.send_message') as mock_send:
        result = onboarding_manager.start_onboarding(
            phone_number=TEST_USER_DATA["phone_number"],
            initial_preferences=TEST_PREFERENCES
        )
        
        assert result.success is True
        mock_send.assert_called_once()  # Welcome message sent

def test_onboarding_duplicate(onboarding_manager, db):
    """Test handling duplicate onboarding."""
    # Create existing user
    user = User(phone_number=TEST_USER_DATA["phone_number"])
    db.add(user)
    db.commit()
    
    result = onboarding_manager.start_onboarding(
        phone_number=TEST_USER_DATA["phone_number"]
    )
    
    assert result.success is False
    assert "already registered" in result.message

def test_onboarding_validation(onboarding_manager):
    """Test onboarding input validation."""
    # Test invalid phone number
    with pytest.raises(ValueError):
        onboarding_manager.start_onboarding(phone_number="invalid")
    
    # Test missing required preferences
    with pytest.raises(ValueError):
        onboarding_manager.start_onboarding(
            phone_number=TEST_USER_DATA["phone_number"],
            initial_preferences={"invalid": "preferences"}
        )

def test_cli_add_user(cli_runner):
    """Test CLI add user command."""
    result = cli_runner.invoke(add_user, [
        '--phone', TEST_USER_DATA["phone_number"],
        '--name', TEST_USER_DATA["name"],
        '--timezone', TEST_USER_DATA["timezone"]
    ])
    
    assert result.exit_code == 0
    assert "User added successfully" in result.output

def test_cli_update_preferences(cli_runner):
    """Test CLI update preferences command."""
    result = cli_runner.invoke(update_preferences, [
        '--user-id', '1',
        '--timezone', 'America/Los_Angeles',
        '--delivery-time', '15:00'
    ])
    
    assert result.exit_code == 0
    assert "Preferences updated" in result.output

def test_cli_list_users(cli_runner, db):
    """Test CLI list users command."""
    # Add test users
    users = [
        User(name=f"User {i}", phone_number=f"+1234567890{i}")
        for i in range(3)
    ]
    db.add_all(users)
    db.commit()
    
    result = cli_runner.invoke(list_users)
    
    assert result.exit_code == 0
    assert all(user.name in result.output for user in users)

def test_cli_error_handling(cli_runner):
    """Test CLI error handling."""
    # Test invalid phone number
    result = cli_runner.invoke(add_user, [
        '--phone', 'invalid',
        '--name', TEST_USER_DATA["name"]
    ])
    assert result.exit_code != 0
    assert "Invalid phone number" in result.output

def test_timezone_conversion(user_config):
    """Test timezone handling."""
    # Update timezone
    user_config.update_preferences({
        "timezone": "America/Los_Angeles",
        "delivery_time": "14:00"
    })
    
    # Convert delivery time to UTC
    utc_time = user_config.get_utc_delivery_time()
    assert isinstance(utc_time, datetime)
    assert utc_time.tzinfo == pytz.UTC

def test_bulk_operations(cli_runner):
    """Test bulk user operations."""
    # Create test data file
    with cli_runner.isolated_filesystem():
        with open('users.csv', 'w') as f:
            f.write("name,phone_number,timezone\n")
            for i in range(5):
                f.write(f"User {i},+1234567890{i},UTC\n")
        
        result = cli_runner.invoke(add_user, ['--file', 'users.csv'])
        
        assert result.exit_code == 0
        assert "5 users added" in result.output

def test_audit_logging(user_config):
    """Test audit logging for user operations."""
    with patch('logging.Logger.info') as mock_log:
        user_config.update_preferences(TEST_PREFERENCES)
        
        # Verify audit log was created
        mock_log.assert_called_with(
            "User preferences updated",
            extra={"user_id": 1, "changes": TEST_PREFERENCES}
        )
