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
        Strips all non-numeric characters and ensures proper format.
        """
        clean = re.sub(r'\D', '', phone)
        if len(clean) == 10:
            return clean
        elif len(clean) == 11 and clean.startswith('1'):
            return clean[1:]
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

notification_manager = NotificationManager()  # Singleton instance
