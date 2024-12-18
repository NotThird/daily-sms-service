import pytest
from unittest.mock import Mock, patch
from twilio.base.exceptions import TwilioRestException
from src.sms_service import SMSService

@pytest.fixture
def mock_account():
    return Mock(friendly_name="Test Account")

@pytest.fixture
def sms_service(mock_account):
    with patch('twilio.rest.Client') as MockClient:
        # Mock account validation
        MockClient.return_value.api.accounts.return_value.fetch.return_value = mock_account
        service = SMSService(
            account_sid="fake_sid",
            auth_token="fake_token",
            from_number="+1234567890"
        )
        return service

def test_init_validates_credentials(mock_account):
    with patch('twilio.rest.Client') as MockClient:
        # Mock successful validation
        MockClient.return_value.api.accounts.return_value.fetch.return_value = mock_account
        
        service = SMSService("fake_sid", "fake_token", "+1234567890")
        assert service is not None

def test_init_missing_credentials():
    with pytest.raises(ValueError, match="Missing required credentials"):
        SMSService("", "fake_token", "+1234567890")

def test_init_invalid_credentials():
    with patch('twilio.rest.Client') as MockClient:
        # Mock validation failure
        MockClient.return_value.api.accounts.return_value.fetch.side_effect = \
            Exception("Invalid credentials")
        
        with pytest.raises(ValueError, match="Failed to validate Twilio credentials"):
            SMSService("fake_sid", "fake_token", "+1234567890")

