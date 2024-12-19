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

## Prerequisites

1. AWS Account with necessary permissions
2. OpenAI API key
3. Twilio account and phone number
4. Domain name for webhook HTTPS endpoint
5. GitHub account for CI/CD
6. Redis instance (optional, for distributed rate limiting)

## Setup Instructions

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install poetry
   poetry install
   ```
3. Set up environment variables (see .env.example)
4. Initialize database:
   ```bash
   poetry run alembic upgrade head
   ```
5. Configure rate limits in environment:
   ```bash
   # API Rate Limits
   OPENAI_TOKENS_PER_MIN=10000
   OPENAI_REQUESTS_PER_MIN=50
   TWILIO_MESSAGES_PER_DAY=1000
   TWILIO_MESSAGES_PER_SECOND=1
   
   # Optional Redis Configuration
   REDIS_URL=redis://localhost:6379/0
   ```

## Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment instructions.

## Development

1. Create virtual environment:
   ```bash
   poetry shell
   ```
2. Run tests:
   ```bash
   pytest
   ```
3. Format code:
   ```bash
   black .
   flake8
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

## Monitoring

- AWS CloudWatch Logs for application logs
- AWS CloudWatch Metrics for performance monitoring
- Twilio Console for SMS delivery status
- Database health metrics in AWS RDS console
- Rate limit metrics and alerts
- Redis monitoring (if used)

## Cost Control

1. Rate Limiting:
   - Prevents API cost overruns
   - Controls SMS usage
   - Configurable limits

2. Database:
   - Automatic cleanup
   - Size monitoring
   - 90-day migration support

3. Monitoring:
   - Usage tracking
   - Cost alerts
   - Performance metrics

## License

MIT
