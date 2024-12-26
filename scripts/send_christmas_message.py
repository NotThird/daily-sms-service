#!/usr/bin/env python3
"""Script to send Christmas messages to all active users."""

import os
import time
from dotenv import load_dotenv
from twilio.rest import Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.models import Recipient

def main():
    # Load environment variables
    load_dotenv()
    
    # Initialize database connection
    DATABASE_URL = "postgresql://austin_franklin_user:kZz1yqpwMLlfapljhJTjQgU7E4YTwgNy@dpg-cth7omogph6c73d9brog-a.oregon-postgres.render.com/austin_franklin"
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db_session = Session()
    
    # Initialize Twilio client
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )
    
    # Christmas message template
    christmas_message = (
        "🎄 Merry Christmas! May your day be filled with joy, warmth, and beautiful moments. "
        "Sending you heartfelt wishes for peace, happiness, and wonderful memories with loved ones. "
        "Happy Holidays! ✨🎁"
    )
    
    # Get all active recipients
    active_recipients = db_session.query(Recipient).filter(Recipient.is_active == True).all()
    total_recipients = len(active_recipients)
    
    print(f"Found {total_recipients} active recipients")
    
    # Send messages with rate limiting
    messages_sent = 0
    messages_failed = 0
    from_number = os.getenv('TWILIO_FROM_NUMBER')
    
    for recipient in active_recipients:
        try:
            message = client.messages.create(
                body=christmas_message,
                from_=from_number,
                to=recipient.phone_number
            )
            print(f"Message sent to {recipient.phone_number}! SID: {message.sid}")
            messages_sent += 1
            
            # Rate limiting: 5 messages per second (from .env TWILIO_MESSAGES_PER_SECOND)
            time.sleep(0.2)  # 1/5 second delay between messages
            
        except Exception as e:
            print(f"Error sending message to {recipient.phone_number}: {str(e)}")
            messages_failed += 1
    
    print(f"\nSummary:")
    print(f"Total recipients: {total_recipients}")
    print(f"Messages sent: {messages_sent}")
    print(f"Messages failed: {messages_failed}")

if __name__ == "__main__":
    main()
