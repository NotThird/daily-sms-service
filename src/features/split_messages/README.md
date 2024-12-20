# Split Message Feature

This feature enables sending split secret messages between two users, where each user receives part of a message that only makes sense when combined with the other part.

## Purpose

The split message feature allows scheduling messages that are automatically divided into two parts, with each part sent to a different recipient at a specified time. This creates an engaging experience where recipients need to collaborate to understand the complete message.

## Usage

```python
from datetime import datetime
from features.split_messages.code import SplitMessageService

# Initialize service
split_service = SplitMessageService(db_session)

# Schedule a split message
result = split_service.schedule_split_message(
    message="This is a secret message that will be split",
    recipient1_phone="+1234567890",
    recipient2_phone="+0987654321",
    scheduled_time=datetime(2024, 1, 20, 22, 40)  # 10:40 PM
)
```

## Internal Logic

1. Message Splitting:
   - Takes a complete message as input
   - Splits it into two parts using an alternating word pattern
   - Adds placeholders to help recipients understand message structure
   - Returns two complementary parts that only make sense when combined

2. Message Scheduling:
   - Validates both recipients exist in the system
   - Creates two scheduled messages, one for each recipient
   - Sets exact delivery time for both messages
   - Returns confirmation with preview of both message parts

3. Message Format:
   - Part 1: Contains even-indexed words with placeholders
   - Part 2: Contains odd-indexed words with placeholders
   - Example:
     Original: "This is a secret message"
     Part 1: "This ___ a ___ message"
     Part 2: "___ is ___ secret ___"

## Dependencies

- scheduler.py: For message scheduling functionality
- models.py: Database models for recipients and messages
- sms_service.py: For actual message delivery

## Error Handling

- Validates both recipients exist before scheduling
- Ensures scheduled time is valid
- Handles database transaction atomically
- Returns clear error messages if scheduling fails

## Future Improvements

1. Add more sophisticated message splitting algorithms
2. Support different types of content (images, links)
3. Add message expiration
4. Implement message verification system
