#!/usr/bin/env python3
"""Script to send holiday messages to all active users."""

import asyncio
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.features.holiday_messaging.code import HolidayMessageService
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Send holiday messages to all active users."""
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")

    # Set up database connection
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Initialize holiday message service
        service = HolidayMessageService(session)
        
        # Send messages
        logger.info("Starting to send holiday messages...")
        result = await service.send_bulk_messages()
        
        # Log results
        logger.info("Holiday message sending completed:")
        logger.info(f"Total users: {result['total_users']}")
        logger.info(f"Messages sent: {result['messages_sent']}")
        logger.info(f"Messages failed: {result['messages_failed']}")
        
    except Exception as e:
        logger.error(f"Error sending holiday messages: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    asyncio.run(main())
