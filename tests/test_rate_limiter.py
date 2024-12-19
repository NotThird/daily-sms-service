import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
from src.rate_limiter import APIRateLimiter, rate_limit_openai, rate_limit_sms

def test_openai_rate_limiter():
    """Test OpenAI API rate limiting."""
    limiter = APIRateLimiter()
    
    # Should allow requests within limits
    assert limiter.check_openai_limit(100) is True
    assert limiter.check_openai_limit(100) is True
    
    # Should reject when token limit exceeded
    limiter.openai_limits['token_count'] = 9900
    assert limiter.check_openai_limit(200) is False
    
    # Should reject when request limit exceeded
    limiter.openai_limits['request_count'] = 49
    assert limiter.check_openai_limit(50) is False
    
    # Should reset after minute passes
    limiter.openai_limits['last_reset'] = datetime.now() - timedelta(minutes=1)
    assert limiter.check_openai_limit(100) is True
    assert limiter.openai_limits['token_count'] == 100
    assert limiter.openai_limits['request_count'] == 1

def test_sms_rate_limiter():
    """Test SMS rate limiting."""
    limiter = APIRateLimiter()
    
    # Should allow messages within limits
    assert limiter.check_twilio_limit() is True
    
    # Should reject when exceeding messages per second
    assert limiter.check_twilio_limit() is False
    
    # Should allow after delay
    limiter.twilio_limits['last_message_time'] = datetime.now() - timedelta(seconds=2)
    assert limiter.check_twilio_limit() is True
    
    # Should reject when daily limit reached
    limiter.twilio_limits['daily_count'] = 1000
    assert limiter.check_twilio_limit() is False
    
    # Should reset after day changes
    limiter.twilio_limits['last_daily_reset'] = datetime.now() - timedelta(days=1)
    assert limiter.check_twilio_limit() is True
    assert limiter.twilio_limits['daily_count'] == 1

@pytest.mark.asyncio
async def test_rate_limit_openai_decorator():
    """Test OpenAI rate limiting decorator."""
    mock_function = Mock(return_value="test")
    decorated = rate_limit_openai(estimated_tokens=100)(mock_function)
    
    # First call should succeed
    result = decorated()
    assert result == "test"
    assert mock_function.called
    
    # Subsequent calls should be rate limited
    mock_function.reset_mock()
    with pytest.raises(Exception, match="Rate limit exceeded"):
        for _ in range(60):  # Exceed rate limit
            decorated()

@pytest.mark.asyncio
async def test_rate_limit_sms_decorator():
    """Test SMS rate limiting decorator."""
    mock_function = Mock(return_value="test")
    decorated = rate_limit_sms()(mock_function)
    
    # First call should succeed
    result = decorated()
    assert result == "test"
    assert mock_function.called
    
    # Subsequent calls should be rate limited
    mock_function.reset_mock()
    with pytest.raises(Exception, match="Rate limit exceeded"):
        for _ in range(10):  # Exceed rate limit
            decorated()

def test_rate_limiter_thread_safety():
    """Test thread safety of rate limiters."""
    import threading
    import queue
    
    limiter = APIRateLimiter()
    results = queue.Queue()
    
    def worker():
        try:
            result = limiter.check_openai_limit(100)
            results.put(result)
        except Exception as e:
            results.put(e)
    
    # Create multiple threads to test concurrency
    threads = [threading.Thread(target=worker) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    
    # Collect results
    thread_results = []
    while not results.empty():
        thread_results.append(results.get())
    
    # Verify results
    assert len(thread_results) == 10
    assert isinstance(thread_results[0], bool)
    assert not any(isinstance(r, Exception) for r in thread_results)

@pytest.fixture
def mock_redis():
    """Mock Redis for testing distributed rate limiting."""
    with patch('redis.Redis') as mock:
        yield mock

def test_distributed_rate_limiting(mock_redis):
    """Test rate limiting with Redis backend."""
    from src.rate_limiter import limiter
    
    # Configure limiter to use Redis
    limiter.storage_url = "redis://localhost:6379/0"
    
    @limiter.limit("10/minute")
    def test_endpoint():
        return "success"
    
    # First call should succeed
    assert test_endpoint() == "success"
    
    # Mock Redis to simulate rate limit exceeded
    mock_redis.return_value.incr.return_value = 11
    
    # Should raise rate limit exceeded
    with pytest.raises(Exception, match="Rate limit exceeded"):
        test_endpoint()
