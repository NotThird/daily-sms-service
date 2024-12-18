#!/usr/bin/env python3
import click
import os
import logging
from logging.config import dictConfig
from datetime import datetime
import json

from .models import get_db_session
from .message_generator import MessageGenerator
from .sms_service import SMSService
from .scheduler import MessageScheduler

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default',
            'level': 'INFO'
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'scheduler.log',
            'formatter': 'default',
            'level': 'INFO'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
})

logger = logging.getLogger(__name__)

def init_services():
    """Initialize all required services."""
    try:
        # Initialize database session
        db_session = get_db_session(os.getenv('DATABASE_URL'))
        
        # Initialize message generator
        message_generator = MessageGenerator(os.getenv('OPENAI_API_KEY'))
        
        # Initialize SMS service
        sms_service = SMSService(
            os.getenv('TWILIO_ACCOUNT_SID'),
            os.getenv('TWILIO_AUTH_TOKEN'),
            os.getenv('TWILIO_FROM_NUMBER')
        )
        
        # Initialize scheduler
        scheduler = MessageScheduler(
            db_session,
            message_generator,
            sms_service
        )
        
        return scheduler, db_session
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise

@click.group()
def cli():
    """Daily Positivity SMS Service CLI"""
    pass

@cli.command()
def schedule_messages():
    """Schedule daily messages for all active recipients."""
    try:
        scheduler, db_session = init_services()
        
        logger.info("Starting daily message scheduling...")
        result = scheduler.schedule_daily_messages()
        
        logger.info(
            f"Scheduled {result['scheduled']} messages "
            f"({result['failed']} failed) "
            f"out of {result['total']} recipients"
        )
        
        # Write results to status file for monitoring
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'schedule_messages',
            'result': result
        }
        
        with open('scheduler_status.json', 'w') as f:
            json.dump(status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in schedule_messages command: {str(e)}")
        raise
    finally:
        db_session.close()

@cli.command()
def process_messages():
    """Process and send scheduled messages that are due."""
    try:
        scheduler, db_session = init_services()
        
        logger.info("Processing scheduled messages...")
        result = scheduler.process_scheduled_messages()
        
        logger.info(
            f"Processed {result['total']} messages: "
            f"{result['sent']} sent, {result['failed']} failed"
        )
        
        # Write results to status file for monitoring
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'process_messages',
            'result': result
        }
        
        with open('scheduler_status.json', 'w') as f:
            json.dump(status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in process_messages command: {str(e)}")
        raise
    finally:
        db_session.close()

@cli.command()
@click.option('--days', default=30, help='Number of days of records to keep')
def cleanup():
    """Clean up old records from the database."""
    try:
        scheduler, db_session = init_services()
        
        logger.info(f"Cleaning up records older than {days} days...")
        result = scheduler.cleanup_old_records(days)
        
        logger.info(
            f"Cleaned up {result['scheduled_messages_deleted']} scheduled messages "
            f"and {result['message_logs_deleted']} message logs"
        )
        
        # Write results to status file for monitoring
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': 'cleanup',
            'result': result
        }
        
        with open('scheduler_status.json', 'w') as f:
            json.dump(status, f, indent=2)
            
    except Exception as e:
        logger.error(f"Error in cleanup command: {str(e)}")
        raise
    finally:
        db_session.close()

@cli.command()
@click.argument('phone_number')
@click.argument('message')
def test_message(phone_number, message):
    """Send a test message to a specific phone number."""
    try:
        scheduler, db_session = init_services()
        
        logger.info(f"Sending test message to {phone_number}...")
        
        # Validate phone number
        if not scheduler.sms_service.validate_phone_number(phone_number):
            logger.error("Invalid phone number")
            return
        
        # Send message
        result = scheduler.sms_service.send_message(phone_number, message)
        
        if result['status'] == 'success':
            logger.info(f"Test message sent successfully. SID: {result['message_sid']}")
        else:
            logger.error(f"Failed to send test message: {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in test_message command: {str(e)}")
        raise
    finally:
        db_session.close()

if __name__ == '__main__':
    cli()
