#!/usr/bin/env python3
"""
Script to demonstrate when LLM content is generated vs when it's sent.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pytz
import time

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

def test_llm_scheduling():
    """Test when LLM content is generated vs when it's sent."""
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
        
        print("\nStep 1: Generating LLM content now...")
        message = message_generator.generate_message({
            'previous_messages': []
        })
        print(f"Generated content: {message}")
        
        # Schedule message for 1 minute from now
        scheduled_time = datetime.now(pytz.UTC) + timedelta(minutes=1)
        
        print(f"\nStep 2: Storing content for scheduled delivery at {scheduled_time}...")
        scheduled_msg = ScheduledMessage(
            recipient_id=recipient.id,
            scheduled_time=scheduled_time,
            status='pending',
            content=message
        )
        
        session.add(scheduled_msg)
        session.commit()
        print("Content stored in database")
        
        print("\nStep 3: Waiting 30 seconds...")
        time.sleep(30)
        
        print("\nStep 4: Checking stored content...")
        stored_msg = session.query(ScheduledMessage).get(scheduled_msg.id)
        print(f"Content in database: {stored_msg.content}")
        print("(Notice it's the same as what was generated)")
        
        print("\nStep 5: Waiting 30 more seconds for scheduled time...")
        time.sleep(30)
        
        print("\nStep 6: Processing scheduled message...")
        result = scheduler.process_scheduled_messages()
        print(f"Processing results: {result}")
        print("(Notice the message was sent using the pre-generated content)")
        
    except Exception as e:
        print(f"\nError in test: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    test_llm_scheduling()
