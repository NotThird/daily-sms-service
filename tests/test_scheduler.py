import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import pytz
from src.scheduler import MessageScheduler
from src.models import Recipient, ScheduledMessage, MessageLog

@pytest.fixture
def mock_db_session():
    return Mock()

@pytest.fixture
def mock_message_generator():
    return Mock()

@pytest.fixture
def mock_sms_service():
    return Mock()

@pytest.fixture
def scheduler(mock_db_session, mock_message_generator, mock_sms_service):
    return MessageScheduler(
        mock_db_session,
        mock_message_generator,
        mock_sms_service
    )

def test_schedule_daily_messages_success(scheduler, mock_db_session):
    # Mock active recipients
    recipient1 = Mock(spec=Recipient, id=1, timezone='UTC')
    recipient2 = Mock(spec=Recipient, id=2, timezone='America/New_York')
    mock_db_session.query.return_value.filter_by.return_value.all.return_value = [
        recipient1, recipient2
    ]
    
    result = scheduler.schedule_daily_messages()
    
    assert result['scheduled'] == 2
    assert result['failed'] == 0
    assert result['total'] == 2
    assert mock_db_session.add.call_count == 2
    mock_db_session.commit.assert_called_once()

def test_schedule_daily_messages_partial_failure(scheduler, mock_db_session):
    # Mock one successful and one failed recipient
    recipient1 = Mock(spec=Recipient, id=1, timezone='UTC')
    recipient2 = Mock(spec=Recipient, id=2, timezone='Invalid/Timezone')
    mock_db_session.query.return_value.filter_by.return_value.all.return_value = [
        recipient1, recipient2
    ]
    
    result = scheduler.schedule_daily_messages()
    
    assert result['scheduled'] == 1
    assert result['failed'] == 1
    assert result['total'] == 2
    mock_db_session.commit.assert_called_once()

def test_process_scheduled_messages_success(scheduler, mock_db_session, mock_message_generator, mock_sms_service):
    # Mock scheduled messages
    message1 = Mock(spec=ScheduledMessage, id=1, recipient_id=1)
    message2 = Mock(spec=ScheduledMessage, id=2, recipient_id=2)
    mock_db_session.query.return_value.filter.return_value.all.return_value = [
        message1, message2
    ]
    
    # Mock recipients
    recipient1 = Mock(spec=Recipient, id=1, phone_number='+1234567890', is_active=True)
    recipient2 = Mock(spec=Recipient, id=2, phone_number='+0987654321', is_active=True)
    mock_db_session.query.return_value.get.side_effect = [recipient1, recipient2]
    
    # Mock message generation and sending
    mock_message_generator.generate_message.return_value = "Test message"
    mock_sms_service.send_message.return_value = {
        'status': 'success',
        'message_sid': 'MSG123'
    }
    
    result = scheduler.process_scheduled_messages()
    
    assert result['sent'] == 2
    assert result['failed'] == 0
    assert result['total'] == 2
    assert mock_db_session.add.call_count == 2  # One MessageLog per successful send
    mock_db_session.commit.assert_called_once()

def test_process_scheduled_messages_inactive_recipient(scheduler, mock_db_session):
    # Mock scheduled message
    message = Mock(spec=ScheduledMessage, id=1, recipient_id=1)
    mock_db_session.query.return_value.filter.return_value.all.return_value = [message]
    
    # Mock inactive recipient
    recipient = Mock(spec=Recipient, id=1, is_active=False)
    mock_db_session.query.return_value.get.return_value = recipient
    
    result = scheduler.process_scheduled_messages()
    
    assert result['sent'] == 0
    assert result['failed'] == 0
    assert result['total'] == 1
    assert message.status == 'cancelled'
    mock_db_session.commit.assert_called_once()

def test_process_scheduled_messages_send_failure(scheduler, mock_db_session, mock_message_generator, mock_sms_service):
    # Mock scheduled message
    message = Mock(spec=ScheduledMessage, id=1, recipient_id=1)
    mock_db_session.query.return_value.filter.return_value.all.return_value = [message]
    
    # Mock active recipient
    recipient = Mock(spec=Recipient, id=1, phone_number='+1234567890', is_active=True)
    mock_db_session.query.return_value.get.return_value = recipient
    
    # Mock message generation and failed sending
    mock_message_generator.generate_message.return_value = "Test message"
    mock_sms_service.send_message.return_value = {
        'status': 'error',
        'error': 'Failed to send'
    }
    
    result = scheduler.process_scheduled_messages()
    
    assert result['sent'] == 0
    assert result['failed'] == 1
    assert result['total'] == 1
    assert message.status == 'failed'
    assert 'Failed to send' in message.error_message
    mock_db_session.commit.assert_called_once()

def test_generate_send_time(scheduler):
    timezone_str = 'UTC'
    send_time = scheduler._generate_send_time(timezone_str)
    
    assert isinstance(send_time, datetime)
    assert send_time.tzinfo == pytz.UTC
    
    # Convert to local time for testing window
    local_time = send_time.astimezone(pytz.timezone(timezone_str))
    assert 12 <= local_time.hour <= 16  # 12 PM to 4 PM (allowing for minutes)
    assert 0 <= local_time.minute <= 59

def test_get_recent_messages(scheduler, mock_db_session):
    # Mock recent message logs
    mock_logs = [
        Mock(spec=MessageLog, content="Message 1"),
        Mock(spec=MessageLog, content="Message 2")
    ]
    mock_db_session.query.return_value.filter.return_value.all.return_value = mock_logs
    
    recent_messages = scheduler._get_recent_messages(1, days=7)
    
    assert len(recent_messages) == 2
    assert "Message 1" in recent_messages
    assert "Message 2" in recent_messages

def test_cleanup_old_records(scheduler, mock_db_session):
    # Mock deletion results
    mock_db_session.query.return_value.filter.return_value.delete.side_effect = [5, 10]
    
    result = scheduler.cleanup_old_records(days=30)
    
    assert result['scheduled_messages_deleted'] == 5
    assert result['message_logs_deleted'] == 10
    mock_db_session.commit.assert_called_once()

def test_cleanup_old_records_failure(scheduler, mock_db_session):
    # Mock deletion failure
    mock_db_session.commit.side_effect = Exception("Database error")
    
    with pytest.raises(Exception):
        scheduler.cleanup_old_records(days=30)
    
    mock_db_session.rollback.assert_called_once()

def test_timezone_handling(scheduler):
    # Test various timezone strings
    timezones = ['UTC', 'America/New_York', 'Europe/London', 'Asia/Tokyo']
    
    for tz_str in timezones:
        send_time = scheduler._generate_send_time(tz_str)
        local_time = send_time.astimezone(pytz.timezone(tz_str))
        
        assert 12 <= local_time.hour <= 16
        assert isinstance(send_time, datetime)
        assert send_time.tzinfo == pytz.UTC

def test_invalid_timezone_handling(scheduler):
    with pytest.raises(Exception):
        scheduler._generate_send_time('Invalid/Timezone')

def test_database_transaction_rollback(scheduler, mock_db_session):
    # Mock database error during scheduling
    mock_db_session.commit.side_effect = Exception("Database error")
    
    with pytest.raises(Exception):
        scheduler.schedule_daily_messages()
    
    mock_db_session.rollback.assert_called_once()
