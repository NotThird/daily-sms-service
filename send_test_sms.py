from twilio.rest import Client
import os
import logging
import time
import ssl
import certifi
from dotenv import load_dotenv
from pathlib import Path
import urllib3

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure urllib3 to use system certificates
urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()

# Create SSL context with system certificates
def create_ssl_context():
    context = ssl.create_default_context(cafile=certifi.where())
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context

# Get the absolute path to .env file
env_path = Path('.') / '.env'
logger.debug(f"Loading .env file from: {env_path.absolute()}")

# Load environment variables with override
load_dotenv(env_path, override=True)

def send_test_sms():
    # Force reload specific variables
    os.environ['TWILIO_FROM_NUMBER'] = '+18065422438'
    os.environ['DEVELOPMENT_TEST_NUMBER'] = '+18777804236'

    # Get credentials from environment variables
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    from_number = os.getenv('TWILIO_FROM_NUMBER')
    to_number = os.getenv('DEVELOPMENT_TEST_NUMBER')

    # Debug: Print all relevant environment variables
    logger.debug("Environment variables loaded:")
    logger.debug(f"TWILIO_ACCOUNT_SID: {account_sid}")
    logger.debug(f"TWILIO_AUTH_TOKEN: {auth_token[:4]}..." if auth_token else "TWILIO_AUTH_TOKEN: None")
    logger.debug(f"TWILIO_FROM_NUMBER: {from_number}")
    logger.debug(f"DEVELOPMENT_TEST_NUMBER: {to_number}")

    print("\nUsing credentials:")
    print(f"Account SID: {account_sid}")
    print(f"Auth Token: {auth_token[:4]}..." if auth_token else "Auth Token: None")
    print(f"From Number: {from_number}")
    print(f"To Number: {to_number}")

    # Verify all required variables are present
    if not all([account_sid, auth_token, from_number, to_number]):
        print("\nError: Missing required environment variables!")
        if not account_sid:
            print("- TWILIO_ACCOUNT_SID is missing")
        if not auth_token:
            print("- TWILIO_AUTH_TOKEN is missing")
        if not from_number:
            print("- TWILIO_FROM_NUMBER is missing")
        if not to_number:
            print("- DEVELOPMENT_TEST_NUMBER is missing")
        return

    try:
        # Set up SSL context
        ssl_context = create_ssl_context()
        
        # Configure urllib3 to use our SSL context
        urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()
        urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context

        # Initialize Twilio client with SSL context
        client = Client(account_sid, auth_token)
        
        # Configure the client's HTTP client to use our SSL context
        client.http_client.verify = certifi.where()

        print("\nAttempting to validate credentials...")
        # Try to fetch account info first to validate credentials
        account = client.api.accounts(account_sid).fetch()
        print(f"Account validation successful: {account.friendly_name}")

        print("\nSending message...")
        # Send message
        message = client.messages.create(
            body="Test message using .env credentials",
            from_=from_number,
            to=to_number
        )

        print(f"\nMessage sent successfully!")
        print(f"Message SID: {message.sid}")
        print(f"Initial Status: {message.status}")

        # Wait and check final status
        print("\nChecking delivery status...")
        for i in range(3):  # Check status up to 3 times
            time.sleep(2)  # Wait 2 seconds between checks
            message = client.messages(message.sid).fetch()
            print(f"Current Status: {message.status}")
            if message.status in ['delivered', 'failed', 'undelivered']:
                break

        # Print final message details
        print(f"\nFinal Message Details:")
        print(f"Status: {message.status}")
        print(f"Error Code: {message.error_code or 'None'}")
        print(f"Error Message: {message.error_message or 'None'}")
        print(f"Direction: {message.direction}")
        print(f"From: {message.from_}")
        print(f"To: {message.to}")
        if hasattr(message, 'price'):
            print(f"Price: {message.price} {message.price_unit}")

    except Exception as e:
        print(f"\nError:")
        print(f"Type: {type(e)}")
        print(f"Message: {str(e)}")
        if hasattr(e, 'code'):
            print(f"Error code: {e.code}")
        if hasattr(e, 'msg'):
            print(f"Error message: {e.msg}")
        # Print SSL verification paths
        print(f"\nSSL Certificate Path: {certifi.where()}")
        print(f"SSL Context Verify Mode: {ssl_context.verify_mode}")
        print(f"SSL Context Check Hostname: {ssl_context.check_hostname}")

if __name__ == '__main__':
    send_test_sms()
