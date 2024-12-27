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
        # Validate individual credentials
        if not account_sid:
            raise ValueError("TWILIO_ACCOUNT_SID is required")
        if not auth_token:
            raise ValueError("TWILIO_AUTH_TOKEN is required")
        if not from_number:
            raise ValueError("TWILIO_FROM_NUMBER is required")
            
        try:
            # Validate phone number before creating client
            self.from_number = self._sanitize_phone(from_number)
            
            # Initialize Twilio client
            self.client = Client(account_sid, auth_token)
            
            # Verify credentials by making a test API call
            account = self.client.api.accounts(account_sid).fetch()
            if not account or account.status != "active":
                raise ValueError(f"Twilio account not active: {account.status if account else 'unknown'}")
                
            print(f"SMS Service initialized successfully with account: {account_sid[:6]}...")
            print(f"Using phone number: {self.from_number}")
            
        except Exception as e:
            print(f"Failed to initialize SMS Service: {str(e)}")
            raise
        
    @staticmethod
    def _sanitize_phone(phone: str) -> str:
        """
        Sanitize phone numbers to prevent injection.
        Ensures proper E.164 format with country code.
        """
        # If phone number already has + prefix, use it as is
        if phone.startswith('+'):
            print(f"Using phone number as-is: {phone}")
            return phone
            
        # Otherwise, clean and format
        clean = re.sub(r'\D', '', phone)
        if len(clean) == 10:
            formatted = f"+1{clean}"  # Add US country code
        elif len(clean) == 11 and clean.startswith('1'):
            formatted = f"+{clean}"  # Number already has country code
        else:
            raise ValueError(f"Invalid phone number format: {phone}")
            
        print(f"Sanitized phone number: {formatted}")
        return formatted
        
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
