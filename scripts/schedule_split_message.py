#!/usr/bin/env python3
"""
Script to schedule a split secret message between two recipients.
"""
from datetime import datetime
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.features.split_messages.code import SplitMessageService
from src.models import Recipient, db

def schedule_split_message():
    """Schedule a split message for Austin and Monica."""
    # Setup database connection
    db_url = "postgresql://austin_franklin_user:kZz1yqpwMLlfapljhJTjQgU7E4YTwgNy@dpg-cth7omogph6c73d9brog-a.oregon-postgres.render.com/austin_franklin"
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print(f"Database URL: {os.getenv('DATABASE_URL')}")
        print("\nQuerying recipients...")
        
        # Get recipients
        austin = session.query(Recipient).filter_by(phone_number="+18065351575").first()
        monica = session.query(Recipient).filter_by(phone_number="+12146822825").first()
        
        print(f"Found Austin: {austin is not None}")
        print(f"Found Monica: {monica is not None}")
        
        if not austin or not monica:
            print("Error: Both Austin and Monica must be registered in the system")
            return
        
        # Create service
        service = SplitMessageService(session)
        
        # Set scheduled time for 10:50 PM in recipients' timezone
        tz = pytz.timezone(austin.timezone)  # Assuming both recipients are in same timezone
        now = datetime.now(tz)
        scheduled_time = now.replace(hour=22, minute=50, second=0, microsecond=0)
        
        # If 10:50 PM has passed for today, schedule for tomorrow
        if scheduled_time <= now:
            scheduled_time = scheduled_time.replace(day=scheduled_time.day + 1)
        
        # Schedule the split message
        secret_message = "The treasure is hidden under the old oak tree in central park"
        result = service.schedule_split_message(
            message=secret_message,
            recipient1_phone=austin.phone_number,
            recipient2_phone=monica.phone_number,
            scheduled_time=scheduled_time
        )
        
        print("\nSuccessfully scheduled split message!")
        print(f"Scheduled for: {scheduled_time}")
        print("\nMessage preview:")
        print(f"Austin will receive: {result['recipient1_message']}")
        print(f"Monica will receive: {result['recipient2_message']}")
        
    except Exception as e:
        print(f"Error scheduling message: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    schedule_split_message()