def test_send_message_success(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock successful message send
        mock_message = Mock(
            sid='MSG123',
            status='queued',
            from_='+1234567890',
            to='+1987654321',
            direction='outbound-api',
            price='0.07',
            price_unit='USD'
        )
        MockClient.return_value.messages.create.return_value = mock_message
        
        # Mock status polling
        mock_status = {
            'status': 'delivered',
            'error_code': None,
            'error_message': None,
            'direction': 'outbound-api',
            'from_number': '+1234567890',
            'to_number': '+1987654321',
            'price': '0.07',
            'price_unit': 'USD',
            'date_sent': '2023-09-15T12:00:00Z',
            'date_updated': '2023-09-15T12:01:00Z'
        }
        with patch.object(sms_service, '_poll_message_status', return_value=mock_status):
            result = sms_service.send_message("+1987654321", "Test message")
            
            assert result['status'] == 'success'
            assert result['message_sid'] == 'MSG123'
            assert result['delivery_status'] == 'delivered'
            assert result['from_number'] == '+1234567890'
            assert result['to_number'] == '+1987654321'
            assert result['price'] == '0.07'
            assert result['price_unit'] == 'USD'

def test_send_message_twilio_error(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock Twilio error
        error = TwilioRestException(
            uri='fake_uri',
            msg='Invalid phone number',
            code=21211,
            status=400
        )
        MockClient.return_value.messages.create.side_effect = error
        
        result = sms_service.send_message("+1987654321", "Test message")
        
        assert result['status'] == 'error'
        assert result['message_sid'] is None
        assert result['error_code'] == 21211
        assert 'Invalid phone number' in result['error']

def test_send_message_unexpected_error(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock unexpected error
        MockClient.return_value.messages.create.side_effect = Exception("Unexpected error")
        
        result = sms_service.send_message("+1987654321", "Test message")
        
        assert result['status'] == 'error'
        assert result['message_sid'] is None
        assert result['error_code'] is None
        assert 'Unexpected error' in result['error']

def test_poll_message_status(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock message status progression
        mock_statuses = [
            Mock(
                status='queued',
                error_code=None,
                error_message=None,
                direction='outbound-api',
                from_='+1234567890',
                to='+1987654321',
                price='0.07',
                price_unit='USD',
                date_sent='2023-09-15T12:00:00Z',
                date_updated='2023-09-15T12:00:00Z'
            ),
            Mock(
                status='delivered',
                error_code=None,
                error_message=None,
                direction='outbound-api',
                from_='+1234567890',
                to='+1987654321',
                price='0.07',
                price_unit='USD',
                date_sent='2023-09-15T12:00:00Z',
                date_updated='2023-09-15T12:01:00Z'
            )
        ]
        MockClient.return_value.messages.return_value.fetch.side_effect = mock_statuses
        
        result = sms_service._poll_message_status('MSG123', max_attempts=2, delay=0)
        
        assert result['status'] == 'delivered'
        assert result['from_number'] == '+1234567890'
        assert result['to_number'] == '+1987654321'
        assert result['price'] == '0.07'
        assert MockClient.return_value.messages.return_value.fetch.call_count == 2

def test_validate_phone_number_success(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock successful lookup
        MockClient.return_value.lookups.v2.phone_numbers.return_value.fetch.return_value = Mock()
        
        result = sms_service.validate_phone_number("+1987654321")
        
        assert result is True

def test_validate_phone_number_failure(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock lookup failure
        MockClient.return_value.lookups.v2.phone_numbers.return_value.fetch.side_effect = \
            Exception("Invalid number")
        
        result = sms_service.validate_phone_number("+1987654321")
        
        assert result is False

def test_process_delivery_status_success(sms_service):
    status_data = {
        'MessageSid': 'MSG123',
        'MessageStatus': 'delivered',
        'ErrorCode': None
    }
    
    result = sms_service.process_delivery_status(status_data)
    
    assert result['processed'] is True
    assert result['message_sid'] == 'MSG123'
    assert result['status'] == 'delivered'
    assert result['error_code'] is None

def test_process_delivery_status_failure(sms_service):
    status_data = {
        'MessageSid': 'MSG123',
        'MessageStatus': 'failed',
        'ErrorCode': '30001'
    }
    
    result = sms_service.process_delivery_status(status_data)
    
    assert result['processed'] is True
    assert result['message_sid'] == 'MSG123'
    assert result['status'] == 'failed'
    assert result['error_code'] == '30001'

def test_process_delivery_status_invalid_data(sms_service):
    status_data = {}  # Invalid/empty data
    
    result = sms_service.process_delivery_status(status_data)
    
    assert result['processed'] is False
    assert 'error' in result

def test_get_message_status_success(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock message status
        mock_message = Mock(
            status='delivered',
            error_code=None,
            error_message=None,
            direction='outbound-api',
            from_='+1234567890',
            to='+1987654321',
            price='0.07',
            price_unit='USD',
            date_sent='2023-09-15T12:00:00Z',
            date_updated='2023-09-15T12:01:00Z'
        )
        MockClient.return_value.messages.return_value.fetch.return_value = mock_message
        
        result = sms_service.get_message_status('MSG123')
        
        assert result['status'] == 'delivered'
        assert result['error_code'] is None
        assert result['error_message'] is None
        assert result['direction'] == 'outbound-api'
        assert result['from_number'] == '+1234567890'
        assert result['to_number'] == '+1987654321'
        assert result['price'] == '0.07'
        assert result['price_unit'] == 'USD'
        assert result['date_sent'] == '2023-09-15T12:00:00Z'
        assert result['date_updated'] == '2023-09-15T12:01:00Z'

def test_get_message_status_error(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock error fetching status
        MockClient.return_value.messages.return_value.fetch.side_effect = \
            Exception("Failed to fetch status")
        
        result = sms_service.get_message_status('MSG123')
        
        assert result['status'] == 'error'
        assert 'Failed to fetch status' in result['error_message']

def test_retry_on_temporary_failure(sms_service):
    with patch('twilio.rest.Client') as MockClient:
        # Mock temporary failure then success
        mock_message = Mock(sid='MSG123')
        MockClient.return_value.messages.create.side_effect = [
            TwilioRestException(
                uri='fake_uri',
                msg='Service unavailable',
                code=503,
                status=503
            ),
            mock_message
        ]
        
        # Mock status polling for successful case
        mock_status = {
            'status': 'delivered',
            'error_code': None,
            'error_message': None,
            'direction': 'outbound-api',
            'from_number': '+1234567890',
            'to_number': '+1987654321',
            'price': '0.07',
            'price_unit': 'USD',
            'date_sent': '2023-09-15T12:00:00Z',
            'date_updated': '2023-09-15T12:01:00Z'
        }
        with patch.object(sms_service, '_poll_message_status', return_value=mock_status):
            result = sms_service.send_message("+1987654321", "Test message")
            
            assert result['status'] == 'success'
            assert result['message_sid'] == 'MSG123'
            assert MockClient.return_value.messages.create.call_count == 2
