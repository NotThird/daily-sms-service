from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from tenacity import retry, stop_after_attempt, wait_exponential
from typing import Optional, Dict
import logging
import time
import ssl

logger = logging.getLogger(__name__)

class SMSService:
    """Handles SMS operations using Twilio."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """
        Initialize Twilio client with credentials and validate them.
        Raises ValueError if credentials are invalid.
        """
        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Missing required credentials")
            
        self.client = Client(
            account_sid, 
            auth_token,
            http_client_options={
                "ssl_version": ssl.PROTOCOL_TLSv1_2
            }
        )
        self.from_number = from_number
        
        # Validate credentials on initialization
        try:
            account = self.client.api.accounts(account_sid).fetch()
            logger.info(f"Twilio account validated: {account.friendly_name}")
        except Exception as e:
            error_msg = f"Failed to validate Twilio credentials: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def send_message(self, to_number: str, message: str) -> Dict:
        """
        Send an SMS message using Twilio with enhanced status checking.
        Returns a dict with detailed status and message information.
        """
        try:
            # Send the message
            message = self.client.messages.create(
                body=message,
                from_=self.from_number,
                to=to_number,
                status_callback=self._get_status_callback_url()
            )
            
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
