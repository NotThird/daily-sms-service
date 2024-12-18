from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, create_engine, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Recipient(Base):
    """Represents a message recipient with opt-in/out status."""
    __tablename__ = 'recipients'

    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True, nullable=False)
    timezone = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserConfig(Base):
    """Stores user configuration and personalization settings."""
    __tablename__ = 'user_configs'

    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=True)
    email = Column(String(255), nullable=True)
    preferences = Column(JSON, nullable=False, default={})  # Stores GPT prompt preferences
    personal_info = Column(JSON, nullable=False, default={})  # Stores additional personal info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MessageLog(Base):
    """Logs all sent and received messages with detailed delivery information."""
    __tablename__ = 'message_logs'

    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, nullable=False)
    message_type = Column(String(20), nullable=False)  # 'outbound' or 'inbound'
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # 'queued', 'sent', 'delivered', 'failed', etc.
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    twilio_sid = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    price = Column(Float, nullable=True)
    price_unit = Column(String(10), nullable=True)
    direction = Column(String(20), nullable=True)  # 'outbound-api', 'inbound', etc.

class ScheduledMessage(Base):
    """Tracks scheduled messages for the day."""
    __tablename__ = 'scheduled_messages'

    id = Column(Integer, primary_key=True)
    recipient_id = Column(Integer, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    status = Column(String(20), default='pending')  # 'pending', 'sent', 'failed'
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

def init_db(database_url):
    """Initialize database connection and create tables."""
    engine = create_engine(database_url)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)

def get_db_session(database_url):
    """Get a new database session."""
    Session = init_db(database_url)
    return Session()
