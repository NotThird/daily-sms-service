"""
Tests for web application functionality.
Covers routes, webhooks, health checks, and error handling.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from flask import url_for
from .code import create_app
from features.core.code import User, Message, db_session

@pytest.fixture
def app():
    """Create test application."""
    app = create_app(testing=True)
    return app

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def db():
    """Create test database session."""
    with db_session() as session:
        yield session

def test_health_check(client):
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'database' in data
    assert 'timestamp' in data

def test_health_check_database_error(client):
    """Test health check with database error."""
    with patch('features.core.code.db_session') as mock_session:
        mock_session.side_effect = Exception("Database error")
        
        response = client.get('/health')
        assert response.status_code == 503
        
        data = json.loads(response.data)
        assert data['status'] == 'unhealthy'
        assert data['database']['connected'] is False

@pytest.mark.parametrize('endpoint', [
    '/webhook/inbound',
    '/webhook/status'
])
def test_webhook_authentication(client, endpoint):
    """Test webhook authentication."""
    # Test without Twilio signature
    response = client.post(endpoint)
    assert response.status_code == 403
    
    # Test with invalid Twilio signature
    headers = {'X-Twilio-Signature': 'invalid'}
    response = client.post(endpoint, headers=headers)
    assert response.status_code == 403

def test_inbound_webhook_valid(client):
    """Test valid inbound webhook processing."""
    mock_data = {
        'From': '+1234567890',
        'Body': 'Test message'
    }
    
    with patch('features.web_app.code.validate_twilio_request', return_value=True):
        response = client.post('/webhook/inbound', json=mock_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True

def test_status_webhook_valid(client):
    """Test valid status webhook processing."""
    mock_data = {
        'MessageSid': 'test_sid',
        'MessageStatus': 'delivered'
    }
    
    with patch('features.web_app.code.validate_twilio_request', return_value=True):
        response = client.post('/webhook/status', json=mock_data)
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['success'] is True

def test_rate_limiting(client):
    """Test rate limiting functionality."""
    # Make multiple rapid requests
    responses = [
        client.get('/health')
        for _ in range(60)  # Exceed rate limit
    ]
    
    # Some requests should be rate limited
    assert any(r.status_code == 429 for r in responses)

def test_error_handling(client):
    """Test error handling."""
    # Test 404
    response = client.get('/nonexistent')
    assert response.status_code == 404
    
    # Test 500
    with patch('features.web_app.code.process_webhook', side_effect=Exception("Test error")):
        response = client.post('/webhook/inbound')
        assert response.status_code == 500

def test_csrf_protection(client):
    """Test CSRF protection."""
    # Test without CSRF token
    response = client.post('/protected-endpoint')
    assert response.status_code == 400
    
    # Test with invalid CSRF token
    headers = {'X-CSRF-Token': 'invalid'}
    response = client.post('/protected-endpoint', headers=headers)
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_async_webhook_processing(client):
    """Test asynchronous webhook processing."""
    mock_data = {
        'MessageSid': 'test_sid',
        'Body': 'Test message'
    }
    
    with patch('features.web_app.code.process_webhook_async') as mock_process:
        mock_process.return_value = True
        
        response = client.post('/webhook/inbound', json=mock_data)
        assert response.status_code == 202  # Accepted
        
        # Verify async processing was triggered
        mock_process.assert_called_once_with(mock_data)

def test_response_caching(client):
    """Test response caching."""
    # First request
    response1 = client.get('/cached-endpoint')
    assert response1.status_code == 200
    
    # Second request should hit cache
    with patch('features.web_app.code.expensive_operation') as mock_op:
        response2 = client.get('/cached-endpoint')
        assert response2.status_code == 200
        mock_op.assert_not_called()

def test_database_integration(client, db):
    """Test database integration."""
    # Create test user
    user = User(name="Test User", email="test@example.com")
    db.add(user)
    db.commit()
    
    # Test endpoint that uses database
    response = client.get(f'/users/{user.id}')
    assert response.status_code == 200
    
    data = json.loads(response.data)
    assert data['name'] == user.name
    assert data['email'] == user.email

def test_logging(client, caplog):
    """Test logging functionality."""
    with patch('features.web_app.code.logger') as mock_logger:
        # Trigger error
        client.get('/nonexistent')
        
        # Verify error was logged
        mock_logger.error.assert_called_once()
        assert "404 Not Found" in str(mock_logger.error.call_args)
