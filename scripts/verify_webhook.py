#!/usr/bin/env python3
import os
from twilio.rest import Client
from dotenv import load_dotenv

def main():
    """Verify Twilio webhook configuration."""
    print("Loading environment variables...")
    load_dotenv()
    
    # Initialize Twilio client
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )
    
    phone_number = os.getenv('TWILIO_FROM_NUMBER')
    
    print(f"\nChecking webhook configuration for {phone_number}")
    
    try:
        # Get the phone number instance
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            print(f"Error: Phone number {phone_number} not found in account")
            return
            
        number = numbers[0]
        
        # Print current configuration
        print("\nCurrent webhook configuration:")
        print(f"SMS URL: {number.sms_url}")
        print(f"SMS Method: {number.sms_method}")
        print(f"Status Callback: {number.status_callback}")
        print(f"Status Callback Method: {number.status_callback_method}")
        print(f"Voice URL: {number.voice_url}")
        print(f"Voice Method: {number.voice_method}")
        
    except Exception as e:
        print(f"❌ Error checking webhook configuration: {str(e)}")

if __name__ == "__main__":
    main()
