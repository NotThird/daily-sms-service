#!/usr/bin/env python
import os
import sys
from datetime import datetime, timedelta
import pytz
import time

import dotenv
from pathlib import Path

# Load environment variables
dotenv.load_dotenv()

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure SQLite for testing
os.environ['DATABASE_URL'] = 'sqlite:///test.db'

from src.app import app, db, message_scheduler, user_config_service
from src.models import Recipient, MessageLog, UserConfig, ScheduledMessage

# Initialize database and clean up old data
with app.app_context():
    db.create_all()
    # Clean up any existing scheduled messages
    ScheduledMessage.query.delete()
    # Clean up any existing message logs
    MessageLog.query.delete()
    # Clean up any existing user configs
    UserConfig.query.delete()
    # Clean up any existing recipients
    Recipient.query.delete()
    db.session.commit()

def test_scheduler():
    """Test the scheduler by creating a test recipient and verifying message scheduling."""
    with app.app_context():
        try:
            # Create or get test recipient
            phone_number = os.getenv('TEST_PHONE_NUMBER')
            if not phone_number:
                print("Please set TEST_PHONE_NUMBER environment variable")
                sys.exit(1)

            recipient = Recipient(
                phone_number=phone_number,
                timezone='UTC',
                is_active=True
            )
            db.session.add(recipient)
            db.session.flush()

            # Set preferred time to 2 minutes from now
            now = datetime.now(pytz.UTC)
            preferred_time = (now + timedelta(minutes=2)).strftime("%H:%M")
            
            # Update user config with preferred time
            user_config_service.create_or_update_config(
                recipient_id=recipient.id,
                preferences={'preferred_time': preferred_time}
            )
            
            print(f"\nTest setup complete:")
            print(f"Recipient ID: {recipient.id}")
            print(f"Phone Number: {phone_number}")
            print(f"Preferred Time: {preferred_time}")
            
            # Schedule messages
            print("\nScheduling messages...")
            schedule_result = message_scheduler.schedule_daily_messages()
            print(f"Schedule result: {schedule_result}")
            
            # Check scheduled messages
            print("\nChecking scheduled messages...")
            scheduled_msgs = ScheduledMessage.query.filter_by(
                recipient_id=recipient.id,
                status='pending'
            ).all()
            
            for msg in scheduled_msgs:
                local_time = msg.scheduled_time.astimezone(pytz.timezone(recipient.timezone))
                print(f"\nFound scheduled message:")
                print(f"Status: {msg.status}")
                print(f"Scheduled for: {local_time}")
                print(f"Current time: {datetime.now(pytz.UTC)}")
                
                # Convert preferred time to UTC for comparison
                hour, minute = map(int, preferred_time.split(':'))
                tz = pytz.timezone(recipient.timezone)
                current_time = datetime.now(tz)
                preferred_dt = tz.localize(
                    datetime.combine(
                        current_time.date(),
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                ).astimezone(pytz.UTC)

                # Compare the UTC times (ignoring date)
                if (msg.scheduled_time.hour == preferred_dt.hour and 
                    msg.scheduled_time.minute == preferred_dt.minute):
                    print("\n✅ TEST PASSED!")
                    print(f"Message successfully scheduled for:")
                    print(f"UTC time: {msg.scheduled_time}")
                    print(f"Local time: {local_time}")
                    print(f"Current time: {datetime.now(pytz.UTC)}")
                    return
            
            print("\n❌ TEST FAILED!")
            print(f"No message found scheduled for preferred time: {preferred_time}")
            print("Found instead:")
            for msg in scheduled_msgs:
                local_time = msg.scheduled_time.astimezone(pytz.timezone(recipient.timezone))
                print(f"UTC time: {msg.scheduled_time}")
                print(f"Local time: {local_time}")
                
        except Exception as e:
            print(f"Error during test: {str(e)}")
            raise

if __name__ == '__main__':
    test_scheduler()
