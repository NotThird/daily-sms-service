"""
Tests for rate limiting functionality.
Covers in-memory and Redis-based rate limiting.
"""

import pytest
import time
from unittest.mock import patch, MagicMock
import redis
from .code import RateLimiter, RedisRateLimiter

# Test data
TEST_KEY = "test_requests"
TEST_LIMIT = 5
TEST_WINDOW = 1  # 1 second

@pytest.fixture
def limiter():
    """Create in-memory rate limiter instance."""
    return RateLimiter(
        key=TEST_KEY,
        limit=TEST_LIMIT,
        window=TEST_WINDOW
    )

@pytest.fixture
def redis_mock():
    """Create mock Redis client."""
    return MagicMock(spec=redis.Redis)

@pytest.fixture
def redis_limiter(redis_mock):
    """Create Redis rate limiter instance with mock client."""
    return RedisRateLimiter(
        redis_client=redis_mock,
        key=TEST_KEY,
        limit=TEST_LIMIT,
        window=TEST_WINDOW
    )

def test_basic_rate_limiting(limiter):
    """Test basic rate limiting functionality."""
    # Should allow TEST_LIMIT requests
    for _ in range(TEST_LIMIT):
        assert limiter.allow_request() is True
    
    # Next request should be denied
    assert limiter.allow_request() is False

def test_window_reset(limiter):
    """Test rate limit window reset."""
    # Use up all requests
    for _ in range(TEST_LIMIT):
        assert limiter.allow_request() is True
    
    # Wait for window to reset
    time.sleep(TEST_WINDOW + 0.1)
    
    # Should allow requests again
    assert limiter.allow_request() is True

def test_concurrent_requests(limiter):
    """Test rate limiting with concurrent requests."""
    import threading
    
    def make_request():
        return limiter.allow_request()
    
    # Create threads for concurrent requests
    threads = []
    results = []
    
    for _ in range(TEST_LIMIT + 5):
        thread = threading.Thread(
            target=lambda: results.append(make_request())
        )
        threads.append(thread)
        thread.start()
    
    # Wait for all threads
    for thread in threads:
        thread.join()
    
    # Should have exactly TEST_LIMIT True results
    assert sum(1 for r in results if r) == TEST_LIMIT

def test_redis_rate_limiting(redis_limiter, redis_mock):
    """Test Redis-based rate limiting."""
    # Mock Redis get/set operations
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    
    # Should allow TEST_LIMIT requests
    for _ in range(TEST_LIMIT):
        assert redis_limiter.allow_request() is True
    
    # Update mock to simulate limit reached
    redis_mock.get.return_value = str(TEST_LIMIT).encode()
    
    # Next request should be denied
    assert redis_limiter.allow_request() is False

def test_redis_connection_failure(redis_limiter, redis_mock):
    """Test Redis connection failure handling."""
    # Simulate Redis connection failure
    redis_mock.get.side_effect = redis.ConnectionError("Connection failed")
    
    # Should fall back to in-memory limiting
    assert redis_limiter.allow_request() is True
    
    # Verify fallback tracking works
    for _ in range(TEST_LIMIT - 1):
        assert redis_limiter.allow_request() is True
    assert redis_limiter.allow_request() is False

def test_remaining_requests(limiter):
    """Test remaining requests calculation."""
    for i in range(TEST_LIMIT):
        remaining = limiter.get_remaining_requests()
        assert remaining == TEST_LIMIT - i
        limiter.allow_request()
    
    assert limiter.get_remaining_requests() == 0

def test_redis_remaining_requests(redis_limiter, redis_mock):
    """Test remaining requests with Redis."""
    # Mock initial state
    redis_mock.get.return_value = None
    
    for i in range(TEST_LIMIT):
        redis_mock.get.return_value = str(i).encode()
        remaining = redis_limiter.get_remaining_requests()
        assert remaining == TEST_LIMIT - i

def test_cleanup(limiter):
    """Test cleanup of expired entries."""
    # Use up some requests
    for _ in range(TEST_LIMIT - 1):
        limiter.allow_request()
    
    # Wait for window to expire
    time.sleep(TEST_WINDOW + 0.1)
    
    # Trigger cleanup
    limiter.cleanup()
    
    # Should reset available requests
    assert limiter.get_remaining_requests() == TEST_LIMIT

def test_redis_pipeline(redis_limiter, redis_mock):
    """Test Redis pipeline usage."""
    pipeline_mock = MagicMock()
    redis_mock.pipeline.return_value.__enter__.return_value = pipeline_mock
    
    redis_limiter.allow_request()
    
    # Verify pipeline was used
    assert redis_mock.pipeline.called
    assert pipeline_mock.execute.called

def test_different_keys(limiter):
    """Test rate limiting with different keys."""
    limiter2 = RateLimiter(
        key="other_requests",
        limit=TEST_LIMIT,
        window=TEST_WINDOW
    )
    
    # Use up limits for first key
    for _ in range(TEST_LIMIT):
        limiter.allow_request()
    
    # Second key should still allow requests
    assert limiter2.allow_request() is True

def test_zero_limit(limiter):
    """Test rate limiter with zero limit."""
    limiter = RateLimiter(
        key=TEST_KEY,
        limit=0,
        window=TEST_WINDOW
    )
    
    assert limiter.allow_request() is False
    assert limiter.get_remaining_requests() == 0

def test_negative_window(limiter):
    """Test rate limiter with negative window."""
    with pytest.raises(ValueError):
        RateLimiter(
            key=TEST_KEY,
            limit=TEST_LIMIT,
            window=-1
        )

def test_redis_key_prefix(redis_limiter, redis_mock):
    """Test Redis key prefixing."""
    redis_limiter.allow_request()
    
    # Verify prefix was used in Redis key
    called_key = redis_mock.get.call_args[0][0]
    assert called_key.startswith(b'rate_limit:')
