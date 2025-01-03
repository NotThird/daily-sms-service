from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Dict
import logging
import time
import ssl
import certifi
import urllib3
import twilio.http.http_client
from .rate_limiter import rate_limit_sms

logger = logging.getLogger(__name__)

# Configure SSL for all requests
urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()
twilio.http.http_client.CA_BUNDLE = certifi.where()

def create_ssl_context():
    """Create a secure SSL context with system certificates."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context

# Set up SSL context
ssl_context = create_ssl_context()
urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context

class SMSService:
    """Handles SMS operations using Twilio."""
    
    def _refresh_client(self):
        """Refresh the Twilio client with a new SSL context."""
        ssl_context = create_ssl_context()
        urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context
        self.client = Client(self.account_sid, self.auth_token)
        self.client.http_client.verify = certifi.where()

    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Initialize Twilio client with credentials and validate them.
        Raises ValueError if credentials are invalid.
        """
        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Missing required credentials")
            
        # Set up SSL context
        ssl_context = create_ssl_context()
        
        # Configure urllib3 to use our SSL context
        urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()
        urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context

        # Store credentials
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.from_number = from_number

        # Initialize Twilio client
        self.client = Client(self.account_sid, self.auth_token)
        
        # Configure the client's HTTP client to use our SSL context
        self.client.http_client.verify = certifi.where()
        
        # Validate credentials on initialization
        try:
            account = self.client.api.accounts(account_sid).fetch()
            logger.info(f"Twilio account validated: {account.friendly_name}")
        except Exception as e:
            error_msg = f"Failed to validate Twilio credentials: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
    @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
    @rate_limit_sms()
    def send_message(self, to_number: str, message: str) -> Dict:
        """
        Send an SMS message using Twilio with enhanced status checking.
        Returns a dict with detailed status and message information.
        """
        try:
            # Try sending with current client
            try:
                message = self.client.messages.create(
                    body=message,
                    from_=self.from_number,
                    to=to_number,
                    status_callback=self._get_status_callback_url()
                )
            except Exception as e:
                if 'SSL' in str(e):
                    logger.info("SSL error encountered, refreshing client...")
                    # Try up to 3 times with fresh client
                    for attempt in range(3):
                        try:
                            self._refresh_client()
                            message = self.client.messages.create(
                                body=message,
                                from_=self.from_number,
                                to=to_number,
                                status_callback=self._get_status_callback_url()
                            )
                            break
                        except Exception as retry_e:
                            if attempt == 2:  # Last attempt failed
                                raise retry_e
                            logger.warning(f"Retry {attempt + 1} failed, trying again...")
                            time.sleep(1)  # Brief pause between retries
                else:
                    raise
            
            logger.info(f"Message sent successfully. SID: {message.sid}")
            
            # Check message status with retries
            final_status = self._poll_message_status(message.sid)
            
            return {
                'status': 'success',
                'message_sid': message.sid,
                'delivery_status': final_status['status'],
                'error_code': final_status.get('error_code'),
                'error_message': final_status.get('error_message'),
                'direction': final_status.get('direction'),
                'from_number': message.from_,
                'to_number': message.to,
                'price': final_status.get('price'),
                'price_unit': final_status.get('price_unit'),
                'date_sent': final_status.get('date_sent'),
                'date_updated': final_status.get('date_updated')
            }
            
        except TwilioRestException as e:
            error_msg = f"Twilio error: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message_sid': None,
                'status_code': e.code,
                'error': error_msg,
                'error_code': getattr(e, 'code', None),
                'error_message': str(e)
            }
            
        except Exception as e:
            error_msg = f"Unexpected error sending SMS: {str(e)}"
            logger.error(error_msg)
            return {
                'status': 'error',
                'message_sid': None,
                'status_code': 500,
                'error': error_msg,
                'error_code': None,
                'error_message': str(e)
            }

    def _poll_message_status(self, message_sid: str, max_attempts: int = 3, delay: int = 2) -> Dict:
        """
        Poll message status until final state or max attempts reached.
        Returns the final message status details.
        """
        final_states = ['delivered', 'failed', 'undelivered']
        
        for _ in range(max_attempts):
            status_info = self.get_message_status(message_sid)
            current_status = status_info['status']
            
            logger.debug(f"Message {message_sid} current status: {current_status}")
            
            if current_status in final_states:
                return status_info
                
            time.sleep(delay)
        
        return status_info

    @rate_limit_sms()
    def validate_phone_number(self, phone_number: str) -> bool:
        """
        Validate if a phone number is in correct format.
        Returns True if valid, False otherwise.
        """
        try:
            # Use Twilio Lookup API to validate number
            lookup = self.client.lookups.v2.phone_numbers(phone_number).fetch()
            return True
        except Exception as e:
            logger.error(f"Phone number validation failed: {str(e)}")
            return False

    def _get_status_callback_url(self) -> Optional[str]:
        """
        Get the webhook URL for delivery status callbacks.
        Should be configured in environment variables.
        """
        # This should be configured in your environment
        from os import getenv
        return getenv('TWILIO_STATUS_CALLBACK_URL')

    def process_delivery_status(self, status_data: Dict) -> Dict:
        """
        Process delivery status webhook from Twilio.
        Returns processed status information.
        """
        try:
            message_sid = status_data.get('MessageSid')
            message_status = status_data.get('MessageStatus')
            error_code = status_data.get('ErrorCode')
            
            logger.info(f"Message {message_sid} status update: {message_status}")
            
            return {
                'message_sid': message_sid,
                'status': message_status,
                'error_code': error_code,
                'processed': True
            }
            
        except Exception as e:
            error_msg = f"Error processing delivery status: {str(e)}"
            logger.error(error_msg)
            return {
                'error': error_msg,
                'processed': False
            }

    @rate_limit_sms()
    def get_message_status(self, message_sid: str) -> Dict:
        """
        Get detailed status information for a message by SID.
        """
        try:
            message = self.client.messages(message_sid).fetch()
            return {
                'status': message.status,
                'error_code': message.error_code,
                'error_message': message.error_message,
                'direction': message.direction,
                'from_number': message.from_,
                'to_number': message.to,
                'price': message.price,
                'price_unit': message.price_unit,
                'date_sent': message.date_sent,
                'date_updated': message.date_updated
            }
        except Exception as e:
            logger.error(f"Error fetching message status: {str(e)}")
            return {
                'status': 'error',
                'error_message': str(e)
            }

    def handle_opt_out(self, phone_number: str) -> bool:
        """
        Handle opt-out request.
        Returns True if successful, False otherwise.
        """
        try:
            # You might want to implement custom logic here
            # For now, we'll just log it
            logger.info(f"Processing opt-out for {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error processing opt-out: {str(e)}")
            return False

    def handle_opt_in(self, phone_number: str) -> bool:
        """
        Handle opt-in request.
        Returns True if successful, False otherwise.
        """
        try:
            # You might want to implement custom logic here
            # For now, we'll just log it
            logger.info(f"Processing opt-in for {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Error processing opt-in: {str(e)}")
            return False
