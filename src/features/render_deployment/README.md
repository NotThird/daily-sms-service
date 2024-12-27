# Render Deployment Feature

## Purpose
This feature provides optimized configuration and management for deploying the application on Render's platform. It implements secure deployment hooks, efficient database connection pooling, and environment validation to ensure reliable deployments.

## Usage

### Basic Configuration
```python
from src.features.render_deployment.code import configure_render_deployment

# Configure deployment with default settings
config, pool_manager = configure_render_deployment(
    database_url=os.getenv('DATABASE_URL'),
    deploy_hook_secret=os.getenv('RENDER_DEPLOY_HOOK_SECRET')
)
```

### Health Check Caching
```python
@config.cache_health_check
def health_check():
    return {
        "status": "healthy",
        "database": check_database(),
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Database Connection Pool
```python
# Get connection from pool
with pool_manager.get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT 1")
```

## Implementation Details

### Security Practices

1. **Deploy Hook Signature Validation**
   - Implements HMAC-SHA256 signature validation for Render deploy hooks
   - Prevents unauthorized deployment triggers
   - Uses constant-time comparison to prevent timing attacks

2. **Environment Variable Validation**
   - Validates presence and types of all required environment variables
   - Sanitizes sensitive information in database URLs
   - Prevents deployment with missing or invalid configuration

### Performance Optimizations

1. **Connection Pooling**
   - Implements efficient database connection pooling
   - Reduces connection overhead and improves response times
   - Automatically manages connection lifecycle
   - Configurable pool size based on workload

2. **Health Check Caching**
   - Caches health check responses for 60 seconds
   - Reduces database load during high-traffic periods
   - Automatically invalidates cache when needed

## Testing

The feature includes comprehensive tests covering:
- Deploy hook signature validation
- Health check response caching
- Connection pool management
- Environment variable validation
- Zero-downtime deployment simulation

Run tests with:
```bash
pytest src/features/render_deployment/tests.py -v
```

## Dependencies
- psycopg2: PostgreSQL database adapter
- cachetools: Caching utilities
- requests: HTTP client library

## Configuration

Required environment variables:
```
DATABASE_URL=postgresql://user:pass@host:5432/db
PORT=5000
FLASK_ENV=production
OPENAI_API_KEY=your_key
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
RENDER_DEPLOY_HOOK_SECRET=your_secret
```

## Integration with Render

1. Set up a Render Web Service
2. Configure environment variables in Render dashboard
3. Add deploy hook URL in repository settings
4. Update health check endpoint in render.yaml

Example render.yaml configuration:
```yaml
services:
  - type: web
    name: your-app
    env: python
    buildCommand: "./build.sh"
    startCommand: "./docker-entrypoint.sh web"
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: your-db
          property: connectionString
