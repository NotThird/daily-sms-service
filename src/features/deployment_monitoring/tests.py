"""
Tests for deployment monitoring functionality.
Covers typical and edge cases for deployment verification.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
import requests
from .code import DeploymentVerifier, verify_deployment, with_retry

# Test data
TEST_URL = "https://api.example.com"
TEST_TWILIO_SID = "test_sid"
TEST_TWILIO_TOKEN = "test_token"

@pytest.fixture
def verifier():
    """Create a DeploymentVerifier instance for testing."""
    return DeploymentVerifier(TEST_URL, TEST_TWILIO_SID, TEST_TWILIO_TOKEN, max_retries=3)

def test_retry_decorator_success():
    """Test retry decorator with successful execution."""
    mock_func = MagicMock(return_value=True)
    decorated = with_retry(max_tries=3)(mock_func)
    
    result = decorated()
    
    assert result is True
    assert mock_func.call_count == 1

def test_retry_decorator_retry_success():
    """Test retry decorator with success after retries."""
    mock_func = MagicMock(side_effect=[Exception("Retry 1"), Exception("Retry 2"), True])
    decorated = with_retry(max_tries=3)(mock_func)
    
    result = decorated()
    
    assert result is True
    assert mock_func.call_count == 3

def test_retry_decorator_failure():
    """Test retry decorator with complete failure."""
    mock_func = MagicMock(side_effect=Exception("Failed"))
    decorated = with_retry(max_tries=3)(mock_func)
    
    result = decorated()
    
    assert result is False
    assert mock_func.call_count == 3

@pytest.fixture
def mock_response():
    """Create a mock response with healthy status."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {'status': 'healthy', 'database': {'connected': True}}
    return response

def test_verify_health_endpoint_success(verifier, mock_response):
    """Test successful health endpoint verification."""
    with patch.object(verifier.session, 'get', return_value=mock_response) as mock_get:
        assert verifier.verify_health_endpoint() is True
        assert mock_get.call_count == 1

def test_verify_health_endpoint_unhealthy(verifier, mock_response):
    """Test health endpoint reporting unhealthy status."""
    mock_response.json.return_value = {'status': 'unhealthy'}
    with patch.object(verifier.session, 'get', return_value=mock_response):
        assert verifier.verify_health_endpoint() is False

def test_verify_health_endpoint_retry_success(verifier, mock_response):
    """Test health endpoint verification succeeding after retries."""
    with patch.object(verifier.session, 'get') as mock_get:
        mock_get.side_effect = [
            requests.RequestException("Retry 1"),
            requests.RequestException("Retry 2"),
            mock_response
        ]
        
        assert verifier.verify_health_endpoint() is True
        assert mock_get.call_count == 3

def test_verify_health_endpoint_error(verifier):
    """Test health endpoint connection error with retries."""
    with patch.object(verifier.session, 'get', side_effect=requests.RequestException("Failed")):
        assert verifier.verify_health_endpoint() is False

def test_verify_webhook_authentication_success(verifier):
    """Test successful webhook authentication verification."""
    mock_response = MagicMock()
    mock_response.status_code = 403  # Expected when no signature
    
    with patch.object(verifier.session, 'post', return_value=mock_response) as mock_post:
        assert verifier.verify_webhook_authentication() is True
        assert mock_post.call_count == 1

def test_verify_webhook_authentication_retry_success(verifier):
    """Test webhook authentication verification succeeding after retries."""
    mock_response = MagicMock()
    mock_response.status_code = 403
    
    with patch.object(verifier.session, 'post') as mock_post:
        mock_post.side_effect = [
            requests.RequestException("Retry 1"),
            requests.RequestException("Retry 2"),
            mock_response
        ]
        
        assert verifier.verify_webhook_authentication() is True
        assert mock_post.call_count == 3

def test_verify_webhook_authentication_failure(verifier):
    """Test webhook authentication misconfiguration."""
    mock_response = MagicMock()
    mock_response.status_code = 200  # Unexpected when no signature
    
    with patch.object(verifier.session, 'post', return_value=mock_response):
        assert verifier.verify_webhook_authentication() is False

def test_verify_message_scheduling_success(verifier):
    """Test successful message scheduling verification."""
    mock_messages = [MagicMock(status='delivered') for _ in range(5)]
    
    with patch.object(verifier.twilio_client.messages, 'list', return_value=mock_messages):
        assert verifier.verify_message_scheduling() is True

def test_verify_message_scheduling_no_messages(verifier):
    """Test message scheduling with no recent messages."""
    with patch.object(verifier.twilio_client.messages, 'list', return_value=[]):
        assert verifier.verify_message_scheduling() is False

