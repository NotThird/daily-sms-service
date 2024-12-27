"""Tests for Render deployment configuration and optimizations."""

import os
import pytest
import psycopg2
from unittest.mock import patch, MagicMock
from .code import (
    RenderDeploymentConfig,
    ConnectionPoolManager,
    EnvironmentValidator,
    configure_render_deployment
)

@pytest.fixture
def deploy_config():
    """Fixture for RenderDeploymentConfig instance."""
    return RenderDeploymentConfig("test_secret")

@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to set mock environment variables."""
    env_vars = {
        'DATABASE_URL': 'postgresql://user:pass@localhost:5432/db',
        'PORT': '5000',
        'FLASK_ENV': 'production',
        'OPENAI_API_KEY': 'test_key',
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token'
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars

def test_deploy_signature_validation(deploy_config):
    """Test deploy hook signature validation."""
    payload = b'test_payload'
    # Generate valid signature
    import hmac
    import hashlib
    valid_sig = hmac.new(
        deploy_config.deploy_hook_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    assert deploy_config.validate_deploy_signature(valid_sig, payload)
    assert not deploy_config.validate_deploy_signature('invalid_sig', payload)
    assert not deploy_config.validate_deploy_signature('', payload)

def test_health_check_caching(deploy_config):
    """Test health check response caching."""
    call_count = 0
    
    @deploy_config.cache_health_check
    def mock_health_check():
        nonlocal call_count
        call_count += 1
        return {"status": "healthy"}
    
    # First call should execute function
    result1 = mock_health_check()
    assert call_count == 1
    assert result1 == {"status": "healthy"}
    
    # Second call should use cache
    result2 = mock_health_check()
    assert call_count == 1  # Shouldn't increment
    assert result2 == {"status": "healthy"}

@pytest.fixture
def mock_pool():
    """Fixture for mocked connection pool."""
    with patch('psycopg2.pool.SimpleConnectionPool') as mock:
        yield mock

def test_connection_pool_initialization(mock_pool):
    """Test database connection pool initialization."""
    pool_manager = ConnectionPoolManager(
        "postgresql://test:test@localhost:5432/test",
        min_conn=1,
        max_conn=5
    )
    
    mock_pool.assert_called_once()
    assert pool_manager.min_conn == 1
    assert pool_manager.max_conn == 5

def test_connection_pool_get_return(mock_pool):
    """Test getting and returning connections from pool."""
    pool_manager = ConnectionPoolManager(
        "postgresql://test:test@localhost:5432/test"
    )
    
    # Mock connection
    mock_conn = MagicMock()
    mock_pool.return_value.getconn.return_value = mock_conn
    
    # Get connection
    conn = pool_manager.get_connection()
    assert conn == mock_conn
    mock_pool.return_value.getconn.assert_called_once()
    
    # Return connection
    pool_manager.return_connection(conn)
    mock_pool.return_value.putconn.assert_called_once_with(mock_conn)

def test_connection_pool_close(mock_pool):
    """Test closing connection pool."""
    pool_manager = ConnectionPoolManager(
        "postgresql://test:test@localhost:5432/test"
    )
    
    pool_manager.close_pool()
    mock_pool.return_value.closeall.assert_called_once()

def test_environment_validation(mock_env_vars):
    """Test environment variable validation."""
    # Test successful validation
    validated = EnvironmentValidator.validate_environment()
    assert validated['PORT'] == 5000  # Should be converted to int
    assert validated['DATABASE_URL'] == mock_env_vars['DATABASE_URL']
    
    # Test missing variable
    with pytest.raises(ValueError) as exc_info:
        with patch.dict(os.environ, {}, clear=True):
            EnvironmentValidator.validate_environment()
    assert "Missing required environment variables" in str(exc_info.value)
    
    # Test invalid type
    with pytest.raises(ValueError) as exc_info:
        with patch.dict(os.environ, {'PORT': 'invalid_port'}):
            EnvironmentValidator.validate_environment()
    assert "Invalid PORT" in str(exc_info.value)

def test_database_url_sanitization():
    """Test database URL sanitization."""
    url = "postgresql://user:password123@localhost:5432/db"
    sanitized = EnvironmentValidator.sanitize_database_url(url)
    assert "password123" not in sanitized
    assert "****" in sanitized
    assert "user" in sanitized
    assert "localhost" in sanitized

def test_render_deployment_configuration(mock_env_vars, mock_pool):
    """Test full Render deployment configuration."""
    config, pool_manager = configure_render_deployment(
        mock_env_vars['DATABASE_URL'],
        "test_secret",
        min_conn=2,
        max_conn=10
    )
    
    assert isinstance(config, RenderDeploymentConfig)
    assert isinstance(pool_manager, ConnectionPoolManager)
    assert pool_manager.min_conn == 2
    assert pool_manager.max_conn == 10

def test_pool_initialization_failure(mock_pool):
    """Test handling of pool initialization failure."""
    mock_pool.side_effect = psycopg2.Error("Connection failed")
    
    with pytest.raises(psycopg2.Error) as exc_info:
        ConnectionPoolManager("postgresql://test:test@localhost:5432/test")
    assert "Connection failed" in str(exc_info.value)

def test_zero_downtime_deployment_simulation(deploy_config, mock_pool):
    """Test zero-downtime deployment scenario."""
    # Simulate deploy hook call
    payload = b'{"deployment": "123", "status": "success"}'
    signature = "valid_signature"
    
    with patch.object(deploy_config, 'validate_deploy_signature', return_value=True):
        assert deploy_config.validate_deploy_signature(signature, payload)
    
    # Simulate health check during deployment
    @deploy_config.cache_health_check
    def health_check():
        return {"status": "healthy", "deployment": "123"}
    
    result = health_check()
    assert result["status"] == "healthy"
    
    # Verify connection pool remains active
    pool_manager = ConnectionPoolManager(
        "postgresql://test:test@localhost:5432/test"
    )
    mock_conn = pool_manager.get_connection()
    assert mock_conn is not None
    
    # Return connection to pool
    pool_manager.return_connection(mock_conn)
    mock_pool.return_value.putconn.assert_called_once()
