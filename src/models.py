from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Recipient(db.Model):
    """Represents a message recipient with opt-in/out status."""
    __tablename__ = 'recipients'

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False)
    timezone = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserConfig(db.Model):
    """Stores user configuration and personalization settings."""
    __tablename__ = 'user_configs'

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    preferences = db.Column(db.JSON, nullable=False, default={})  # Stores GPT prompt preferences
    personal_info = db.Column(db.JSON, nullable=False, default={})  # Stores additional personal info
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class MessageLog(db.Model):
    """Logs all sent and received messages with detailed delivery information."""
    __tablename__ = 'message_logs'

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # 'outbound' or 'inbound'
    content = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'queued', 'sent', 'delivered', 'failed', etc.
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime, nullable=True)
    twilio_sid = db.Column(db.String(50), nullable=True)
    error_message = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=True)
    price_unit = db.Column(db.String(10), nullable=True)
    direction = db.Column(db.String(20), nullable=True)  # 'outbound-api', 'inbound', etc.

class ScheduledMessage(db.Model):
    """Tracks scheduled messages for the day."""
    __tablename__ = 'scheduled_messages'

    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'sent', 'failed'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)
