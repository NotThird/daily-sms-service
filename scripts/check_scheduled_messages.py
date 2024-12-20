#!/usr/bin/env python3
"""
Script to check and clean up scheduled messages.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

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

from src.models import ScheduledMessage

def check_scheduled_messages():
    """Check and clean up scheduled messages."""
    # Setup database connection
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get all pending messages
        pending_messages = session.query(ScheduledMessage).filter(
            ScheduledMessage.status == 'pending'
        ).all()
        
        print(f"\nFound {len(pending_messages)} pending messages")
        
        if pending_messages:
            print("\nPending messages:")
            for msg in pending_messages:
                print(f"\nMessage ID: {msg.id}")
                print(f"Recipient ID: {msg.recipient_id}")
                print(f"Scheduled Time: {msg.scheduled_time}")
                print(f"Content: {msg.content}")
            
            # Ask if we should mark these messages as cancelled
            print("\nWould you like to cancel these pending messages? [y/N]: ")
            confirm = input()
            if confirm.lower() == 'y':
                for msg in pending_messages:
                    msg.status = 'cancelled'
                    print(f"Cancelled message {msg.id}")
                session.commit()
                print("\nAll pending messages have been cancelled")
            else:
                print("\nNo changes made")
        
    except Exception as e:
        print(f"\nError checking messages: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    check_scheduled_messages()
