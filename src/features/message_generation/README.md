# Message Generation Feature

This feature handles the generation of positive messages using GPT-4-mini and manages the scheduling of message delivery.

## Purpose

The message generation feature is responsible for:
- Generating unique, positive messages using GPT-4-mini
- Managing message scheduling and delivery windows
- Maintaining message history to avoid repetition
- Handling message generation failures gracefully

## Components

### Message Generator (code.py)
- GPT-4-mini integration
- Message generation logic
- Content filtering and validation
- Fallback mechanisms
- History tracking

### Scheduler (scheduler.py)
- Message delivery scheduling
- Timezone handling
- Delivery window management
- Retry logic for failed deliveries

## Usage

### Generating Messages

```python
from features.message_generation.code import MessageGenerator

generator = MessageGenerator()
message = await generator.generate_message(
    user_preferences={
        "tone": "uplifting",
        "topics": ["motivation", "growth"]
    }
)
```

### Scheduling Messages

```python
from features.message_generation.scheduler import MessageScheduler

scheduler = MessageScheduler()
scheduled_time = scheduler.schedule_message(
    user_id=123,
    timezone="America/New_York",
    delivery_window={
        "start": "12:00",
        "end": "17:00"
    }
)
```

## Dependencies

### Internal Dependencies
- features/core/code.py: Database models
- features/notification_system/sms.py: Message delivery

### External Dependencies
- openai: GPT-4-mini integration
- pytz: Timezone handling
- APScheduler: Message scheduling

## Configuration

The feature can be configured through environment variables:

```bash
# Required
OPENAI_API_KEY=your-api-key
MODEL_NAME=gpt-4-mini

# Optional
MAX_RETRIES=3
GENERATION_TIMEOUT=30
DELIVERY_WINDOW_START=12  # 12 PM
DELIVERY_WINDOW_END=17    # 5 PM
```

## Testing

The feature includes comprehensive tests covering:
- Message generation
- Scheduling logic
- Error handling
- Integration with GPT-4-mini
- Timezone handling

```bash
# Run message generation tests
pytest src/features/message_generation/tests.py
```

## Error Handling

1. **Generation Failures**
   - Automatic retries with backoff
   - Fallback to pre-generated messages
   - Error logging and monitoring

2. **Scheduling Issues**
   - Timezone validation
   - Delivery window checks
   - Schedule conflict resolution

3. **API Limits**
   - Rate limiting compliance
   - Token usage monitoring
   - Cost optimization
