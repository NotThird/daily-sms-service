import random
from datetime import datetime, timedelta
import pytz
import logging
from typing import Optional, List, Dict
from sqlalchemy.orm import Session

from .models import Recipient, ScheduledMessage, MessageLog, UserConfig
from .message_generator import MessageGenerator
from .sms_service import SMSService
from .user_config_service import UserConfigService

logger = logging.getLogger(__name__)

class MessageScheduler:
    """Handles scheduling and sending of daily messages."""
    
    def __init__(
        self,
        db_session: Session,
        message_generator: MessageGenerator,
        sms_service: SMSService,
        user_config_service: UserConfigService
    ):
        """Initialize scheduler with required services."""
        self.db = db_session
        self.message_generator = message_generator
        self.sms_service = sms_service
        self.user_config_service = user_config_service

    def schedule_daily_messages(self) -> Dict[str, int]:
        """
        Schedule messages for all active recipients.
        Returns count of scheduled and failed attempts.
        """
        try:
            # Get all active recipients
            recipients = self.db.query(Recipient).filter_by(is_active=True).all()
            
            scheduled_count = 0
            failed_count = 0
            skipped_count = 0
            
            for recipient in recipients:
                try:
                    # Check if recipient already has a pending message for today
                    today_start = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
                    tomorrow_start = today_start + timedelta(days=1)
                    
                    existing_message = self.db.query(ScheduledMessage).filter(
                        ScheduledMessage.recipient_id == recipient.id,
                        ScheduledMessage.status == 'pending',
                        ScheduledMessage.scheduled_time >= today_start,
                        ScheduledMessage.scheduled_time < tomorrow_start
                    ).first()
                    
                    if existing_message:
                        logger.info(f"Skipping recipient {recipient.id} - already has pending message for today")
                        skipped_count += 1
                        continue
                    
                    # Generate time based on preferences or random time
                    scheduled_time = self._generate_send_time(recipient.timezone, recipient.id)
                    
                    # Generate message content now
                    recent_messages = self._get_recent_messages(recipient.id)
                    message = self.message_generator.generate_message({
                        'previous_messages': recent_messages
                    })
                    
                    # Create scheduled message with content
                    scheduled_msg = ScheduledMessage(
                        recipient_id=recipient.id,
                        scheduled_time=scheduled_time,
                        status='pending',
                        content=message
                    )
                    
                    self.db.add(scheduled_msg)
                    scheduled_count += 1
                    logger.info(f"Scheduled message for recipient {recipient.id} at {scheduled_time}")
                    
                except Exception as e:
                    logger.error(f"Failed to schedule message for recipient {recipient.id}: {str(e)}")
                    failed_count += 1
            
            self.db.commit()
            
            return {
                'scheduled': scheduled_count,
                'failed': failed_count,
                'skipped': skipped_count,
                'total': len(recipients)
            }
            
        except Exception as e:
            logger.error(f"Error in schedule_daily_messages: {str(e)}")
            raise

    def process_scheduled_messages(self) -> Dict[str, int]:
        """
        Process all scheduled messages that are due.
        Returns count of sent and failed messages.
        """
        try:
            # Get all pending messages scheduled for now or earlier
            current_time = datetime.utcnow()
            due_messages = self.db.query(ScheduledMessage).filter(
                ScheduledMessage.status == 'pending',
                ScheduledMessage.scheduled_time <= current_time,
                ScheduledMessage.content != None  # Only process messages with content
            ).all()
            
            sent_count = 0
            failed_count = 0
            
            for scheduled_msg in due_messages:
                try:
                    # Get recipient
                    recipient = self.db.query(Recipient).get(scheduled_msg.recipient_id)
                    
                    if not recipient or not recipient.is_active:
                        scheduled_msg.status = 'cancelled'
                        continue
                    
                    # Send the pre-generated message
                    result = self.sms_service.send_message(
                        recipient.phone_number,
                        scheduled_msg.content
                    )
                    
                    if result['status'] == 'success':
                        # Log successful send
                        message_log = MessageLog(
                            recipient_id=recipient.id,
                            message_type='outbound',
                            content=scheduled_msg.content,
                            status='sent',
                            twilio_sid=result['message_sid']
                        )
                        self.db.add(message_log)
                        
                        scheduled_msg.status = 'sent'
                        scheduled_msg.sent_at = current_time
                        sent_count += 1
                        logger.info(f"Successfully sent message {scheduled_msg.id} to recipient {recipient.id}")
                        
                    else:
                        # Log failed send
                        scheduled_msg.status = 'failed'
                        scheduled_msg.error_message = result.get('error')
                        failed_count += 1
                        logger.error(f"Failed to send message {scheduled_msg.id}: {result.get('error')}")
                    
                except Exception as e:
                    logger.error(f"Error processing scheduled message {scheduled_msg.id}: {str(e)}")
                    scheduled_msg.status = 'failed'
                    scheduled_msg.error_message = str(e)
                    failed_count += 1
            
            self.db.commit()
            
            return {
                'sent': sent_count,
                'failed': failed_count,
                'total': len(due_messages)
            }
            
        except Exception as e:
            logger.error(f"Error in process_scheduled_messages: {str(e)}")
            raise

    def _generate_send_time(self, timezone_str: str, recipient_id: int) -> datetime:
        """Generate send time based on user preferences or random time between 12 PM and 5 PM."""
        # Get current time in recipient's timezone
        tz = pytz.timezone(timezone_str)
        current_time = datetime.now(tz)
        
        # Check for preferred time in user config
        config = self.user_config_service.get_config(recipient_id)
        if config and config.preferences.get('preferred_time'):
            try:
                # Expected format "HH:MM" in 24-hour time
                preferred_time = config.preferences['preferred_time']
                hour, minute = map(int, preferred_time.split(':'))
                
                # Create naive datetime for today with preferred time
                naive_time = datetime.combine(
                    current_time.date(),
                    datetime.min.time().replace(hour=hour, minute=minute)
                )
                
                # Convert naive time to timezone-aware time
                local_time = tz.localize(naive_time)
                
                # If preferred time has passed for today, schedule for tomorrow
                if local_time <= current_time:
                    local_time = local_time + timedelta(days=1)
                
                # Convert to UTC
                return local_time.astimezone(pytz.UTC)
            except (ValueError, KeyError):
                logger.warning(f"Invalid preferred_time format for recipient {recipient_id}, falling back to random time")
        
        # Fall back to random time if no valid preferred time
        hour = random.randint(12, 16)  # 12 PM to 4 PM (to allow for minutes)
        minute = random.randint(0, 59)
        
        # Create naive datetime and convert to timezone-aware time
        naive_time = datetime.combine(
            current_time.date(),
            datetime.min.time().replace(hour=hour, minute=minute)
        )
        local_time = tz.localize(naive_time)
        
        # Convert to UTC
        return local_time.astimezone(pytz.UTC)

    def _get_recent_messages(self, recipient_id: int, days: int = 7) -> List[str]:
        """Get recent messages sent to recipient to avoid repetition."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        recent_logs = self.db.query(MessageLog).filter(
            MessageLog.recipient_id == recipient_id,
            MessageLog.message_type == 'outbound',
            MessageLog.sent_at >= cutoff_date
        ).all()
        
        return [log.content for log in recent_logs]

    def cleanup_old_records(self, days: int = 30) -> Dict[str, int]:
        """Clean up old scheduled messages and logs."""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Delete old scheduled messages
            scheduled_deleted = self.db.query(ScheduledMessage).filter(
                ScheduledMessage.created_at < cutoff_date
            ).delete()
            
            # Delete old message logs
            logs_deleted = self.db.query(MessageLog).filter(
                MessageLog.sent_at < cutoff_date
            ).delete()
            
            self.db.commit()
            
            return {
                'scheduled_messages_deleted': scheduled_deleted,
                'message_logs_deleted': logs_deleted
            }
            
        except Exception as e:
            logger.error(f"Error in cleanup_old_records: {str(e)}")
            self.db.rollback()
            raise
