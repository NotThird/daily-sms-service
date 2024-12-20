"""Tests for the split message feature."""
import pytest
from datetime import datetime, timedelta
from src.models import Recipient, ScheduledMessage
from src.features.split_messages.code import SplitMessageService

def test_split_message():
    """Test message splitting logic."""
    service = SplitMessageService(None)  # No DB needed for this test
    
    # Test basic splitting
    message = "This is a secret message"
    part1, part2 = service.split_message(message)
    
    assert part1 == "This ___ a ___ message"
    assert part2 == "___ is ___ secret ___"
    
    # Test with odd number of words
    message = "Hello world how are you"
    part1, part2 = service.split_message(message)
    
    assert part1 == "Hello ___ how ___ you"
    assert part2 == "___ world ___ are ___"

def test_schedule_split_message(db_session):
    """Test scheduling split messages."""
    # Create test recipients
    recipient1 = Recipient(
        phone_number="+1234567890",
        timezone="UTC",
        is_active=True
    )
    recipient2 = Recipient(
        phone_number="+0987654321",
        timezone="UTC",
        is_active=True
    )
    db_session.add(recipient1)
    db_session.add(recipient2)
    db_session.commit()
    
    service = SplitMessageService(db_session)
    scheduled_time = datetime.utcnow() + timedelta(hours=1)
    
    # Schedule split message
    result = service.schedule_split_message(
        message="This is a secret message",
        recipient1_phone="+1234567890",
        recipient2_phone="+0987654321",
        scheduled_time=scheduled_time
    )
    
    # Verify result format
    assert "recipient1_message" in result
    assert "recipient2_message" in result
    assert "scheduled_time" in result
    
    # Verify scheduled messages in database
    scheduled_msgs = db_session.query(ScheduledMessage).all()
    assert len(scheduled_msgs) == 2
    
    # Verify message content
    messages = [msg.content for msg in scheduled_msgs]
    assert "Part 1 of split message: This ___ a ___ message" in messages
    assert "Part 2 of split message: ___ is ___ secret ___" in messages
    
    # Verify scheduling
    for msg in scheduled_msgs:
        assert msg.scheduled_time == scheduled_time
        assert msg.status == "pending"

def test_invalid_recipients(db_session):
    """Test handling of invalid recipients."""
    service = SplitMessageService(db_session)
    scheduled_time = datetime.utcnow() + timedelta(hours=1)
    
    # Test with non-existent recipients
    with pytest.raises(ValueError, match="Both recipients must exist in the system"):
        service.schedule_split_message(
            message="This is a test",
            recipient1_phone="+1111111111",
            recipient2_phone="+2222222222",
            scheduled_time=scheduled_time
        )
    
    # Verify no messages were scheduled
    scheduled_msgs = db_session.query(ScheduledMessage).all()
    assert len(scheduled_msgs) == 0
