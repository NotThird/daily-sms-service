import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from src.features.holiday_automation.code import (
    HolidayAutomationService,
    HolidayConfig
)
from src.models import Recipient, UserConfig

def test_holiday_config_retrieval():
    """Test holiday configuration retrieval and caching."""
    service = HolidayAutomationService(Mock())
    
    # Test getting existing holiday
    config = service.get_holiday_config("New Year's Day")
    assert config is not None
    assert config.name == "New Year's Day"
    
    # Test caching (should hit cache)
    config_cached = service.get_holiday_config("New Year's Day")
    assert config_cached is config
    
    # Test unknown holiday
    assert service.get_holiday_config("Unknown Holiday") is None

def test_message_generation():
    """Test holiday message generation with various inputs."""
    service = HolidayAutomationService(Mock())
    holiday = service.DEFAULT_HOLIDAYS[0]  # New Year's
    
    # Test with full user config
    recipient = Recipient(id=1, phone_number="+1234567890", is_active=True)
    config = UserConfig(
        recipient_id=1,
        name="John Doe",
        preferences='{"interests": "photography and travel"}'
    )
    
    message = service._generate_holiday_message(holiday, recipient, config)
    assert "John Doe" in message
    assert "photography and travel" in message
    assert "2024" in message
    
    # Test with minimal config
    minimal_config = UserConfig(recipient_id=1)
    message = service._generate_holiday_message(holiday, recipient, minimal_config)
    assert "friend" in message
    assert "personal goals" in message
    
    # Test with no config
    message = service._generate_holiday_message(holiday, recipient, None)
    assert "friend" in message
    assert "personal goals" in message

def test_input_sanitization():
    """Test input sanitization for security."""
    service = HolidayAutomationService(Mock())
    
    # Test basic sanitization
    assert service._sanitize_input("John Doe") == "John Doe"
    
    # Test removal of special characters
    assert service._sanitize_input("John<script>alert(1)</script>") == "Johnscriptalert1script"
    
    # Test empty input
    assert service._sanitize_input("") == ""
    assert service._sanitize_input(None) == ""

@patch('src.features.holiday_automation.code.datetime')
def test_message_scheduling(mock_datetime):
    """Test holiday message scheduling functionality."""
    mock_db = Mock()
    mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
        (
            Recipient(id=1, phone_number="+1234567890", is_active=True),
            UserConfig(recipient_id=1, name="John Doe")
        ),
        (
            Recipient(id=2, phone_number="+0987654321", is_active=True),
            None
        )
    ]
    
    # Mock current time
    mock_now = datetime(2023, 12, 25, 12, 0)
    mock_datetime.utcnow.return_value = mock_now
    mock_datetime.fromisoformat.return_value = datetime(2024, 1, 1, 0, 0)
    
    service = HolidayAutomationService(mock_db)
    result = service.schedule_holiday_messages("New Year's Day")
    
    assert result["scheduled"] == 2
    assert result["failed"] == 0
    assert result["total"] == 2
    
    # Verify database calls
    assert mock_db.add.call_count == 2
    assert mock_db.commit.call_count == 1
