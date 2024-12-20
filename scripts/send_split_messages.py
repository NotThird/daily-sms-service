#!/usr/bin/env python3
"""
Script to immediately send split messages to recipients.
"""
from datetime import datetime
import argparse
import os
import sys
from pathlib import Path
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Load environment variables from the root directory
root_dir = Path(__file__).resolve().parent.parent
dotenv_path = root_dir / '.env'

# Force reload environment variables
if os.path.exists(dotenv_path):
    print(f"\nFound .env file at: {dotenv_path}")
    # Clear any existing env vars
    for key in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER', 'DATABASE_URL']:
        if key in os.environ:
            del os.environ[key]
    # Load fresh env vars
    load_dotenv(dotenv_path, override=True)
else:
    print(f"Error: .env file not found at {dotenv_path}")
    sys.exit(1)

# Add the src directory to the Python path
sys.path.append(str(root_dir))

from src.sms_service import SMSService
from src.models import Recipient
from src.features.split_messages.code import SplitMessageService

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Send split messages to two recipients.')
    parser.add_argument('--message', type=str, help='The complete message to split')
    parser.add_argument('--recipient1', type=str, help='First recipient phone number')
    parser.add_argument('--recipient2', type=str, help='Second recipient phone number')
    
    # If no args provided, use defaults for Austin and Monica
    args = parser.parse_args()
    if not any(vars(args).values()):
        args.recipient1 = "+18065351575"  # Austin
        args.recipient2 = "+12146822825"  # Monica
        args.message = "The treasure is hidden under the old oak tree in central park"
    
    return args

def send_split_messages(message=None, recipient1=None, recipient2=None):
    """Send split messages to recipients immediately."""
    # Debug: Print environment variables
    print("\nLoaded environment variables:")
    print(f"TWILIO_ACCOUNT_SID: {os.getenv('TWILIO_ACCOUNT_SID')}")
    print(f"TWILIO_AUTH_TOKEN: {os.getenv('TWILIO_AUTH_TOKEN')}")
    print(f"TWILIO_FROM_NUMBER: {os.getenv('TWILIO_FROM_NUMBER')}")
    print(f"DATABASE_URL exists: {'Yes' if os.getenv('DATABASE_URL') else 'No'}")
    
    # Verify required environment variables
    required_vars = ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER', 'DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"\nError: Missing required environment variables: {', '.join(missing_vars)}")
        return
    
    # Setup database connection
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get recipients
        recipient1_obj = session.query(Recipient).filter_by(phone_number=recipient1).first()
        recipient2_obj = session.query(Recipient).filter_by(phone_number=recipient2).first()
        
        if not recipient1_obj or not recipient2_obj:
            print(f"\nError: Recipients must be registered in the system")
            print(f"Recipient 1 ({recipient1}): {'Found' if recipient1_obj else 'Not found'}")
            print(f"Recipient 2 ({recipient2}): {'Found' if recipient2_obj else 'Not found'}")
            return
        
        # Initialize services
        split_service = SplitMessageService(session)
        sms_service = SMSService(
            account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
            auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
            from_number=os.getenv('TWILIO_FROM_NUMBER')
        )
        
        # Split message using the service
        try:
            part1, part2 = split_service.split_message(message)
        except Exception as e:
            print(f"\nError splitting message: {str(e)}")
            return
        
        print("\nSplit message preview:")
        print(f"Part 1: {part1}")
        print(f"Part 2: {part2}")
        
        # Confirm before sending
        confirm = input("\nSend these messages? [y/N]: ")
        if confirm.lower() != 'y':
            print("Message sending cancelled")
            return
        
        # Send messages
        try:
            result1 = sms_service.send_message(recipient1_obj.phone_number, f"Part 1 of split message: {part1}")
            result2 = sms_service.send_message(recipient2_obj.phone_number, f"Part 2 of split message: {part2}")
            
            print("\nMessage sending results:")
            print(f"Recipient 1 ({recipient1}): {result1['status']}")
            print(f"Recipient 2 ({recipient2}): {result2['status']}")
            
        except Exception as e:
            print(f"\nError sending messages: {str(e)}")
            
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
    finally:
        session.close()

if __name__ == "__main__":
    args = parse_args()
    send_split_messages(
        message=args.message,
        recipient1=args.recipient1,
        recipient2=args.recipient2
    )
