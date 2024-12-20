#!/usr/bin/env python3
"""
Script to schedule a split secret message between two recipients.
"""
from datetime import datetime, timedelta
import argparse
import pytz
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the root directory
root_dir = Path(__file__).resolve().parent.parent
dotenv_path = root_dir / '.env'

# Force reload environment variables
if os.path.exists(dotenv_path):
    print(f"\nFound .env file at: {dotenv_path}")
    # Clear any existing env vars
    for key in ['DATABASE_URL']:
        if key in os.environ:
            del os.environ[key]
    # Load fresh env vars
    load_dotenv(dotenv_path, override=True)
else:
    print(f"Error: .env file not found at {dotenv_path}")
    sys.exit(1)

# Add the src directory to the Python path
sys.path.append(str(root_dir))

from src.features.split_messages.code import SplitMessageService
from src.models import Recipient

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Schedule a split secret message.')
    parser.add_argument('--message', type=str, help='The complete message to split')
    parser.add_argument('--recipient1', type=str, help='First recipient phone number')
    parser.add_argument('--recipient2', type=str, help='Second recipient phone number')
    parser.add_argument('--minutes', type=int, default=10, help='Minutes from now to schedule (default: 10)')
    
    args = parser.parse_args()
    
    # Set default values if not provided
    if not args.message:
        args.message = "A mysterious map leads to a hidden fortune beneath the ancient willow where moonlight meets shadow at midnight's dance"
    if not args.recipient1:
        args.recipient1 = "+18065351575"  # Austin
    if not args.recipient2:
        args.recipient2 = "+12146822825"  # Monica
    if not args.minutes:
        args.minutes = 10
    
    return args

def schedule_split_message(message=None, recipient1=None, recipient2=None, minutes=10):
    """Schedule a split message between two recipients."""
    # Setup database connection
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("Error: DATABASE_URL environment variable not set")
        return
    
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("\nQuerying recipients...")
        
        # Get recipients
        recipient1_obj = session.query(Recipient).filter_by(phone_number=recipient1).first()
        recipient2_obj = session.query(Recipient).filter_by(phone_number=recipient2).first()
        
        print(f"Recipient 1 ({recipient1}): {'Found' if recipient1_obj else 'Not found'}")
        print(f"Recipient 2 ({recipient2}): {'Found' if recipient2_obj else 'Not found'}")
        
        if not recipient1_obj or not recipient2_obj:
            print("\nError: Both recipients must be registered in the system")
            return
        
        # Create service
        service = SplitMessageService(session)
        
        # Set scheduled time to X minutes from now in recipients' timezone
        tz = pytz.timezone(recipient1_obj.timezone)  # Using first recipient's timezone
        now = datetime.now(tz)
        scheduled_time = now + timedelta(minutes=minutes)
        
        # Preview the split message
        part1, part2 = service.split_message(message)
        print("\nMessage preview:")
        print(f"Part 1: {part1}")
        print(f"Part 2: {part2}")
        
        # Confirm scheduling
        print(f"\nSchedule this message for {scheduled_time.strftime('%I:%M %p')}? [y/N]")
        confirm = input()
        if confirm.lower() != 'y':
            print("Message scheduling cancelled")
            return
        
        # Schedule the split message
        result = service.schedule_split_message(
            message=message,
            recipient1_phone=recipient1_obj.phone_number,
            recipient2_phone=recipient2_obj.phone_number,
            scheduled_time=scheduled_time
        )
        
        print("\nSuccessfully scheduled split message!")
        print(f"Scheduled for: {scheduled_time.strftime('%I:%M %p %Z')}")
        print("\nMessage parts:")
        print(f"Recipient 1 will receive: {result['recipient1_message']}")
        print(f"Recipient 2 will receive: {result['recipient2_message']}")
        
    except Exception as e:
        print(f"\nError scheduling message: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    args = parse_args()
    schedule_split_message(
        message=args.message,
        recipient1=args.recipient1,
        recipient2=args.recipient2,
        minutes=args.minutes
    )
