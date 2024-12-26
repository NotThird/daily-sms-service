"""
Tests for the notification system feature
"""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock
from .code import NotificationManager, NotificationEvent

@pytest.fixture
def notification_manager():
    return NotificationManager(admin_phone="8065351575")

def test_phone_sanitization():
    """Test phone number sanitization."""
    manager = NotificationManager()
    
    # Test valid formats
    assert manager._sanitize_phone("8065351575") == "8065351575"
    assert manager._sanitize_phone("1-806-535-1575") == "8065351575"
    assert manager._sanitize_phone("(806) 535-1575") == "8065351575"
    
    # Test invalid formats
    with pytest.raises(ValueError):
        manager._sanitize_phone("123")
    with pytest.raises(ValueError):
        manager._sanitize_phone("abcdefghij")

def test_message_formatting(notification_manager):
    """Test message template formatting."""
    event = NotificationEvent(
        event_type='signup',
        user_id='test123',
        message='Test message'
    )
    formatted = notification_manager._format_message(event)
    assert 'test123' in formatted
    assert '🎉' in formatted  # Check emoji included

@pytest.mark.asyncio
async def test_handle_user_signup(notification_manager):
    """Test user signup notification."""
    with patch('src.features.sms.send_sms', new_callable=AsyncMock) as mock_send:
        await notification_manager.handle_user_signup("test_user_123")
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert call_kwargs['to_number'] == "8065351575"
        assert "test_user_123" in call_kwargs['message']

@pytest.mark.asyncio
async def test_handle_message_receipt(notification_manager):
    """Test message receipt notification."""
    with patch('src.features.sms.send_sms', new_callable=AsyncMock) as mock_send:
        await notification_manager.handle_message_receipt("user123", "msg456")
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert "user123" in call_kwargs['message']
        assert "msg456" in call_kwargs['message']

@pytest.mark.asyncio
async def test_handle_system_alert(notification_manager):
    """Test system alert notification."""
    with patch('src.features.sms.send_sms', new_callable=AsyncMock) as mock_send:
        test_message = "Critical system event"
        await notification_manager.handle_system_alert(test_message)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args[1]
        assert test_message in call_kwargs['message']
        assert "⚠️" in call_kwargs['message']

@pytest.mark.asyncio
async def test_notification_error_handling(notification_manager):
    """Test graceful handling of SMS sending failures."""
    with patch('src.features.sms.send_sms', side_effect=Exception("SMS failed")):
        # Should not raise exception
        await notification_manager.handle_system_alert("Test alert")
