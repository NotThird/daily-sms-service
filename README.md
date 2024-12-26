# Daily Positivity SMS Service

A cloud-based service that sends daily AI-generated positive messages via SMS using GPT-4 and Twilio.

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  AWS EventBridge│────▶│ Lambda/ECS   │────▶│ OpenAI API    │
│  (Scheduler)    │     │ (Generator)   │     │ (GPT-4)       │
└─────────────────┘     └──────────────┘     └───────────────┘
                              │
                              ▼
┌─────────────────┐     ┌──────────────┐     ┌───────────────┐
│  AWS RDS        │◀───▶│ Flask App    │◀───▶│ Twilio API    │
│  (PostgreSQL)   │     │ (Webhooks)   │     │ (SMS)         │
└─────────────────┘     └──────────────┘     └───────────────┘
                              │
                              ▼
┌─────────────────┐     ┌──────────────┐
│  Redis          │◀───▶│ Rate Limiter │
│  (Optional)     │     │ (API/SMS)    │
└─────────────────┘     └──────────────┘
```

## Features

- Daily AI-generated positive messages using GPT-4
- Random delivery time between 12 PM and 5 PM
- Two-way interaction with opt-out/opt-in support
- Cloud-native deployment with high availability
- Comprehensive logging and monitoring
- Secure secrets management
- Rate limiting for API and SMS usage
- Distributed rate limiting with Redis (optional)
- Cost optimization through usage controls

## System Components

1. **Message Generation (src/message_generator.py)**
   - Uses OpenAI's GPT-4 API
   - Generates unique, positive messages
   - Includes fallback mechanism for API failures
   - Maintains message history to avoid repetition

2. **SMS Service (src/features/sms/code.py)**
   - Handles Twilio integration
   - Manages message delivery
   - Processes delivery status callbacks
   - Handles opt-in/opt-out requests

3. **Web Application (src/app.py)**
   - Flask-based webhook handler
   - Processes incoming messages
   - Manages subscription status
   - Provides health check endpoint

4. **Scheduler (src/scheduler.py)**
   - Manages daily message scheduling
   - Handles timezone-aware delivery windows
   - Processes scheduled messages
   - Implements cleanup routines

## Prerequisites

1. AWS Account with necessary permissions
2. OpenAI API key
3. Twilio account and phone number
4. Domain name for webhook HTTPS endpoint
5. GitHub account for CI/CD
6. Redis instance (optional, for distributed rate limiting)

## Local Development Setup

1. **Prerequisites**
   ```bash
   # Install Python 3.9+
   # Install Poetry
   curl -sSL https://install.python-poetry.org | python3 -

   # Clone repository
   git clone <repository-url>
   cd daily-positivity

   # Install dependencies
   poetry install
   ```

2. **Environment Configuration**
   ```bash
   # Copy example environment file
   cp .env.example .env

   # Edit .env with your credentials
   # Required variables:
   # - DATABASE_URL
   # - OPENAI_API_KEY
   # - TWILIO_ACCOUNT_SID
   # - TWILIO_AUTH_TOKEN
   # - TWILIO_FROM_NUMBER
   ```

3. **Database Setup**
   ```bash
   # Initialize database
   poetry run alembic upgrade head
   ```

4. **Running Tests**
   ```bash
   # Run all tests with coverage
   poetry run pytest

   # Run specific test file
   poetry run pytest tests/test_app.py

   # Run tests with specific marker
   poetry run pytest -m "not slow"
   ```

5. **Local Development Server**
   ```bash
   # Start Flask development server
   poetry run flask run

   # For testing webhooks locally
   # Install ngrok and start tunnel
   ngrok http 5000
   ```

## Rate Limiting

The service implements multi-level rate limiting:

1. HTTP Endpoint Limits:
   - User config updates: 30/minute
   - Inbound messages: 60/minute
   - Status callbacks: 120/minute
   - Health checks: unlimited

2. OpenAI API Limits:
   - Token-based limiting
   - Request frequency control
   - Automatic retry with backoff

3. Twilio SMS Limits:
   - Daily message quota
   - Per-second rate limiting
   - Error handling with retries

4. Storage Options:
   - In-memory (default)
   - Redis (distributed)

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## Maintenance Guide

### Daily Operations

1. **Monitoring**
   - Check CloudWatch logs for errors
   - Monitor message delivery rates
   - Track API usage and costs
   - Review system performance metrics

2. **Database Maintenance**
   - Regular cleanup routines
   - Verify database health
   - Monitor database size
   - Check backup status

3. **Security Maintenance**
   - Rotate API keys periodically
   - Update AWS credentials
   - Refresh Twilio tokens
   - Update database passwords

### Troubleshooting

1. **Common Issues**
   - Message delivery failures
   - Scheduling issues
   - API rate limits
   - Database connectivity

2. **Error Resolution**
   - Check application logs
   - Verify service health
   - Review recent changes
   - Check infrastructure status

## Best Practices

1. **Code Quality**
   - Follow PEP 8 guidelines
   - Write comprehensive tests
   - Document code changes
   - Use type hints

2. **Deployment**
   - Use CI/CD pipeline
   - Test in staging first
   - Deploy during low-traffic periods
   - Maintain deployment documentation

3. **Data Management**
   - Regular database backups
   - Implement data retention policies
   - Monitor database performance
   - Clean up old records

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

## License

MIT
