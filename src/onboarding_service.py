from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from .models import Recipient, UserConfig
import json
import logging
import pytz
from datetime import datetime

logger = logging.getLogger(__name__)

class OnboardingService:
    """Manages the user onboarding flow via SMS."""
    
    # Define onboarding steps and their questions
    ONBOARDING_STEPS = {
        'name': "Hi! Welcome to our service. What's your name?",
        'occupation': "What's your occupation or profession? This helps us personalize messages.",
        'interests': "What are your main interests or hobbies? (separate multiple with commas)",
        'style': "What communication style do you prefer? Reply with:\nC for Casual\nP for Professional",
        'timing': "Would you like to receive messages in the morning (M) or evening (E)?",
        'confirmation': "Great! You're all set up. Reply Y to confirm and start receiving messages."
    }

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def start_onboarding(self, recipient_id: int) -> str:
        """
        Start the onboarding process for a new user.
        Returns the first onboarding question.
        """
        try:
            # Create or get user config
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            if not config:
                config = UserConfig(
                    recipient_id=recipient_id,
                    preferences={'onboarding_step': 'name'},
                    personal_info={}
                )
                self.db_session.add(config)
            else:
                # Reset the config for a fresh start
                config.preferences = {'onboarding_step': 'name'}
                config.personal_info = {}
                config.name = None

            # Set timezone to Central time
            recipient = self.db_session.query(Recipient).filter_by(id=recipient_id).first()
            recipient.timezone = 'America/Chicago'
            
            self.db_session.commit()
            logger.info(f"Starting onboarding for user {recipient_id}, preferences: {config.preferences}")
            return self.ONBOARDING_STEPS['name']

        except Exception as e:
            logger.error(f"Error starting onboarding: {str(e)}")
            raise

    def process_response(self, recipient_id: int, message: str) -> Tuple[str, bool]:
        """
        Process a user's response during onboarding.
        Returns (next_message, is_complete).
        """
        try:
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            recipient = self.db_session.query(Recipient).filter_by(id=recipient_id).first()
            
            if not config or not recipient:
                logger.info(f"No config found for user {recipient_id}, starting onboarding")
                return self.start_onboarding(recipient_id), False

            current_step = config.preferences.get('onboarding_step')
            logger.info(f"Processing response for user {recipient_id}, current step: {current_step}, message: {message}")
            
            if not current_step:
                logger.info(f"No current step for user {recipient_id}, starting onboarding")
                return self.start_onboarding(recipient_id), False

            # Process the response based on current step
            next_step = None
            
            if current_step == 'name':
                config.name = message
                config.personal_info['name'] = message
                next_step = 'occupation'
                
            elif current_step == 'occupation':
                config.personal_info['occupation'] = message
                next_step = 'interests'
                
            elif current_step == 'interests':
                config.personal_info['interests'] = [interest.strip() for interest in message.split(',')]
                next_step = 'style'
                
            elif current_step == 'style':
                if message.upper() not in ['C', 'P']:
                    return "Please reply with C for Casual or P for Professional.", False
                config.preferences['communication_style'] = 'casual' if message.upper() == 'C' else 'professional'
                next_step = 'timing'
                
            elif current_step == 'timing':
                if message.upper() not in ['M', 'E']:
                    return "Please reply with M for morning or E for evening.", False
                config.preferences['message_time'] = 'morning' if message.upper() == 'M' else 'evening'
                next_step = 'confirmation'
                
            elif current_step == 'confirmation':
                if message.upper() != 'Y':
                    return "Please reply Y to confirm your registration.", False
                config.preferences['onboarding_complete'] = True
                config.preferences.pop('onboarding_step', None)
                self.db_session.commit()
                return f"Welcome {config.name}! You're all set to receive daily messages. Text STOP at any time to unsubscribe.", True

            # Update step and commit
            if next_step:
                config.preferences['onboarding_step'] = next_step
                self.db_session.commit()
                return self.ONBOARDING_STEPS[next_step], False

            # Should never reach here since all steps have a next_step or return earlier
            raise ValueError(f"Invalid onboarding step: {current_step}")

        except Exception as e:
            logger.error(f"Error processing onboarding response: {str(e)}")
            raise

    def is_onboarding_complete(self, recipient_id: int) -> bool:
        """Check if a user has completed onboarding."""
        try:
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            is_complete = bool(config and config.preferences.get('onboarding_complete'))
            logger.info(f"Checking if onboarding complete for user {recipient_id}: {is_complete}")
            return is_complete
        except Exception as e:
            logger.error(f"Error checking onboarding status: {str(e)}")
            return False

    def is_in_onboarding(self, recipient_id: int) -> bool:
        """Check if a user is currently in the onboarding process."""
        try:
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            in_onboarding = bool(config and config.preferences.get('onboarding_step'))
            logger.info(f"Checking if user {recipient_id} is in onboarding: {in_onboarding}, preferences: {config.preferences if config else None}")
            return in_onboarding
        except Exception as e:
            logger.error(f"Error checking if in onboarding: {str(e)}")
            return False
