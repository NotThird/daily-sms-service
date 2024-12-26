"""
Tests for message generation functionality.
Covers message generation, scheduling, and error handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import pytz
from .code import MessageGenerator
from .scheduler import MessageScheduler
from features.core.code import User, Message, db_session

# Test data
TEST_USER_DATA = {
    "id": 1,
    "name": "Test User",
    "timezone": "America/New_York",
    "preferences": {
        "tone": "uplifting",
        "topics": ["motivation", "growth"]
    }
}

TEST_MESSAGE_DATA = {
    "content": "Stay positive and keep growing!",
    "user_id": 1
}

@pytest.fixture
def db():
    """Create test database session."""
    with db_session() as session:
        yield session

@pytest.fixture
def generator():
    """Create message generator instance."""
    return MessageGenerator()

@pytest.fixture
def scheduler():
    """Create message scheduler instance."""
    return MessageScheduler()

@pytest.fixture
def test_user(db):
    """Create test user."""
    user = User(**TEST_USER_DATA)
    db.add(user)
    db.commit()
    return user

def test_message_generation(generator):
    """Test basic message generation."""
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value = {
            'choices': [{
                'message': {'content': TEST_MESSAGE_DATA['content']}
            }]
        }
        
        message = generator.generate_message(TEST_USER_DATA['preferences'])
        
        assert message is not None
        assert isinstance(message, str)
        assert len(message) > 0

def test_message_generation_with_history(generator, db, test_user):
    """Test message generation with history check."""
    # Add some message history
    history_message = Message(
        content="Previous message",
        user_id=test_user.id
    )
    db.add(history_message)
    db.commit()
    
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value = {
            'choices': [{
                'message': {'content': TEST_MESSAGE_DATA['content']}
            }]
        }
        
        message = generator.generate_message(
            TEST_USER_DATA['preferences'],
            user_id=test_user.id
        )
        
        # Verify history was included in prompt
        prompt = mock_openai.call_args[0][0]['messages'][0]['content']
        assert "Previous message" in prompt

def test_message_generation_failure(generator):
    """Test message generation failure handling."""
    with patch('openai.ChatCompletion.create', side_effect=Exception("API Error")):
        # Should fall back to pre-generated message
        message = generator.generate_message(TEST_USER_DATA['preferences'])
        
        assert message is not None
        assert isinstance(message, str)
        assert len(message) > 0

def test_content_filtering(generator):
    """Test message content filtering."""
    with patch('openai.ChatCompletion.create') as mock_openai:
        # Test inappropriate content
        mock_openai.return_value = {
            'choices': [{
                'message': {'content': "Inappropriate message with bad words"}
            }]
        }
        
        # Should generate new message or use fallback
        message = generator.generate_message(TEST_USER_DATA['preferences'])
        assert "Inappropriate" not in message

def test_schedule_message(scheduler, test_user):
    """Test message scheduling."""
    scheduled_time = scheduler.schedule_message(
        user_id=test_user.id,
        timezone=TEST_USER_DATA['timezone']
    )
    
    # Verify scheduled time is within delivery window
    user_tz = pytz.timezone(TEST_USER_DATA['timezone'])
    local_time = scheduled_time.astimezone(user_tz)
    
    assert 12 <= local_time.hour <= 17  # Between 12 PM and 5 PM
    assert local_time > datetime.now(user_tz)

def test_schedule_message_timezone_handling(scheduler):
    """Test timezone handling in scheduling."""
    timezones = ['America/New_York', 'Asia/Tokyo', 'Europe/London']
    
    for tz in timezones:
        scheduled_time = scheduler.schedule_message(
            user_id=1,
            timezone=tz
        )
        
        local_time = scheduled_time.astimezone(pytz.timezone(tz))
        assert 12 <= local_time.hour <= 17

def test_schedule_conflict_resolution(scheduler):
    """Test handling of scheduling conflicts."""
    # Schedule multiple messages
    times = [
        scheduler.schedule_message(user_id=1, timezone='UTC')
        for _ in range(5)
    ]
    
    # Verify no duplicate times
    assert len(set(times)) == len(times)

@pytest.mark.asyncio
async def test_async_message_generation(generator):
    """Test asynchronous message generation."""
    with patch('openai.ChatCompletion.acreate') as mock_openai:
        mock_openai.return_value = {
            'choices': [{
                'message': {'content': TEST_MESSAGE_DATA['content']}
            }]
        }
        
        message = await generator.generate_message_async(
            TEST_USER_DATA['preferences']
        )
        
        assert message is not None
        assert isinstance(message, str)

def test_retry_mechanism(generator):
    """Test retry mechanism for failed generation."""
    with patch('openai.ChatCompletion.create') as mock_openai:
        # Fail twice, succeed on third try
        mock_openai.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            {
                'choices': [{
                    'message': {'content': TEST_MESSAGE_DATA['content']}
                }]
            }
        ]
        
        message = generator.generate_message(TEST_USER_DATA['preferences'])
        
        assert message == TEST_MESSAGE_DATA['content']
        assert mock_openai.call_count == 3

def test_message_caching(generator):
    """Test message caching for similar prompts."""
    with patch('openai.ChatCompletion.create') as mock_openai:
        mock_openai.return_value = {
            'choices': [{
                'message': {'content': TEST_MESSAGE_DATA['content']}
            }]
        }
        
        # First call should hit API
        message1 = generator.generate_message(TEST_USER_DATA['preferences'])
        
        # Similar prompt should use cache
        message2 = generator.generate_message(TEST_USER_DATA['preferences'])
        
        assert mock_openai.call_count == 1
        assert message1 == message2

def test_scheduler_persistence(scheduler, db):
    """Test scheduler state persistence."""
    # Schedule message
    scheduled_time = scheduler.schedule_message(
        user_id=1,
        timezone='UTC'
    )
    
    # Simulate scheduler restart
    new_scheduler = MessageScheduler()
    
    # Should restore scheduled message
    assert new_scheduler.get_scheduled_message(1) is not None
