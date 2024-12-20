#!/usr/bin/env python3
"""
Script to manually process scheduled messages.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
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

def process_scheduled_messages(wait_time=None):
    """Process any pending scheduled messages."""
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
        
        if wait_time:
            print(f"\nWaiting {wait_time} seconds for scheduled message...")
            time.sleep(wait_time)
        
        # Process scheduled messages
        print("\nProcessing scheduled messages...")
        result = scheduler.process_scheduled_messages()
        
        print("\nProcessing results:")
        print(f"Messages sent: {result['sent']}")
        print(f"Messages failed: {result['failed']}")
        print(f"Total messages processed: {result['total']}")
        
    except Exception as e:
        print(f"\nError processing messages: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    # If no argument provided, wait 65 seconds (just over 1 minute)
    wait_time = int(sys.argv[1]) if len(sys.argv) > 1 else 65
    process_scheduled_messages(wait_time)
