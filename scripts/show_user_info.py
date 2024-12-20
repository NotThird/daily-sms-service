#!/usr/bin/env python
import os
import sys
from datetime import datetime, timedelta
import pytz
import dotenv
from pathlib import Path

# Load environment variables
dotenv.load_dotenv()

# Add the src directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Initialize database
if not os.getenv('DATABASE_URL'):
    db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test.db')
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

from src.app import app, db
from src.models import Recipient, MessageLog, UserConfig, ScheduledMessage
from src.scheduler import MessageScheduler
from src.message_generator import MessageGenerator
from src.sms_service import SMSService
from src.user_config_service import UserConfigService

def show_user_info(phone_number=None):
    """Show user information and message history."""
    with app.app_context():
        try:
            # Initialize database
            db.create_all()

            # Get all recipients or filter by phone number
            query = Recipient.query
            if phone_number:
                query = query.filter_by(phone_number=phone_number)
            recipients = query.all()

            if not recipients and phone_number:
                print(f"Creating test user with phone number {phone_number}...")
                recipient = Recipient(
                    phone_number=phone_number,
                    timezone='UTC',
                    is_active=True,
                    created_at=datetime.utcnow()
                )
                db.session.add(recipient)
                db.session.flush()  # Get the ID
                
                # Add test config
                preferred_time = (datetime.now(pytz.UTC) + timedelta(minutes=2)).strftime("%H:%M")
                config = UserConfig(
                    recipient_id=recipient.id,
                    preferences={'preferred_time': preferred_time}
                )
                db.session.add(config)
                
                # Initialize services
                message_generator = MessageGenerator(os.getenv('OPENAI_API_KEY', 'dummy_key'))
                sms_service = SMSService(
                    os.getenv('TWILIO_ACCOUNT_SID', 'dummy_sid'),
                    os.getenv('TWILIO_AUTH_TOKEN', 'dummy_token'),
                    os.getenv('TWILIO_FROM_NUMBER', '+1234567890')
                )
                user_config_service = UserConfigService(db.session)
                
                # Schedule a test message
                scheduler = MessageScheduler(db.session, message_generator, sms_service, user_config_service)
                scheduler.schedule_daily_messages()
                
                db.session.commit()
                recipients = [recipient]
            elif not recipients:
                print("No users found")
                return

            for recipient in recipients:
                print("\n" + "="*50)
                print(f"User Information:")
                print(f"ID: {recipient.id}")
                print(f"Phone Number: {recipient.phone_number}")
                print(f"Timezone: {recipient.timezone}")
                print(f"Active: {recipient.is_active}")
                print(f"Created: {recipient.created_at}")
                
                # Get user config
                config = UserConfig.query.filter_by(recipient_id=recipient.id).first()
                if config:
                    print("\nUser Configuration:")
                    print(f"Name: {config.name}")
                    print(f"Preferences: {config.preferences}")
                    print(f"Personal Info: {config.personal_info}")
                
                # Get scheduled messages
                scheduled = ScheduledMessage.query.filter_by(
                    recipient_id=recipient.id,
                    status='pending'
                ).all()
                if scheduled:
                    print("\nScheduled Messages:")
                    for msg in scheduled:
                        local_time = msg.scheduled_time.astimezone(pytz.timezone(recipient.timezone))
                        print(f"- Scheduled for: {local_time} ({msg.status})")
                else:
                    print("\nNo scheduled messages")
                
                # Get recent message history
                recent_msgs = MessageLog.query.filter_by(
                    recipient_id=recipient.id
                ).order_by(MessageLog.sent_at.desc()).limit(5).all()
                
                if recent_msgs:
                    print("\nRecent Messages:")
                    for msg in recent_msgs:
                        print(f"\nType: {msg.message_type}")
                        print(f"Status: {msg.status}")
                        print(f"Time: {msg.sent_at}")
                        print(f"Content: {msg.content[:100] if msg.content else 'None'}...")
                        if msg.error_message:
                            print(f"Error: {msg.error_message}")
                else:
                    print("\nNo message history")

        except Exception as e:
            print(f"Error retrieving user information: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        show_user_info(sys.argv[1])
    else:
        show_user_info()
