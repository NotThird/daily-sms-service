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
            if current_step == 'name':
                config.name = message
                config.personal_info['name'] = message  # Store in both places for consistency
                config.preferences['onboarding_step'] = 'occupation'
                next_message = self.ONBOARDING_STEPS['occupation']
                logger.info(f"User {recipient_id} provided name: {message}, moving to occupation step")
                
            elif current_step == 'occupation':
                config.personal_info['occupation'] = message
                config.preferences['onboarding_step'] = 'interests'
                next_message = self.ONBOARDING_STEPS['interests']
                logger.info(f"User {recipient_id} provided occupation: {message}, moving to interests step")

            elif current_step == 'interests':
                interests = [interest.strip() for interest in message.split(',')]
                config.personal_info['interests'] = interests
                config.preferences['onboarding_step'] = 'style'
                next_message = self.ONBOARDING_STEPS['style']
                logger.info(f"User {recipient_id} provided interests: {interests}, moving to style step")

            elif current_step == 'style':
                if message.upper() not in ['C', 'P']:
                    logger.info(f"User {recipient_id} provided invalid style: {message}")
                    return "Please reply with C for Casual or P for Professional.", False
                config.preferences['communication_style'] = 'casual' if message.upper() == 'C' else 'professional'
                config.preferences['onboarding_step'] = 'timing'
                next_message = self.ONBOARDING_STEPS['timing']
                logger.info(f"User {recipient_id} provided style preference: {message}, moving to timing step")

            elif current_step == 'timing':
                if message.upper() not in ['M', 'E']:
                    logger.info(f"User {recipient_id} provided invalid timing: {message}")
                    return "Please reply with M for morning or E for evening.", False
                config.preferences['message_time'] = 'morning' if message.upper() == 'M' else 'evening'
                config.preferences['onboarding_step'] = 'confirmation'
                next_message = self.ONBOARDING_STEPS['confirmation']
                logger.info(f"User {recipient_id} provided timing preference: {message}, moving to confirmation step")
                
            elif current_step == 'confirmation':
                if message.upper() != 'Y':
                    logger.info(f"User {recipient_id} provided invalid confirmation: {message}")
                    return "Please reply Y to confirm your registration.", False
                # Complete onboarding
                config.preferences['onboarding_complete'] = True
                config.preferences.pop('onboarding_step', None)
                next_message = f"Welcome {config.name}! You're all set to receive daily messages. Text STOP at any time to unsubscribe."
                logger.info(f"User {recipient_id} completed onboarding, final preferences: {config.preferences}")
                self.db_session.commit()
                return next_message, True

            # Log the state before committing
            logger.info(f"Updating user {recipient_id} config - preferences: {config.preferences}, personal_info: {config.personal_info}")
            self.db_session.commit()
            return next_message, False

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
