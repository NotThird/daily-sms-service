# Web Application Feature

This feature provides the main Flask web application that handles HTTP requests, webhooks, and serves as the primary interface for the service.

## Purpose

The web application feature serves as the main entry point for:
- Handling incoming webhook requests from Twilio
- Processing user interactions
- Serving health check endpoints
- Managing rate limiting
- Providing API endpoints

## Components

### Web Application (code.py)
- Flask application setup and configuration
- Route handlers and controllers
- Webhook processing
- Health check implementation
- Error handling and logging

## Usage

### Running the Application

```python
from features.web_app.code import create_app

app = create_app()
app.run()
```

### Webhook Handling

```python
@app.route('/webhook/inbound', methods=['POST'])
def handle_inbound_webhook():
    # Webhook handling implementation
    pass
```

### Health Check

```bash
# Check application health
curl http://localhost:5000/health

# Expected response
{
    "status": "healthy",
    "database": {
        "connected": true
    },
    "timestamp": "2024-01-25T12:00:00Z"
}
```

## Dependencies

### Internal Dependencies
- features/core/code.py: Database models
- features/rate_limiting/code.py: Rate limiting functionality

### External Dependencies
- Flask: Web framework
- Werkzeug: WSGI utilities
- SQLAlchemy: Database ORM (via core)

## Configuration

The web application can be configured through environment variables:

```bash
# Required
FLASK_APP=src/features/web_app/code.py
FLASK_ENV=development  # or production
SECRET_KEY=your-secret-key

# Optional
PORT=5000
HOST=0.0.0.0
DEBUG=True
```

## Testing

The feature includes comprehensive tests covering:
- Route handling
- Webhook processing
- Health check functionality
- Error cases
- Rate limiting integration

```bash
# Run web application tests
pytest src/features/web_app/tests.py
```

## Security

1. **Request Validation**
   - Twilio signature verification
   - Input sanitization
   - CSRF protection

2. **Rate Limiting**
   - Per-endpoint limits
   - User-based quotas
   - IP-based restrictions

3. **Error Handling**
   - Secure error messages
   - Proper status codes
   - Audit logging