def test_verify_message_scheduling_with_failures(verifier):
    """Test message scheduling with some failed messages."""
    mock_messages = [
        MagicMock(status='delivered'),
        MagicMock(status='failed'),
        MagicMock(status='delivered')
    ]
    
    with patch.object(verifier.twilio_client.messages, 'list', return_value=mock_messages):
        # Should still return True as some messages were delivered
        assert verifier.verify_message_scheduling() is True

def test_verify_database_connection_success(verifier, mock_response):
    """Test successful database connection verification."""
    with patch.object(verifier.session, 'get', return_value=mock_response):
        assert verifier.verify_database_connection() is True

def test_verify_database_connection_failure(verifier, mock_response):
    """Test database connection failure."""
    mock_response.json.return_value = {'database': {'connected': False}}
    with patch.object(verifier.session, 'get', return_value=mock_response):
        assert verifier.verify_database_connection() is False

def test_verify_ssl_certificate_success(verifier):
    """Test successful SSL certificate verification."""
    mock_response = MagicMock()
    mock_response.raw.connection.sock.getpeercert.return_value = {
        'notAfter': (datetime.utcnow() + timedelta(days=60)).strftime('%b %d %H:%M:%S %Y GMT')
    }
    
    with patch('requests.get', return_value=mock_response):
        assert verifier.verify_ssl_certificate() is True

def test_verify_ssl_certificate_near_expiry(verifier):
    """Test SSL certificate near expiry."""
    mock_response = MagicMock()
    mock_response.raw.connection.sock.getpeercert.return_value = {
        'notAfter': (datetime.utcnow() + timedelta(days=20)).strftime('%b %d %H:%M:%S %Y GMT')
    }
    
    with patch('requests.get', return_value=mock_response):
        assert verifier.verify_ssl_certificate() is False

def test_verify_rate_limiting_success(verifier):
    """Test successful rate limiting verification."""
    responses = [MagicMock(status_code=200) for _ in range(45)]
    responses.extend([MagicMock(status_code=429) for _ in range(5)])  # Add some rate-limited responses
    
    with patch.object(verifier.session, 'get', side_effect=responses):
        assert verifier.verify_rate_limiting() is True

def test_verify_rate_limiting_disabled(verifier):
    """Test rate limiting verification when rate limiting is disabled."""
    responses = [MagicMock(status_code=200) for _ in range(50)]
    
    with patch.object(verifier.session, 'get', side_effect=responses):
        assert verifier.verify_rate_limiting() is False

def test_verify_logging_success(verifier):
    """Test successful logging verification."""
    with patch.object(verifier.session, 'post') as mock_post:
        assert verifier.verify_logging() is True
        mock_post.assert_called_once()

def test_verify_logging_failure(verifier):
    """Test logging verification failure."""
    with patch.object(verifier.session, 'post', side_effect=requests.RequestException):
        assert verifier.verify_logging() is False

def test_run_all_checks(verifier):
    """Test running all verification checks."""
    # Mock all verification methods to return True
    with patch.multiple(verifier,
        verify_health_endpoint=MagicMock(return_value=True),
        verify_webhook_authentication=MagicMock(return_value=True),
        verify_message_scheduling=MagicMock(return_value=True),
        verify_database_connection=MagicMock(return_value=True),
        verify_ssl_certificate=MagicMock(return_value=True),
        verify_rate_limiting=MagicMock(return_value=True),
        verify_logging=MagicMock(return_value=True)
    ):
        results = verifier.run_all_checks()
        assert all(results.values())
        assert len(results) == 7  # Verify all checks were run

def test_verify_deployment_success():
    """Test successful deployment verification."""
    with patch('features.deployment_monitoring.code.DeploymentVerifier') as MockVerifier:
        instance = MockVerifier.return_value
        instance.run_all_checks.return_value = {
            'health_endpoint': True,
            'webhook_authentication': True,
            'message_scheduling': True,
            'database_connection': True,
            'ssl_certificate': True,
            'rate_limiting': True,
            'logging': True
        }
        
        assert verify_deployment(TEST_URL, TEST_TWILIO_SID, TEST_TWILIO_TOKEN) is True

def test_verify_deployment_failure():
    """Test deployment verification failure."""
    with patch('features.deployment_monitoring.code.DeploymentVerifier') as MockVerifier:
        instance = MockVerifier.return_value
        instance.run_all_checks.return_value = {
            'health_endpoint': True,
            'webhook_authentication': False,  # One check fails
            'message_scheduling': True,
            'database_connection': True,
            'ssl_certificate': True,
            'rate_limiting': True,
            'logging': True
        }
        
        assert verify_deployment(TEST_URL, TEST_TWILIO_SID, TEST_TWILIO_TOKEN) is False
