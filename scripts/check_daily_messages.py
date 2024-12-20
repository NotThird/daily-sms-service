#!/usr/bin/env python3
"""
Script to check and clean up daily scheduled messages.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

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

from src.models import ScheduledMessage, MessageLog, Recipient

def check_daily_messages():
    """Check and clean up daily scheduled messages."""
    # Setup database connection
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get message statistics for the last 24 hours
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Check scheduled messages
        scheduled_count = session.query(ScheduledMessage).filter(
            ScheduledMessage.created_at >= cutoff_time
        ).count()
        
        pending_count = session.query(ScheduledMessage).filter(
            ScheduledMessage.status == 'pending'
        ).count()
        
        # Check message logs
        sent_logs = session.query(MessageLog).filter(
            MessageLog.sent_at >= cutoff_time,
            MessageLog.status == 'sent'
        ).all()
        
        # Group messages by recipient
        messages_by_recipient = {}
        for log in sent_logs:
            if log.recipient_id not in messages_by_recipient:
                messages_by_recipient[log.recipient_id] = []
            messages_by_recipient[log.recipient_id].append(log)
        
        print("\nLast 24 Hours Statistics:")
        print(f"Total scheduled messages: {scheduled_count}")
        print(f"Currently pending messages: {pending_count}")
        print(f"Total sent messages: {len(sent_logs)}")
        
        if messages_by_recipient:
            print("\nMessages per recipient:")
            for recipient_id, messages in messages_by_recipient.items():
                recipient = session.query(Recipient).get(recipient_id)
                if recipient:
                    print(f"\nRecipient {recipient.phone_number}:")
                    print(f"Message count: {len(messages)}")
                    print("Message times:")
                    for msg in messages:
                        print(f"- {msg.sent_at} UTC: {msg.content[:50]}...")
        
        if pending_count > 0:
            print(f"\nFound {pending_count} pending messages")
            print("\nWould you like to:")
            print("1. Cancel all pending messages")
            print("2. Show pending message details")
            print("3. Exit")
            
            choice = input("\nEnter choice (1-3): ")
            
            if choice == '1':
                session.query(ScheduledMessage).filter(
                    ScheduledMessage.status == 'pending'
                ).update({'status': 'cancelled'})
                session.commit()
                print("\nAll pending messages have been cancelled")
                
            elif choice == '2':
                pending_messages = session.query(ScheduledMessage).filter(
                    ScheduledMessage.status == 'pending'
                ).all()
                
                print("\nPending messages:")
                for msg in pending_messages:
                    recipient = session.query(Recipient).get(msg.recipient_id)
                    print(f"\nMessage ID: {msg.id}")
                    print(f"Recipient: {recipient.phone_number if recipient else 'Unknown'}")
                    print(f"Scheduled Time: {msg.scheduled_time}")
                    print(f"Content: {msg.content[:50]}...")
        
    except Exception as e:
        print(f"\nError checking messages: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    check_daily_messages()
