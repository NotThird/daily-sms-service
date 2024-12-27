"""
---
title: Render Deployment Configuration
description: Manages Render-specific deployment configuration and optimizations
authors: System Team
date_created: 2024-01-25
dependencies:
  - psycopg2
  - requests
  - cachetools
---
"""

import os
import hmac
import hashlib
import time
from typing import Dict, Optional, Any
from cachetools import TTLCache
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import logging
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RenderDeploymentConfig:
    """Manages Render-specific deployment configuration and security."""
    
    def __init__(self, deploy_hook_secret: str):
        """
        Initialize deployment configuration.
        
        Args:
            deploy_hook_secret: Secret for validating Render deploy hooks
        """
        self.deploy_hook_secret = deploy_hook_secret
        self._health_cache = TTLCache(maxsize=100, ttl=60)  # Cache health checks for 60 seconds

    def validate_deploy_signature(self, signature: str, payload: bytes) -> bool:
        """
        Validate Render deploy hook signature.
        
        Args:
            signature: Signature from Render
            payload: Raw request payload
            
        Returns:
            bool: True if signature is valid
        """
        if not signature:
            return False
            
        expected = hmac.new(
            self.deploy_hook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)

    def cache_health_check(self, func):
        """Decorator to cache health check responses."""
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = 'health_status'
            if cache_key in self._health_cache:
                return self._health_cache[cache_key]
                
            result = func(*args, **kwargs)
            self._health_cache[cache_key] = result
            return result
        return wrapper

class ConnectionPoolManager:
    """Manages database connection pooling for Render PostgreSQL."""
    
    def __init__(
        self,
        database_url: str,
        min_conn: int = 2,
        max_conn: int = 10,
        **kwargs
    ):
        """
        Initialize connection pool manager.
        
        Args:
            database_url: Database connection URL
            min_conn: Minimum connections in pool
            max_conn: Maximum connections in pool
        """
        self.database_url = database_url
        self.pool = None
        self.min_conn = min_conn
        self.max_conn = max_conn
        self.pool_kwargs = kwargs
        self._initialize_pool()

    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self.pool = SimpleConnectionPool(
                self.min_conn,
                self.max_conn,
                self.database_url,
                **self.pool_kwargs
            )
            logger.info("Database connection pool initialized")
        except psycopg2.Error as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        if not self.pool:
            self._initialize_pool()
        return self.pool.getconn()

    def return_connection(self, conn):
        """Return a connection to the pool."""
        self.pool.putconn(conn)

    def close_pool(self):
        """Close all connections in the pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Database connection pool closed")

class EnvironmentValidator:
    """Validates and sanitizes environment variables for Render deployment."""
    
    REQUIRED_VARS = {
        'DATABASE_URL': str,
        'PORT': int,
        'FLASK_ENV': str,
        'OPENAI_API_KEY': str,
        'TWILIO_ACCOUNT_SID': str,
        'TWILIO_AUTH_TOKEN': str
    }
    
    @classmethod
    def validate_environment(cls) -> Dict[str, Any]:
        """
        Validate all required environment variables.
        
        Returns:
            Dict[str, Any]: Validated and typed environment variables
        """
        validated = {}
        missing = []
        
        for var, var_type in cls.REQUIRED_VARS.items():
            value = os.getenv(var)
            if value is None:
                missing.append(var)
                continue
                
            try:
                # Convert and validate type
                validated[var] = var_type(value)
            except ValueError as e:
                raise ValueError(f"Invalid {var}: {e}")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
            
        return validated

    @staticmethod
    def sanitize_database_url(url: str) -> str:
        """
        Sanitize database URL to remove sensitive information for logging.
        
        Args:
            url: Database URL
            
        Returns:
            str: Sanitized URL
        """
        try:
            # Remove password from URL
            parts = url.split('@')
            if len(parts) > 1:
                credentials = parts[0].split(':')
                if len(credentials) > 2:
                    # Hide password
                    credentials[2] = '****'
                    parts[0] = ':'.join(credentials)
                return '@'.join(parts)
            return url
        except Exception:
            return 'Invalid URL format'

def configure_render_deployment(
    database_url: str,
    deploy_hook_secret: str,
    min_conn: int = 2,
    max_conn: int = 10
) -> tuple[RenderDeploymentConfig, ConnectionPoolManager]:
    """
    Configure Render deployment with all optimizations.
    
    Args:
        database_url: Database connection URL
        deploy_hook_secret: Secret for deploy hooks
        min_conn: Minimum database connections
        max_conn: Maximum database connections
        
    Returns:
        tuple: (RenderDeploymentConfig, ConnectionPoolManager)
    """
    # Validate environment
    EnvironmentValidator.validate_environment()
    
    # Initialize deployment config
    config = RenderDeploymentConfig(deploy_hook_secret)
    
    # Initialize connection pool
    pool_manager = ConnectionPoolManager(
        database_url,
        min_conn=min_conn,
        max_conn=max_conn,
        connect_timeout=10
    )
    
    logger.info("Render deployment configured successfully")
    return config, pool_manager
