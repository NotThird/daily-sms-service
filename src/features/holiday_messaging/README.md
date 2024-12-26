# Holiday Messaging Feature

A service for sending positive holiday messages to all active users in the system.

## Purpose

This feature enables bulk sending of personalized holiday messages to active users while maintaining system stability through rate limiting and batch processing.

## Usage

```python
from src.features.holiday_messaging.code import HolidayMessageService

# Initialize service with database session
service = HolidayMessageService(db_session)

# Send holiday messages to all active users
result = await service.send_bulk_messages(batch_size=50)
print(f"Sent {result['messages_sent']} messages successfully")
```

## Core Logic

The service implements three main functions:

1. `get_active_users()`: Retrieves all active users from the database
2. `generate_holiday_message(user_name)`: Creates personalized holiday messages with input sanitization
3. `send_bulk_messages(batch_size)`: Sends messages in batches with rate limiting

## Security Features

1. Input Sanitization: User names are sanitized before message generation to prevent injection attacks
2. Rate Limiting: Integrated rate limiting prevents system overload and ensures fair resource usage

## Performance Optimization

- Batch Processing: Messages are sent in configurable batches to optimize throughput
- Active User Filtering: Database query optimized to fetch only active users
- Exception Handling: Failed messages are logged but don't block the entire batch

## Testing

Run the tests using pytest:

```bash
pytest src/features/holiday_messaging/tests.py -v
```

The test suite covers:
- Message generation and sanitization
- User filtering
- Bulk sending with rate limiting
- Error handling and failure scenarios

## Dependencies

- user_management: For accessing user data
- message_generation: For message templating
- sms: For message delivery
- rate_limiting: For controlling message sending rate
