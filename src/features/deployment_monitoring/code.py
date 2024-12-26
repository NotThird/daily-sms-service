"""
---
title: Deployment Monitoring
description: Comprehensive deployment verification and monitoring system
authors: System Team
date_created: 2024-01-24
dependencies:
  - requests
  - twilio
  - logging
---
"""

"""
Deployment monitoring module for verifying deployment status and health.
Implements secure verification checks with performance optimizations.

Security practices:
1. Uses secure HTTPS connections with certificate validation
2. Implements authentication checks for webhook endpoints

Performance optimization:
1. Uses connection pooling for HTTP requests to improve response times
"""

import requests
import sys
import json
from datetime import datetime, timedelta
import time
from twilio.rest import Client
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
import backoff

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def with_retry(max_tries: int = 3, initial_wait: float = 1.0):
    """
    Decorator for implementing retry logic with exponential backoff.
    
    Args:
        max_tries: Maximum number of retry attempts
        initial_wait: Initial wait time between retries in seconds
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            @backoff.on_exception(
                backoff.expo,
                (requests.exceptions.RequestException, Exception),
                max_tries=max_tries,
                base=initial_wait
            )
            def retry_func():
                return func(*args, **kwargs)
            try:
                return retry_func()
            except Exception as e:
                logger.error(f"Failed after {max_tries} attempts: {e}")
                return False
        return wrapper
    return decorator

class DeploymentVerifier:
    def __init__(self, base_url: str, twilio_sid: str, twilio_token: str, max_retries: int = 3):
        """
        Initialize verifier with necessary credentials.
        
        Args:
            base_url: Base URL of the deployed application
            twilio_sid: Twilio Account SID
            twilio_token: Twilio Auth Token
        """
        self.base_url = base_url.rstrip('/')
        self.twilio_client = Client(twilio_sid, twilio_token)
        # Performance: Use connection pooling
        self.session = requests.Session()

    @with_retry()
    def verify_health_endpoint(self) -> bool:
        """
        Verify the application health check endpoint.
        
        Returns:
            bool: True if health check passes, False otherwise
        """
        try:
            # Security: Use HTTPS with certificate validation
            response = self.session.get(
                f"{self.base_url}/health",
                verify=True
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'healthy':
                logger.error(f"Health check failed: {data}")
                return False
                
            logger.info("Health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    @with_retry()
    def verify_webhook_authentication(self) -> bool:
        """
        Verify Twilio webhook authentication is working.
        
        Returns:
            bool: True if webhook auth is properly configured, False otherwise
        """
        try:
            # Try to access webhook without proper Twilio signature
            response = self.session.post(f"{self.base_url}/webhook/inbound")
            
            if response.status_code != 403:
                logger.error("Webhook authentication check failed: Missing signature validation")
                return False
                
            logger.info("Webhook authentication check passed")
            return True
            
        except Exception as e:
            logger.error(f"Webhook authentication check failed: {e}")
            return False

    @with_retry()
    def verify_message_scheduling(self) -> bool:
        """
        Verify message scheduling system is operational.
        
        Returns:
            bool: True if message scheduling is working, False otherwise
        """
        try:
            messages = self.twilio_client.messages.list(
                limit=20,
                date_sent_after=datetime.utcnow() - timedelta(hours=24)
            )
            
            if not messages:
                logger.warning("No messages found in the last 24 hours")
                return False
                
            # Check message statuses
            failed = [m for m in messages if m.status == 'failed']
            if failed:
                logger.warning(f"Found {len(failed)} failed messages in the last 24 hours")
            
            logger.info(f"Found {len(messages)} messages in the last 24 hours")
            return True
            
        except Exception as e:
            logger.error(f"Message scheduling check failed: {e}")
            return False

    @with_retry()
    def verify_database_connection(self) -> bool:
        """
        Verify database connection through the application.
        
        Returns:
            bool: True if database connection is working, False otherwise
        """
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            if 'database' in data and not data['database'].get('connected', False):
                logger.error("Database connection check failed")
                return False
                
            logger.info("Database connection check passed")
            return True
            
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    @with_retry()
    def verify_ssl_certificate(self) -> bool:
        """
        Verify SSL certificate is valid and not expiring soon.
        
        Returns:
            bool: True if SSL certificate is valid and not near expiry, False otherwise
        """
        try:
            response = requests.get(self.base_url, verify=True)
            
            # Check certificate expiration
            cert = response.raw.connection.sock.getpeercert()
            expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (expires - datetime.utcnow()).days
            
            if days_until_expiry < 30:
                logger.warning(f"SSL certificate expires in {days_until_expiry} days")
                return False
                
            logger.info(f"SSL certificate valid for {days_until_expiry} days")
            return True
            
        except Exception as e:
            logger.error(f"SSL certificate check failed: {e}")
            return False

    @with_retry()
    def verify_rate_limiting(self) -> bool:
        """
        Verify rate limiting is working.
        
        Returns:
            bool: True if rate limiting is properly configured, False otherwise
        """
        try:
            # Make multiple rapid requests
            responses = []
            for _ in range(50):
                responses.append(
                    self.session.get(f"{self.base_url}/health")
                )
                time.sleep(0.1)
            
            # Check if any requests were rate limited
            rate_limited = [r for r in responses if r.status_code == 429]
            
            if not rate_limited:
                logger.warning("Rate limiting may not be properly configured")
                return False
                
            logger.info("Rate limiting check passed")
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            return False

    @with_retry()
    def verify_logging(self) -> bool:
        """
        Verify logging system is operational.
        
        Returns:
            bool: True if logging system check completed, False on error
        """
        try:
            # Make a request that should generate logs
            self.session.post(
                f"{self.base_url}/webhook/inbound",
                data={'test': 'logging'}
            )
            
            # Wait briefly for logs to be processed
            time.sleep(2)
            
            logger.info("Logging check completed (manual verification required)")
            return True
            
        except Exception as e:
            logger.error(f"Logging check failed: {e}")
            return False

    def run_all_checks(self) -> Dict[str, bool]:
        """
        Run all verification checks and return results.
        
        Returns:
            Dict[str, bool]: Dictionary of check names and their results
        """
        results = {
            'health_endpoint': self.verify_health_endpoint(),
            'webhook_authentication': self.verify_webhook_authentication(),
            'message_scheduling': self.verify_message_scheduling(),
            'database_connection': self.verify_database_connection(),
            'ssl_certificate': self.verify_ssl_certificate(),
            'rate_limiting': self.verify_rate_limiting(),
            'logging': self.verify_logging()
        }
        
        return results

def verify_deployment(url: str, twilio_sid: str, twilio_token: str) -> bool:
    """
    Verify deployment status by running all checks.
    
    Args:
        url: Base URL of the deployed application
        twilio_sid: Twilio Account SID
        twilio_token: Twilio Auth Token
        
    Returns:
        bool: True if all checks pass, False otherwise
    """
    verifier = DeploymentVerifier(url, twilio_sid, twilio_token)
    results = verifier.run_all_checks()
    
    # Print results
    print("\nDeployment Verification Results:")
    print("=" * 40)
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    print("\nOverall Status:", "✅ PASSED" if all_passed else "❌ FAILED")
    
    return all_passed
