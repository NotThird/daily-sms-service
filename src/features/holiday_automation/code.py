"""
Holiday Automation Service
Automated holiday message scheduling and generation with personalization

Dependencies:
- user_management
- message_generation  
- scheduler
- sms
- rate_limiting

Author: AI Assistant
Created: 2024-01-20
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import logging
import json
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy.orm import Session
from src.models import Recipient, UserConfig, ScheduledMessage
from src.features.rate_limiting.code import RateLimiter
from src.features.sms.code import SMSService
from src.features.message_generation.core import MessageGenerator
from src.scheduler import MessageScheduler

logger = logging.getLogger(__name__)

@dataclass
class HolidayConfig:
    """Configuration for a holiday message."""
    name: str
    date: str  # ISO format date string
    template: str
    personalization_fields: List[str]

class HolidayAutomationService:
    """Service for automated holiday message scheduling and delivery."""
    
    # Default holiday configurations
    DEFAULT_HOLIDAYS = [
        HolidayConfig(
            name="New Year's Day",
            date="2024-01-01",
            template=(
                "Dear {name},\n\n"
                "As we welcome {year}, I hope this new chapter brings you joy, "
                "success, and countless opportunities. May your {interests} "
                "flourish in the coming year!\n\n"
                "Happy New Year! 🎉"
            ),
            personalization_fields=["name", "interests"]
        ),
        # Add more holidays as needed
    ]
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.rate_limiter = RateLimiter()
        self.sms_service = SMSService()
        self.message_generator = MessageGenerator()
        self.scheduler = MessageScheduler(
            db_session=db_session,
            message_generator=self.message_generator,
            sms_service=self.sms_service,
            user_config_service=None  # Will be injected
        )
        
    @lru_cache(maxsize=100)
    def get_holiday_config(self, holiday_name: str) -> Optional[HolidayConfig]:
        """Get holiday configuration with caching for performance."""
        for holiday in self.DEFAULT_HOLIDAYS:
            if holiday.name == holiday_name:
                return holiday
        return None
        
    def schedule_holiday_messages(self, holiday_name: str) -> Dict[str, int]:
        """Schedule holiday messages for all active recipients."""
        holiday = self.get_holiday_config(holiday_name)
        if not holiday:
            raise ValueError(f"Unknown holiday: {holiday_name}")
            
        current_time = datetime.utcnow()
        holiday_date = datetime.fromisoformat(holiday.date)
        
        # Schedule messages for active recipients
        recipients = (
            self.db.query(Recipient, UserConfig)
            .join(
                UserConfig,
                Recipient.id == UserConfig.recipient_id,
                isouter=True
            )
            .filter(Recipient.is_active == True)
            .all()
        )
        
        scheduled_count = 0
        failed_count = 0
        
        for recipient, config in recipients:
            try:
                # Generate personalized message
                message = self._generate_holiday_message(
                    holiday=holiday,
                    recipient=recipient,
                    config=config
                )
                
                # Create scheduled message
                scheduled_msg = ScheduledMessage(
                    recipient_id=recipient.id,
                    scheduled_time=holiday_date,
                    status='pending',
                    content=message,
                    retry_count=0
                )
                
                self.db.add(scheduled_msg)
                scheduled_count += 1
                
            except Exception as e:
                logger.error(f"Failed to schedule holiday message for recipient {recipient.id}: {str(e)}")
                failed_count += 1
                
        self.db.commit()
        
        return {
            "scheduled": scheduled_count,
            "failed": failed_count,
            "total": len(recipients)
        }
        
    def _generate_holiday_message(
        self,
        holiday: HolidayConfig,
        recipient: Recipient,
        config: Optional[UserConfig]
    ) -> str:
        """Generate personalized holiday message with sanitized inputs."""
        # Safely extract user preferences
        preferences = {}
        if config and config.preferences:
            try:
                preferences = json.loads(config.preferences)
            except json.JSONDecodeError:
                logger.warning(f"Invalid preferences JSON for recipient {recipient.id}")
        
        # Build template variables with sanitized inputs
        template_vars = {
            "name": self._sanitize_input(config.name if config else "friend"),
            "year": str(datetime.utcnow().year),
            "interests": self._sanitize_input(
                preferences.get("interests", "personal goals")
            )
        }
        
        return holiday.template.format(**template_vars)
        
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input to prevent template injection."""
        if not text:
            return ""
        return ''.join(c for c in text if c.isalnum() or c.isspace() or c in '.,!?')
