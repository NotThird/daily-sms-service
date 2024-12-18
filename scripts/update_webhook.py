#!/usr/bin/env python3
import os
from twilio.rest import Client
from dotenv import load_dotenv

def main():
    """Update Twilio webhook URLs for SMS."""
    print("Loading environment variables...")
    load_dotenv()
    
    # Initialize Twilio client
    client = Client(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN')
    )
    
    phone_number = os.getenv('TWILIO_FROM_NUMBER')
    base_url = os.getenv('TWILIO_STATUS_CALLBACK_URL').replace('/webhook/inbound', '')
    
    print(f"Updating webhook URLs for {phone_number}")
    print(f"Base URL: {base_url}")
    
    try:
        # Get the phone number instance
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        if not numbers:
            print(f"Error: Phone number {phone_number} not found in account")
            return
            
        number = numbers[0]
        
        # Update both webhook URLs
        number.update(
            sms_url=f"{base_url}/webhook/inbound",
            sms_method='POST',
            status_callback=f"{base_url}/webhook/status",
            status_callback_method='POST'
        )
        
        print("✅ Webhook URLs updated successfully")
        print(f"Inbound messages: {base_url}/webhook/inbound")
        print(f"Status callbacks: {base_url}/webhook/status")
        
    except Exception as e:
        print(f"❌ Error updating webhook URLs: {str(e)}")

if __name__ == "__main__":
    main()
