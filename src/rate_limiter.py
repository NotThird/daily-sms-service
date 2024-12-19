"""
Simple rate limiting configuration for API endpoints and external service calls.
Uses in-memory storage suitable for small-scale deployments.
"""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import functools
import time
from datetime import datetime
import threading
import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

class APIRateLimiter:
    """Manages rate limits for external API calls."""
    
    def __init__(self):
        self.openai_limits = {
            'tokens_per_min': int(os.getenv('OPENAI_TOKENS_PER_MIN', '20000')),
            'requests_per_min': int(os.getenv('OPENAI_REQUESTS_PER_MIN', '100')),
            'last_reset': datetime.now(),
            'token_count': 0,
            'request_count': 0
        }
        
        self.twilio_limits = {
            'messages_per_day': int(os.getenv('TWILIO_MESSAGES_PER_DAY', '2000')),
            'messages_per_second': int(os.getenv('TWILIO_MESSAGES_PER_SECOND', '5')),
            'last_message_time': datetime.now(),
            'daily_count': 0,
            'last_daily_reset': datetime.now()
        }
        
        self._lock = threading.Lock()
        
    def _reset_if_needed(self, limits: Dict[str, Any], reset_interval_seconds: int) -> None:
        """Reset counters if the reset interval has passed."""
        now = datetime.now()
        seconds_since_reset = (now - limits['last_reset']).total_seconds()
        
        if seconds_since_reset >= reset_interval_seconds:
            limits['token_count'] = 0
            limits['request_count'] = 0
            limits['last_reset'] = now
            
    def _reset_daily_if_needed(self) -> None:
        """Reset daily message counter if day has changed."""
        now = datetime.now()
        if now.date() > self.twilio_limits['last_daily_reset'].date():
            self.twilio_limits['daily_count'] = 0
            self.twilio_limits['last_daily_reset'] = now
            
    def check_openai_limit(self, token_count: int) -> bool:
        """
        Check if the OpenAI API call is within rate limits.
        
        Args:
            token_count: Estimated token count for this request
            
        Returns:
            bool: True if within limits, False otherwise
        """
        with self._lock:
            self._reset_if_needed(self.openai_limits, 60)  # Reset every minute
            
            if (self.openai_limits['token_count'] + token_count > self.openai_limits['tokens_per_min'] or
                self.openai_limits['request_count'] + 1 > self.openai_limits['requests_per_min']):
                return False
                
            self.openai_limits['token_count'] += token_count
            self.openai_limits['request_count'] += 1
            return True
            
    def check_twilio_limit(self) -> bool:
        """
        Check if SMS sending is within rate limits.
        
        Returns:
            bool: True if within limits, False otherwise
        """
        with self._lock:
            self._reset_daily_if_needed()
            
            now = datetime.now()
            seconds_since_last = (now - self.twilio_limits['last_message_time']).total_seconds()
            
            # Check messages per second limit
            if seconds_since_last < (1.0 / self.twilio_limits['messages_per_second']):
                return False
                
            # Check daily message limit
            if self.twilio_limits['daily_count'] >= self.twilio_limits['messages_per_day']:
                return False
                
            self.twilio_limits['last_message_time'] = now
            self.twilio_limits['daily_count'] += 1
            return True

# Initialize Flask-Limiter with in-memory storage
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Use simple in-memory storage
)

# Initialize API rate limiter
api_limiter = APIRateLimiter()

def rate_limit_openai(estimated_tokens: int):
    """
    Decorator for OpenAI API calls with token-based rate limiting.
    
    Args:
        estimated_tokens: Estimated token count for the request
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                if api_limiter.check_openai_limit(estimated_tokens):
                    return func(*args, **kwargs)
                    
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"OpenAI rate limit reached, waiting before retry {retry_count}")
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    
            logger.error("OpenAI rate limit reached and max retries exceeded")
            raise Exception("Rate limit exceeded")
            
        return wrapper
    return decorator

def rate_limit_sms():
    """Decorator for SMS sending with rate limiting."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retry_count = 0
            max_retries = 3
            
            while retry_count < max_retries:
                if api_limiter.check_twilio_limit():
                    return func(*args, **kwargs)
                    
                retry_count += 1
                if retry_count < max_retries:
                    logger.warning(f"SMS rate limit reached, waiting before retry {retry_count}")
                    time.sleep(2 ** retry_count)  # Exponential backoff
                    
            logger.error("SMS rate limit reached and max retries exceeded")
            raise Exception("Rate limit exceeded")
            
        return wrapper
    return decorator
