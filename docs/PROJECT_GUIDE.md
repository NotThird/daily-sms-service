# Daily Positivity SMS Service - Project Guide

## Overview

The Daily Positivity SMS Service is a cloud-based application that sends daily AI-generated positive messages to subscribers. It uses GPT-4 for message generation and Twilio for SMS delivery, with a robust cloud infrastructure ensuring reliable operation.

## System Architecture

### Core Components

1. **Message Generation (src/message_generator.py)**
   - Uses OpenAI's GPT-4 API
   - Generates unique, positive messages
   - Includes fallback mechanism for API failures
   - Maintains message history to avoid repetition

2. **SMS Service (src/sms_service.py)**
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

5. **Database Models (src/models.py)**
   - Recipients management
   - Message logging
   - Schedule tracking
   - State persistence

### Infrastructure Components

1. **Database (AWS RDS)**
   - PostgreSQL database
   - Stores recipient information
   - Tracks message history
   - Manages scheduling state

2. **Application Hosting (AWS ECS)**
   - Containerized deployment
   - Auto-scaling capabilities
   - High availability setup
   - Load balanced traffic

3. **Scheduler (AWS EventBridge)**
   - Manages daily triggers
   - Handles message processing
   - Coordinates cleanup tasks

4. **Monitoring (AWS CloudWatch)**
   - Application logging
   - Performance metrics
   - Alert management
   - Resource utilization tracking

## Development Guide

### Setting Up Local Environment

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

   # Verify database
   poetry run python -c "from src.models import get_db_session; session = get_db_session()"
   ```

### Running Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test file
poetry run pytest tests/test_app.py

# Run tests with specific marker
poetry run pytest -m "not slow"
```

### Local Development

1. **Running the Application**
   ```bash
   # Start Flask development server
   poetry run flask run

   # Run scheduler (in separate terminal)
   poetry run python -m src.cli schedule_messages

   # Run message processor (in separate terminal)
   poetry run python -m src.cli process_messages
   ```

2. **Testing Webhooks Locally**
   ```bash
   # Install ngrok
   # Start ngrok tunnel
   ngrok http 5000

   # Update Twilio webhook URLs with ngrok URL
   # Example: https://<your-ngrok-url>/webhook/inbound
   ```

## Deployment Guide

See [DEPLOYMENT.md](../DEPLOYMENT.md) for detailed deployment instructions.

## Maintenance Guide

### Daily Operations

1. **Monitoring**
   - Check CloudWatch logs for errors
   - Monitor message delivery rates
   - Track API usage and costs
   - Review system performance metrics

2. **Database Maintenance**
   ```bash
   # Run cleanup routine
   poetry run python -m src.cli cleanup

   # Verify database health
   curl https://your-domain.com/health
   ```

3. **Backup Verification**
   - Confirm RDS automated backups
   - Verify backup retention policy
   - Test backup restoration periodically

### Troubleshooting

1. **Common Issues**

   a. Message Delivery Failures
   ```bash
   # Check Twilio logs
   # Verify message status
   poetry run python -m src.cli check_message <message_sid>
   ```

   b. Scheduling Issues
   ```bash
   # Verify EventBridge rules
   aws events list-rules --name-prefix daily-positivity

   # Check scheduler logs
   aws logs get-log-events --log-group-name /ecs/daily-positivity --log-stream-name scheduler
   ```

   c. API Rate Limits
   - Monitor OpenAI API usage
   - Check Twilio rate limits
   - Adjust scheduling if needed

2. **Error Resolution**
   - Check application logs
   - Verify service health
   - Review recent changes
   - Check infrastructure status

### Security Maintenance

1. **Regular Updates**
   ```bash
   # Update dependencies
   poetry update

   # Review security advisories
   poetry show --tree
   ```

2. **Credential Rotation**
   - Rotate API keys periodically
   - Update AWS credentials
   - Refresh Twilio tokens
   - Update database passwords

3. **Security Monitoring**
   - Review AWS CloudTrail logs
   - Monitor for unusual activity
   - Check access patterns
   - Verify SSL certificates

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

3. **Monitoring**
   - Set up alerting thresholds
   - Monitor resource usage
   - Track error rates
   - Review performance metrics

4. **Data Management**
   - Regular database backups
   - Implement data retention policies
   - Monitor database performance
   - Clean up old records

## Support and Resources

- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [Twilio API Documentation](https://www.twilio.com/docs/api)
- [AWS Documentation](https://docs.aws.amazon.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
