# Split Messages Feature Folder

## Status: Ready for Use

This folder contains the implementation of the split message feature, which enables sending secret messages split between two recipients.

## Contents

- `code.py`: Main implementation of the SplitMessageService
- `tests.py`: Unit tests for the split message functionality
- `README.md`: Detailed documentation of the feature

## Current State

The feature is fully implemented with the following capabilities:
- Message splitting using alternating word pattern
- Scheduled delivery at specific times
- Support for multiple recipient pairs
- Error handling for invalid recipients

## Recent Updates

- Initial implementation of split message feature
- Added tests for core functionality
- Added database migration for message content field
- Created demonstration script

## Dependencies

- Core Dependencies:
  - SQLAlchemy for database operations
  - PyTZ for timezone handling
  
- Internal Dependencies:
  - models.py: For database models
  - scheduler.py: For message scheduling
  - sms_service.py: For message delivery

## Usage Example

```python
from datetime import datetime
from features.split_messages.code import SplitMessageService

service = SplitMessageService(db_session)
result = service.schedule_split_message(
    message="Secret message here",
    recipient1_phone="+1234567890",
    recipient2_phone="+0987654321",
    scheduled_time=datetime(2024, 1, 20, 22, 40)
)
```

## Testing

Run the tests using:
```bash
pytest src/features/split_messages/tests.py
