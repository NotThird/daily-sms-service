"""
Message Scheduler
---------------
Description: Handles scheduling and delivery of daily personalized messages
Authors: AI Assistant
Date Created: 2024-01-09
Dependencies:
  - core
  - message_generation
  - notification_system
"""

from typing import Dict
from datetime import datetime, timedelta
import pytz
from sqlalchemy.orm import Session
from src.features.core.code import ScheduledMessage, Recipient
from src.features.message_generation.code import MessageGenerator
from src.features.notification_system.code import SMSService
from src.features.user_management.code import UserConfigService

class MessageScheduler:
    """Handles scheduling and processing of daily messages."""
    
    def __init__(self, db_session: Session, message_generator: MessageGenerator, 
                 sms_service: SMSService, user_config_service: UserConfigService):
        """Initialize scheduler with required services."""
        self.db = db_session
        self.message_generator = message_generator
        self.sms_service = sms_service
        self.user_config_service = user_config_service
        
    def schedule_daily_messages(self) -> Dict[str, int]:
        """Schedule messages for all active recipients."""
        try:
            # Get all active recipients
            recipients = self.db.query(Recipient).filter_by(is_active=True).all()
            
            scheduled_count = 0
            failed_count = 0
            
            for recipient in recipients:
                try:
                    # Get user context for personalization
                    context = self.user_config_service.get_gpt_prompt_context(recipient.id)
                    
                    # Generate message content
                    message_content = self.message_generator.generate_message(context)
                    
                    # Calculate scheduled time based on recipient's timezone
                    recipient_tz = pytz.timezone(recipient.timezone)
                    now = datetime.now(recipient_tz)
                    
                    # Get user's preferred message time
                    preferred_time = context.get('preferences', {}).get('message_time', '09:00')
                    hour, minute = map(int, preferred_time.split(':'))
                    
                    # Schedule for next occurrence of preferred time in recipient's timezone
                    scheduled_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    if now.hour > hour or (now.hour == hour and now.minute >= minute):
                        scheduled_time += timedelta(days=1)
                    
                    # Create scheduled message
                    scheduled_msg = ScheduledMessage(
                        recipient_id=recipient.id,
                        scheduled_time=scheduled_time,
                        content=message_content,
                        status='pending'
                    )
                    
                    self.db.add(scheduled_msg)
                    scheduled_count += 1
                    
                except Exception as e:
                    print(f"Failed to schedule message for recipient {recipient.id}: {str(e)}")
                    failed_count += 1
                    
            self.db.commit()
            return {
                'scheduled': scheduled_count,
                'failed': failed_count,
                'total': len(recipients)
            }
            
        except Exception as e:
            print(f"Error in schedule_daily_messages: {str(e)}")
            return {
                'scheduled': 0,
                'failed': 0,
                'total': 0
            }
            
    def process_scheduled_messages(self) -> Dict[str, int]:
        """Process all pending scheduled messages that are due."""
        try:
            # Get pending messages that are due
            current_time = datetime.now(pytz.UTC)
            pending_messages = self.db.query(ScheduledMessage).filter(
                ScheduledMessage.status == 'pending',
                ScheduledMessage.scheduled_time <= current_time
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for message in pending_messages:
                try:
                    # Get recipient
                    recipient = self.db.query(Recipient).get(message.recipient_id)
                    if not recipient or not recipient.is_active:
                        message.status = 'cancelled'
                        continue
                        
                    # Send message
                    result = self.sms_service.send_message(
                        recipient.phone_number,
                        message.content
                    )
                    
                    # Update message status
                    message.sent_at = current_time
                    if result.get('delivery_status') == 'failed':
                        message.status = 'failed'
                        message.error_message = result.get('error_message')
                        failed_count += 1
                    else:
                        message.status = 'sent'
                        sent_count += 1
                        
                except Exception as e:
                    message.status = 'failed'
                    message.error_message = str(e)
                    failed_count += 1
                    
            self.db.commit()
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total': len(pending_messages)
            }
            
        except Exception as e:
            print(f"Error in process_scheduled_messages: {str(e)}")
            return {
                'sent': 0,
                'failed': 0,
                'total': 0
            }
            
    def cleanup_old_records(self) -> Dict[str, int]:
        """Clean up old scheduled message records."""
        try:
            # Delete messages older than 30 days
            cutoff_date = datetime.now(pytz.UTC) - timedelta(days=30)
            deleted = self.db.query(ScheduledMessage).filter(
                ScheduledMessage.scheduled_time < cutoff_date
            ).delete()
            
            self.db.commit()
            return {
                'deleted': deleted
            }
            
        except Exception as e:
            print(f"Error in cleanup_old_records: {str(e)}")
            return {
                'deleted': 0
            }
