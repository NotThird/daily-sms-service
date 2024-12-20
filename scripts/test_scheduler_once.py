#!/usr/bin/env python3
"""
Script to test scheduling a single message for immediate delivery.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pytz

# Load environment variables from the root directory
root_dir = Path(__file__).resolve().parent.parent
dotenv_path = root_dir / '.env'

# Force reload environment variables
if os.path.exists(dotenv_path):
    print(f"\nFound .env file at: {dotenv_path}")
    load_dotenv(dotenv_path, override=True)
else:
    print(f"Error: .env file not found at {dotenv_path}")
    sys.exit(1)

# Add the src directory to the Python path
sys.path.append(str(root_dir))

from src.message_generator import MessageGenerator
from src.sms_service import SMSService
from src.user_config_service import UserConfigService
from src.scheduler import MessageScheduler
from src.models import Recipient, ScheduledMessage

def test_scheduler():
    """Test scheduling and sending a single message."""
    # Setup database connection
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Initialize required services
        message_generator = MessageGenerator(os.getenv('OPENAI_API_KEY'))
        user_config_service = UserConfigService(session)
        sms_service = SMSService(
            account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
            auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
            from_number=os.getenv('TWILIO_FROM_NUMBER')
        )
        
        # Initialize scheduler
        scheduler = MessageScheduler(session, message_generator, sms_service, user_config_service)
        
        # Get test recipient (Austin)
        recipient = session.query(Recipient).filter_by(phone_number="+18065351575").first()
        if not recipient:
            print("Error: Test recipient not found")
            return
        
        # Generate message content
        message = message_generator.generate_message({
            'previous_messages': []
        })
        
        # Schedule message for 1 minute from now
        scheduled_time = datetime.now(pytz.UTC) + timedelta(minutes=1)
        
        # Create scheduled message
        scheduled_msg = ScheduledMessage(
            recipient_id=recipient.id,
            scheduled_time=scheduled_time,
            status='pending',
            content=message
        )
        
        session.add(scheduled_msg)
        session.commit()
        
        print(f"\nScheduled message for {recipient.phone_number}")
        print(f"Scheduled time: {scheduled_time}")
        print(f"Content: {message}")
        
        print("\nWaiting 1 minute for message to be due...")
        print("You can run 'python scripts/check_daily_messages.py' to monitor status")
        
    except Exception as e:
        print(f"\nError in test: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    test_scheduler()
