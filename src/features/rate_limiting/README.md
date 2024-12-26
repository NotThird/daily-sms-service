# Rate Limiting Feature

This feature provides configurable rate limiting functionality to protect API endpoints and external service integrations from overuse.

## Purpose

The rate limiting feature is responsible for:
- Enforcing request rate limits
- Managing distributed rate limiting with Redis
- Protecting API endpoints
- Preventing service abuse
- Optimizing resource usage

## Components

### Rate Limiter (code.py)
- Rate limit implementation
- Redis integration (optional)
- Token bucket algorithm
- Request tracking
- Limit enforcement

## Usage

### Basic Rate Limiting

```python
from features.rate_limiting.code import RateLimiter

limiter = RateLimiter(
    key="api_requests",
    limit=60,  # requests
    window=60  # seconds
)

# Check if request is allowed
if limiter.allow_request():
    # Process request
    pass
else:
    # Return rate limit exceeded error
    pass
```

### Distributed Rate Limiting with Redis

```python
from features.rate_limiting.code import RedisRateLimiter

limiter = RedisRateLimiter(
    redis_url="redis://localhost:6379/0",
    key="api_requests",
    limit=60,
    window=60
)

# Check if request is allowed
allowed, remaining = limiter.check_limit("user_123")
```

## Dependencies

### Internal Dependencies
None

### External Dependencies
- redis: For distributed rate limiting (optional)

## Configuration

The feature can be configured through environment variables:

```bash
# Optional Redis Configuration
REDIS_URL=redis://localhost:6379/0
REDIS_PREFIX=rate_limit

# Default Limits
DEFAULT_RATE_LIMIT=60
DEFAULT_WINDOW_SECONDS=60
```

## Rate Limit Configurations

1. **HTTP Endpoints**
   ```python
   ENDPOINT_LIMITS = {
       'webhook/inbound': {'limit': 60, 'window': 60},  # 60/minute
       'webhook/status': {'limit': 120, 'window': 60},  # 120/minute
       'user/config': {'limit': 30, 'window': 60}       # 30/minute
   }
   ```

2. **External APIs**
   ```python
   API_LIMITS = {
       'openai': {'limit': 3000, 'window': 60},   # 3000/minute
       'twilio': {'limit': 100, 'window': 1}      # 100/second
   }
   ```

## Testing

The feature includes comprehensive tests covering:
- Basic rate limiting
- Redis integration
- Concurrent access
- Error handling
- Edge cases

```bash
# Run rate limiting tests
pytest src/features/rate_limiting/tests.py
```

## Error Handling

1. **Rate Limit Exceeded**
   - Returns 429 Too Many Requests
   - Includes Retry-After header
   - Logs excessive usage

2. **Redis Connection Issues**
   - Falls back to in-memory limiting
   - Logs connection errors
   - Automatic reconnection

3. **Concurrent Access**
   - Thread-safe operations
   - Race condition prevention
   - Atomic updates

## Performance Considerations

1. **Memory Usage**
   - Efficient token bucket implementation
   - Automatic cleanup of expired entries
   - Configurable bucket sizes

2. **Redis Optimization**
   - Connection pooling
   - Pipeline operations
   - Minimal network overhead

3. **Scalability**
   - Distributed rate limiting
   - Horizontal scaling support
   - Load balancer compatibility
