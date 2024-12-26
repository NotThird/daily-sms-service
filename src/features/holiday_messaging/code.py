"""
---
title: Holiday Message Service
description: Sends positive holiday messages to all active users
authors: AI Assistant
date_created: 2024-01-20
dependencies:
  - user_management
  - message_generation
  - sms
  - rate_limiting
---
"""

from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy.orm import Session
from src.models import Recipient, UserConfig
from src.features.rate_limiting.code import RateLimiter
from src.features.sms.code import SMSService
from src.features.message_generation.core import MessageGenerator

logger = logging.getLogger(__name__)

class HolidayMessageService:
    """Service for sending holiday messages to all active users."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rate_limiter = RateLimiter()
        self.sms_service = SMSService()
        self.message_generator = MessageGenerator()
        
    def get_active_recipients(self) -> List[tuple]:
        """Retrieve all active recipients with their configs."""
        return (
            self.db.query(Recipient, UserConfig)
            .join(
                UserConfig,
                Recipient.id == UserConfig.recipient_id,
                isouter=True
            )
            .filter(Recipient.is_active == True)
            .all()
        )
    
    def generate_holiday_message(self, user_name: str) -> str:
        """Generate a personalized holiday message."""
        template = (
            "Dear {name}, 🎄✨\n\n"
            "Wishing you a Christmas filled with joy, warmth, and positivity! "
            "May this festive season bring you countless moments of happiness "
            "and beautiful memories to cherish.\n\n"
            "Happy Holidays! 🎁"
        )
        
        # Sanitize input to prevent injection
        safe_name = ''.join(c for c in user_name if c.isalnum() or c.isspace())
        return template.format(name=safe_name)
    
    async def send_bulk_messages(self, batch_size: int = 50) -> dict:
        """
        Send holiday messages to all active recipients with rate limiting and batching.
        
        Args:
            batch_size: Number of messages to send in each batch
            
        Returns:
            dict: Summary of sending operation
        """
        recipients = self.get_active_recipients()
        total_recipients = len(recipients)
        sent_count = 0
        failed_count = 0
        
        # Process recipients in batches for better performance
        for i in range(0, total_recipients, batch_size):
            batch = recipients[i:i + batch_size]
            
            # Check rate limit for batch
            if not self.rate_limiter.check_rate_limit("holiday_message", len(batch)):
                logger.warning("Rate limit reached, pausing message sending")
                break
                
            for recipient, config in batch:
                try:
                    # Use name from config if available, otherwise use "friend"
                    name = config.name if config and config.name else "friend"
                    message = self.generate_holiday_message(name)
                    await self.sms_service.send_message(
                        recipient=recipient.phone_number,
                        content=message
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send message to {recipient.phone_number}: {str(e)}")
                    failed_count += 1
                    
        return {
            "total_recipients": total_recipients,
            "messages_sent": sent_count,
            "messages_failed": failed_count,
            "timestamp": datetime.utcnow().isoformat()
        }
