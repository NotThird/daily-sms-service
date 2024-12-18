#!/usr/bin/env python3
import os
import requests
from dotenv import load_dotenv

def main():
    """Simulate an incoming SMS message by calling the webhook directly."""
    print("Loading environment variables...")
    load_dotenv()
    
    webhook_url = os.getenv('TWILIO_STATUS_CALLBACK_URL')
    from_number = os.getenv('DEVELOPMENT_TEST_NUMBER')
    
    print(f"\nSending simulated incoming message to {webhook_url}")
    print(f"From: {from_number}")
    
    # Simulate Twilio's webhook POST data
    data = {
        'From': from_number,
        'To': os.getenv('TWILIO_FROM_NUMBER'),
        'Body': 'Hi there',
        'MessageSid': 'SM_TEST_123',
        'AccountSid': os.getenv('TWILIO_ACCOUNT_SID')
    }
    
    try:
        response = requests.post(webhook_url, data=data)
        print(f"\nResponse status code: {response.status_code}")
        print(f"Response body: {response.text}")
        
    except Exception as e:
        print(f"Error sending request: {str(e)}")

if __name__ == "__main__":
    main()
