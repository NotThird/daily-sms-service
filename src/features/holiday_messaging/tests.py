"""Tests for the holiday messaging feature."""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.features.holiday_messaging.code import HolidayMessageService
from src.models import Recipient, UserConfig

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    return session

@pytest.fixture
def mock_rate_limiter():
    """Create a mock rate limiter."""
    limiter = Mock()
    limiter.check_rate_limit.return_value = True
    return limiter

@pytest.fixture
def mock_sms_service():
    """Create a mock SMS service."""
    service = Mock()
    service.send_message = Mock()
    return service

@pytest.fixture
def service(mock_db_session, mock_rate_limiter, mock_sms_service):
    """Create a HolidayMessageService with mocked dependencies."""
    with patch('src.features.holiday_messaging.code.RateLimiter', return_value=mock_rate_limiter), \
         patch('src.features.holiday_messaging.code.SMSService', return_value=mock_sms_service):
        service = HolidayMessageService(mock_db_session)
        return service

def test_generate_holiday_message():
    """Test holiday message generation with various inputs."""
    service = HolidayMessageService(Mock())
    
    # Test normal name
    message = service.generate_holiday_message("John Doe")
    assert "Dear John Doe" in message
    assert "🎄" in message
    assert "Happy Holidays" in message
    
    # Test input sanitization
    message = service.generate_holiday_message("John<script>alert(1)</script>")
    assert "John" in message
    assert "<script>" not in message
    
    # Test empty name
    message = service.generate_holiday_message("")
    assert "Dear" in message
    assert "Happy Holidays" in message

def test_get_active_recipients(service, mock_db_session):
    """Test filtering of active recipients."""
    # Setup mock recipients and configs
    mock_recipient1 = Mock(id=1, is_active=True, phone_number="+1234567890")
    mock_config1 = Mock(recipient_id=1, name="User1")
    mock_recipient2 = Mock(id=2, is_active=False, phone_number="+0987654321")
    mock_config2 = Mock(recipient_id=2, name="User2")
    mock_recipient3 = Mock(id=3, is_active=True, phone_number="+1122334455")
    mock_config3 = Mock(recipient_id=3, name="User3")
    
    mock_query = Mock()
    mock_query.join.return_value = mock_query
    mock_query.filter.return_value.all.return_value = [
        (mock_recipient1, mock_config1),
        (mock_recipient3, mock_config3)
    ]
    mock_db_session.query.return_value = mock_query
    
    # Get active recipients
    active_recipients = service.get_active_recipients()
    
    # Verify results
    assert len(active_recipients) == 2
    assert all(r[0].is_active for r in active_recipients)
    mock_db_session.query.assert_called_once_with(Recipient, UserConfig)

@pytest.mark.asyncio
async def test_send_bulk_messages(service, mock_rate_limiter, mock_sms_service):
    """Test bulk message sending with rate limiting."""
    # Setup mock recipients and configs
    mock_recipient1 = Mock(phone_number="+1234567890")
    mock_config1 = Mock(name="User1")
    mock_recipient2 = Mock(phone_number="+0987654321")
    mock_config2 = Mock(name="User2")
    
    service.get_active_recipients = Mock(return_value=[
        (mock_recipient1, mock_config1),
        (mock_recipient2, mock_config2)
    ])
    
    # Send messages
    result = await service.send_bulk_messages(batch_size=1)
    
    # Verify results
    assert result["total_recipients"] == 2
    assert result["messages_sent"] == 2
    assert result["messages_failed"] == 0
    assert "timestamp" in result
    
    # Verify rate limiting
    assert mock_rate_limiter.check_rate_limit.call_count == 2
    
    # Verify SMS sending
    assert mock_sms_service.send_message.call_count == 2

@pytest.mark.asyncio
async def test_send_bulk_messages_with_failures(service, mock_sms_service):
    """Test handling of SMS sending failures."""
    # Setup mock recipients and configs
    mock_recipient1 = Mock(phone_number="+1234567890")
    mock_config1 = Mock(name="User1")
    mock_recipient2 = Mock(phone_number="+0987654321")
    mock_config2 = Mock(name="User2")
    
    service.get_active_recipients = Mock(return_value=[
        (mock_recipient1, mock_config1),
        (mock_recipient2, mock_config2)
    ])
    
    # Make second SMS fail
    mock_sms_service.send_message.side_effect = [None, Exception("SMS failed")]
    
    # Send messages
    result = await service.send_bulk_messages()
    
    # Verify results
    assert result["total_recipients"] == 2
    assert result["messages_sent"] == 1
    assert result["messages_failed"] == 1

@pytest.mark.asyncio
async def test_rate_limit_stopping(service, mock_rate_limiter):
    """Test that sending stops when rate limit is reached."""
    # Setup mock recipients and configs
    mock_data = [
        (Mock(phone_number=f"+{i}"), Mock(name=f"User{i}"))
        for i in range(5)
    ]
    service.get_active_recipients = Mock(return_value=mock_data)
    
    # Make rate limit fail after first batch
    mock_rate_limiter.check_rate_limit.side_effect = [True, False]
    
    # Send messages with batch size of 2
    result = await service.send_bulk_messages(batch_size=2)
    
    # Verify only first batch was processed
    assert result["total_recipients"] == 5
    assert result["messages_sent"] == 2
