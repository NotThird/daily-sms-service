# Holiday Automation Service

Automated holiday message scheduling and delivery system that sends personalized messages to users on major holidays.

## Purpose

This service extends the messaging system to support automated holiday greetings by:
- Managing holiday configurations with customizable templates
- Scheduling messages for delivery on specific holidays
- Personalizing messages using user preferences and information
- Integrating with the existing scheduler for reliable delivery

## Usage

```python
from src.features.holiday_automation.code import HolidayAutomationService

# Initialize service
service = HolidayAutomationService(db_session)

# Schedule messages for a specific holiday
result = service.schedule_holiday_messages("New Year's Day")
print(f"Scheduled {result['scheduled']} messages")
```

## Implementation Details

### Core Components

1. `HolidayConfig` - Data class for holiday message configuration:
   - Holiday name and date
   - Message template with personalization fields
   - List of required personalization fields

2. `HolidayAutomationService` - Main service class:
   - Holiday configuration management
   - Message scheduling and generation
   - Integration with scheduler and SMS services

### Security Measures

1. Input Sanitization
   - All user inputs are sanitized before template insertion
   - Special characters are stripped to prevent injection attacks

2. Rate Limiting
   - Bulk message scheduling is rate-limited
   - Prevents system overload during high-volume periods

### Performance Optimization

- Holiday configuration caching using `@lru_cache`
  - Reduces database lookups for frequently accessed holidays
  - Configurable cache size (default: 100 entries)

## Testing

The test suite covers:
1. Holiday configuration retrieval and caching
2. Message generation with various user configurations
3. Input sanitization for security
4. Message scheduling functionality

Run tests with:
```bash
pytest src/features/holiday_automation/tests.py
```

## Integration Points

- User Management: Retrieves user preferences and configurations
- Message Generation: Creates personalized message content
- Scheduler: Handles message delivery timing
- SMS Service: Delivers messages to recipients
- Rate Limiting: Controls message sending rates

## Future Enhancements

1. Add support for more holidays with custom templates
2. Implement holiday-specific personalization rules
3. Add timezone-aware scheduling for global recipients
4. Support for multimedia holiday messages (MMS)
