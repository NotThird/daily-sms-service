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
```

## Features

- Daily AI-generated positive messages using GPT-4
- Random delivery time between 12 PM and 5 PM
- Two-way interaction with opt-out/opt-in support
- Cloud-native deployment with high availability
- Comprehensive logging and monitoring
- Secure secrets management

## Prerequisites

1. AWS Account with necessary permissions
2. OpenAI API key
3. Twilio account and phone number
4. Domain name for webhook HTTPS endpoint
5. GitHub account for CI/CD

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

## Monitoring

- AWS CloudWatch Logs for application logs
- AWS CloudWatch Metrics for performance monitoring
- Twilio Console for SMS delivery status
- Database health metrics in AWS RDS console

## License

MIT
