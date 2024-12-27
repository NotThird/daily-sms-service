"""
SMS Service
----------
Description: Handles SMS sending and delivery status tracking using Twilio
Authors: AI Assistant
Date Created: 2024-01-09
Dependencies:
  - twilio
  - rate_limiting
"""

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import re
from typing import Dict, Any, Optional
from src.features.rate_limiting.code import rate_limit_sms

class SMSService:
    """Handles SMS operations using Twilio."""
    
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        """Initialize with Twilio credentials."""
        if not all([account_sid, auth_token, from_number]):
            raise ValueError("Missing required Twilio credentials")
            
        self.client = Client(account_sid, auth_token)
        self.from_number = self._sanitize_phone(from_number)
        
    @staticmethod
    def _sanitize_phone(phone: str) -> str:
        """
        Sanitize phone numbers to prevent injection.
        Strips all non-numeric characters and ensures proper format.
        """
        clean = re.sub(r'\D', '', phone)
        if len(clean) == 10:
            return f"+1{clean}"
        elif len(clean) == 11 and clean.startswith('1'):
            return f"+{clean}"
        elif len(clean) == 12 and clean.startswith('91'):
            return f"+{clean}"
        raise ValueError("Invalid phone number format")
        
    def validate_phone_number(self, phone: str) -> bool:
        """Validate phone number format."""
        try:
            self._sanitize_phone(phone)
            return True
        except ValueError:
            return False
            
    @rate_limit_sms()
    def send_message(self, to_number: str, message: str) -> Dict[str, Any]:
        """
        Send an SMS message using Twilio.
        Returns delivery status and message details.
        """
        try:
            to_number = self._sanitize_phone(to_number)
            
            message = self.client.messages.create(
                to=to_number,
                from_=self.from_number,
                body=message
            )
            
            return {
                'message_sid': message.sid,
                'delivery_status': message.status,
                'price': message.price,
                'price_unit': message.price_unit
            }
            
        except TwilioRestException as e:
            return {
                'delivery_status': 'failed',
                'error_message': str(e),
                'message_sid': None
            }
            
    def get_message_status(self, message_sid: str) -> Dict[str, Any]:
        """Get the current status of a sent message."""
        try:
            message = self.client.messages(message_sid).fetch()
            return {
                'status': message.status,
                'error_message': message.error_message,
                'price': message.price,
                'price_unit': message.price_unit
            }
        except TwilioRestException as e:
            return {
                'status': 'error',
                'error_message': str(e)
            }
            
    def process_delivery_status(self, callback_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process Twilio delivery status callback."""
        message_sid = callback_data.get('MessageSid')
        if not message_sid:
            return {
                'processed': False,
                'error': 'Missing MessageSid'
            }
            
        return {
            'processed': True,
            'message_sid': message_sid,
            'status': callback_data.get('MessageStatus')
        }
        
    def handle_opt_out(self, phone_number: str) -> None:
        """Handle user opt-out request."""
        # Add phone number to Twilio opt-out list if needed
        pass
        
    def handle_opt_in(self, phone_number: str) -> None:
        """Handle user opt-in request."""
        # Remove phone number from Twilio opt-out list if needed
        pass
