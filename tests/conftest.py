import pytest
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Base
from src.message_generator import MessageGenerator
from src.sms_service import SMSService

@pytest.fixture(scope="session")
def test_database():
    """Create a test database and tables."""
    # Use SQLite for testing
    database_url = "sqlite:///test.db"
    engine = create_engine(database_url)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    yield database_url
    
    # Clean up after tests
    Base.metadata.drop_all(engine)
    if os.path.exists("test.db"):
        os.remove("test.db")

@pytest.fixture(scope="session")
def db_engine(test_database):
    """Create a test database engine."""
    return create_engine(test_database)

@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a new database session for a test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    # Rollback the transaction and close connections
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="session")
def message_generator():
    """Create a message generator instance for testing."""
    return MessageGenerator("test_api_key")

@pytest.fixture(scope="session")
def sms_service():
    """Create an SMS service instance for testing."""
    return SMSService(
        account_sid="test_sid",
        auth_token="test_token",
        from_number="+1234567890"
    )

@pytest.fixture(scope="function")
def app_client():
    """Create a test client for the Flask application."""
    from src.app import app
    app.config['TESTING'] = True
    app.config['SERVER_NAME'] = 'localhost'
    
    with app.test_client() as client:
        yield client

@pytest.fixture(scope="function")
def mock_openai():
    """Mock OpenAI API responses."""
    import openai
    original_create = openai.ChatCompletion.create
    
    def mock_create(*args, **kwargs):
        class MockResponse:
            def __init__(self):
                self.choices = [
                    type('Choice', (), {
                        'message': type('Message', (), {
                            'content': "Test positive message"
                        })
                    })
                ]
        return MockResponse()
    
    openai.ChatCompletion.create = mock_create
    yield
    openai.ChatCompletion.create = original_create

@pytest.fixture(scope="function")
def mock_twilio():
    """Mock Twilio API responses."""
    from twilio.rest import Client
    original_create = Client.messages.create
    
    def mock_create(*args, **kwargs):
        return type('Message', (), {
            'sid': 'TEST_MSG_SID',
            'status': 'queued'
        })
    
    Client.messages.create = mock_create
    yield
    Client.messages.create = original_create

@pytest.fixture(scope="function")
def test_recipient(db_session):
    """Create a test recipient in the database."""
    from src.models import Recipient
    
    recipient = Recipient(
        phone_number="+1234567890",
        timezone="UTC",
        is_active=True
    )
    db_session.add(recipient)
    db_session.commit()
    
    return recipient

@pytest.fixture(scope="function")
def test_message_log(db_session, test_recipient):
    """Create a test message log in the database."""
    from src.models import MessageLog
    
    message_log = MessageLog(
        recipient_id=test_recipient.id,
        message_type="outbound",
        content="Test message",
        status="sent",
        twilio_sid="TEST_MSG_SID"
    )
    db_session.add(message_log)
    db_session.commit()
    
    return message_log

@pytest.fixture(scope="function")
def test_scheduled_message(db_session, test_recipient):
    """Create a test scheduled message in the database."""
    from src.models import ScheduledMessage
    from datetime import datetime, timedelta
    import pytz
    
    scheduled_time = datetime.now(pytz.UTC) + timedelta(hours=1)
    
    scheduled_msg = ScheduledMessage(
        recipient_id=test_recipient.id,
        scheduled_time=scheduled_time,
        status="pending"
    )
    db_session.add(scheduled_msg)
    db_session.commit()
    
    return scheduled_msg

def pytest_configure(config):
    """Configure test environment."""
    os.environ['TESTING'] = 'true'
    os.environ['DATABASE_URL'] = 'sqlite:///test.db'
    os.environ['OPENAI_API_KEY'] = 'test_api_key'
    os.environ['TWILIO_ACCOUNT_SID'] = 'test_sid'
    os.environ['TWILIO_AUTH_TOKEN'] = 'test_token'
    os.environ['TWILIO_FROM_NUMBER'] = '+1234567890'

def pytest_unconfigure(config):
    """Clean up test environment."""
    # Remove test environment variables
    test_vars = [
        'TESTING',
        'DATABASE_URL',
        'OPENAI_API_KEY',
        'TWILIO_ACCOUNT_SID',
        'TWILIO_AUTH_TOKEN',
        'TWILIO_FROM_NUMBER'
    ]
    for var in test_vars:
        os.environ.pop(var, None)
