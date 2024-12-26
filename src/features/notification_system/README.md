# Notification System

A feature that sends SMS notifications for important system events like user signups and message receipts.

## Purpose

This system provides real-time SMS notifications to administrators about key events in the application, ensuring immediate awareness of user activity and system status.

## Usage

```python
from src.features.notification_system.code import notification_manager

# For new user signups
await notification_manager.handle_user_signup("user_123")

# For message receipts
await notification_manager.handle_message_receipt("user_123", "msg_456")

# For system alerts
await notification_manager.handle_system_alert("Critical system event")
```

## Logic

The notification system:
1. Validates and sanitizes phone numbers to prevent injection attacks
2. Uses pre-formatted message templates for consistent messaging
3. Handles errors gracefully to prevent system disruption
4. Implements rate limiting to prevent notification flooding

## Security Features

1. Phone Number Sanitization
   - Strips non-numeric characters
   - Validates format (10 digits or 11 digits starting with 1)
   - Prevents potential injection attacks

2. Rate Limiting
   - Prevents notification flooding
   - Protects against potential abuse

## Performance Optimization

- Pre-formatted message templates to avoid runtime string concatenation
- Asynchronous notification sending
- Dynamic imports to prevent circular dependencies

## Testing

Run the tests using pytest:

```bash
pytest src/features/notification_system/tests.py -v
```

The test suite covers:
- Phone number validation
- Message formatting
- Event handling
- Error handling
