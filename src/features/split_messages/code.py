"""
Split Message Feature
--------------------
title: Split Message Feature
description: Handles splitting and scheduling secret messages between users
authors: Cline
date_created: 2024-01-20
dependencies:
  - scheduler.py
  - models.py
  - sms_service.py
"""

from datetime import datetime
import random
from typing import Tuple, Dict
from sqlalchemy.orm import Session
from ...models import Recipient, ScheduledMessage, MessageLog

class SplitMessageService:
    """Handles splitting and scheduling secret messages between users."""
    
    def __init__(self, db_session: Session):
        self.db = db_session

    def split_message(self, message: str) -> Tuple[str, str]:
        """
        Splits a message into two parts that only make sense when combined.
        Uses a simple alternating word pattern for demonstration.
        """
        words = message.split()
        part1_words = words[::2]  # Even indexed words
        part2_words = words[1::2]  # Odd indexed words
        
        # Add indices to help with reconstruction
        part1 = " ___ ".join(part1_words)
        part2 = " ___ ".join(part2_words)
        
        return part1, part2

    def schedule_split_message(
        self,
        message: str,
        recipient1_phone: str,
        recipient2_phone: str,
        scheduled_time: datetime
    ) -> Dict[str, str]:
        """
        Schedules a split message to be sent to two recipients at the specified time.
        """
        # Get recipients
        recipient1 = self.db.query(Recipient).filter_by(phone_number=recipient1_phone).first()
        recipient2 = self.db.query(Recipient).filter_by(phone_number=recipient2_phone).first()
        
        if not recipient1 or not recipient2:
            raise ValueError("Both recipients must exist in the system")
            
        # Split the message
        part1, part2 = self.split_message(message)
        
        # Create scheduled messages
        msg1 = ScheduledMessage(
            recipient_id=recipient1.id,
            scheduled_time=scheduled_time,
            status='pending',
            content=f"Part 1 of split message: {part1}"
        )
        
        msg2 = ScheduledMessage(
            recipient_id=recipient2.id,
            scheduled_time=scheduled_time,
            status='pending',
            content=f"Part 2 of split message: {part2}"
        )
        
        self.db.add(msg1)
        self.db.add(msg2)
        self.db.commit()
        
        return {
            'recipient1_message': part1,
            'recipient2_message': part2,
            'scheduled_time': scheduled_time.isoformat()
        }
