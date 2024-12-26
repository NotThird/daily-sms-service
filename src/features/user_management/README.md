# User Management Feature

This feature handles user configuration, onboarding, and CLI operations for managing user accounts and preferences.

## Purpose

The user management feature is responsible for:
- Managing user configurations and preferences
- Handling user onboarding process
- Providing CLI tools for user management
- Maintaining user settings and state

## Components

### Configuration (config.py)
- User preferences management
- Settings validation
- Configuration persistence
- Default settings handling

### Onboarding (onboarding.py)
- User registration process
- Welcome message handling
- Initial setup workflow
- Preference collection

### CLI Interface (cli.py)
- User management commands
- Configuration updates
- Status queries
- Bulk operations

## Usage

### Managing User Configuration

```python
from features.user_management.config import UserConfig

# Load user configuration
config = UserConfig.load(user_id=123)

# Update preferences
config.update_preferences({
    "delivery_time": "14:00",
    "timezone": "America/New_York",
    "topics": ["motivation", "growth"]
})

# Save changes
config.save()
```

### User Onboarding

```python
from features.user_management.onboarding import OnboardingManager

manager = OnboardingManager()
await manager.start_onboarding(
    phone_number="+1234567890",
    initial_preferences={
        "name": "John Doe",
        "timezone": "America/New_York"
    }
)
```

### CLI Operations

```bash
# Add new user
python -m features.user_management.cli add-user --phone "+1234567890" --name "John Doe"

# Update user preferences
python -m features.user_management.cli update-preferences --user-id 123 --timezone "America/New_York"

# List active users
python -m features.user_management.cli list-users --status active
```

## Dependencies

### Internal Dependencies
- features/core/code.py: Database models
- features/notification_system/sms.py: Welcome messages

### External Dependencies
- click: CLI framework
- pydantic: Configuration validation
- pytz: Timezone handling

## Configuration

The feature can be configured through environment variables:

```bash
# User Management Settings
DEFAULT_TIMEZONE=UTC
DEFAULT_DELIVERY_TIME=14:00
WELCOME_MESSAGE_ENABLED=true

# CLI Settings
CLI_BATCH_SIZE=100
CLI_TIMEOUT=30
```

## Testing

The feature includes comprehensive tests covering:
- Configuration management
- Onboarding workflow
- CLI operations
- Error handling
- Edge cases

```bash
# Run user management tests
pytest src/features/user_management/tests.py
```

## Error Handling

1. **Configuration Errors**
   - Invalid settings validation
   - Missing required fields
   - Type conversion errors
   - Persistence failures

2. **Onboarding Issues**
   - Invalid phone numbers
   - Duplicate registrations
   - Welcome message failures
   - Incomplete setup

3. **CLI Failures**
   - Invalid commands
   - Missing parameters
   - Database errors
   - Timeout handling

## Security Considerations

1. **Data Protection**
   - Secure storage of user data
   - Validation of all inputs
   - Access control enforcement
   - Audit logging

2. **Phone Number Handling**
   - Number validation
   - Format standardization
   - Privacy protection
   - Opt-out enforcement

3. **CLI Security**
   - Command authorization
   - Input sanitization
   - Rate limiting
   - Audit trails
