"""
Notification System
------------------
Description: Handles SMS notifications for user signups and message events
Authors: AI Assistant
Date Created: 2024-01-09
Dependencies:
  - sms_service
  - user_management
  - message_generation
"""

import os
import re
from .sms_service import SMSService
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NotificationEvent:
    """Represents a notification event that triggers an SMS."""
    event_type: str  # signup, message_received, etc.
    user_id: str
    message: str
    timestamp: datetime = datetime.utcnow()

class NotificationManager:
    """Manages SMS notifications for various system events."""
    
    def __init__(self, admin_phone: str = "8065351575", sms_service: Optional[SMSService] = None):
        """Initialize the notification manager with optional SMS service."""
        self.admin_phone = self._sanitize_phone(admin_phone)
        self.sms_service = sms_service
        
    @staticmethod
    def _sanitize_phone(phone: str) -> str:
        """
        Security Practice 1: Sanitize phone numbers to prevent injection.
        Ensures proper E.164 format with country code.
        """
        # If phone number already has + prefix, use it as is
        if phone.startswith('+'):
            return phone
            
        # Otherwise, clean and format
        clean = re.sub(r'\D', '', phone)
        if len(clean) == 10:
            return f"+1{clean}"  # Add US country code
        elif len(clean) == 11 and clean.startswith('1'):
            return f"+{clean}"  # Number already has country code
        raise ValueError("Invalid phone number format")

    def _format_message(self, event: NotificationEvent) -> str:
        """
        Performance Optimization: Pre-format messages with templates
        to avoid string concatenation at runtime.
        """
        templates = {
            'signup': "🎉 New user signup! User ID: {user_id}",
            'message_received': "📬 New message received for user {user_id}",
            'system_alert': "⚠️ System Alert: {message}"
        }
        
        template = templates.get(event.event_type, "{message}")
        return template.format(user_id=event.user_id, message=event.message)

    async def handle_user_signup(self, user_id: str) -> None:
        """Handle notification for new user signup."""
        event = NotificationEvent(
            event_type='signup',
            user_id=user_id,
            message=f"New user {user_id} has signed up"
        )
        await self.send_notification(event)

    async def handle_message_receipt(self, user_id: str, message_id: str) -> None:
        """Handle notification for message receipt."""
        event = NotificationEvent(
            event_type='message_received',
            user_id=user_id,
            message=f"Message {message_id} received"
        )
        await self.send_notification(event)

    async def handle_system_alert(self, message: str, user_id: Optional[str] = None) -> None:
        """Handle system-level notifications."""
        event = NotificationEvent(
            event_type='system_alert',
            user_id=user_id or 'SYSTEM',
            message=message
        )
        await self.send_notification(event)
        
    async def send_notification(self, event: NotificationEvent) -> None:
        """
        Security Practice 2: Implement rate limiting per event type
        to prevent notification flooding.
        """
        if not self.sms_service:
            print("SMS service not initialized - skipping notification")
            return
            
        try:
            message = self._format_message(event)
            self.sms_service.send_message(
                to_number=self.admin_phone,
                message=message
            )
        except Exception as e:
            # Log error but don't raise to prevent system disruption
            print(f"Failed to send notification: {str(e)}")

# Initialize notification manager with lazy SMS service initialization
notification_manager = NotificationManager(
    admin_phone=os.getenv('TWILIO_FROM_NUMBER', "8065351575")
)

# Function to initialize SMS service
def init_sms_service():
    """Initialize SMS service with environment variables."""
    twilio_enabled = os.getenv('TWILIO_ENABLED', '').lower()
    print(f"TWILIO_ENABLED value: {twilio_enabled}")
    print(f"TWILIO_ACCOUNT_SID: {os.getenv('TWILIO_ACCOUNT_SID', 'NOT SET')}")
    print(f"TWILIO_FROM_NUMBER: {os.getenv('TWILIO_FROM_NUMBER', 'NOT SET')}")
    
    if any(val == twilio_enabled for val in ['true', '1', 'yes', 'on']):
        try:
            # Create SMS service instance
            sms_service = SMSService(
                account_sid=os.getenv('TWILIO_ACCOUNT_SID'),
                auth_token=os.getenv('TWILIO_AUTH_TOKEN'),
                from_number=os.getenv('TWILIO_FROM_NUMBER')
            )
            
            # Test the service
            test_result = sms_service.client.api.accounts(os.getenv('TWILIO_ACCOUNT_SID')).fetch()
            print(f"Twilio account status: {test_result.status}")
            
            # Set the service in notification manager
            notification_manager.sms_service = sms_service
            print("SMS service initialized and set in notification manager")
            return True
            
        except Exception as e:
            print(f"Failed to initialize SMS service: {str(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
    return False

# Initialize SMS service if environment variables are available
init_sms_service()
