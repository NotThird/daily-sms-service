from typing import Dict, Optional, Tuple
from sqlalchemy.orm import Session
from .models import Recipient, UserConfig
import json
import logging

logger = logging.getLogger(__name__)

class OnboardingService:
    """Manages the user onboarding flow via SMS."""
    
    # Define onboarding steps and their questions
    ONBOARDING_STEPS = {
        'name': "Hi! Welcome to our service. What's your name?",
        'timezone': "What city are you in? We'll use this to set your timezone.",
        'preferences': "Would you like to receive messages in the morning (M) or evening (E)?",
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
                self.db_session.commit()
            else:
                config.preferences['onboarding_step'] = 'name'
                self.db_session.commit()

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
            if not config:
                return self.start_onboarding(recipient_id), False

            current_step = config.preferences.get('onboarding_step')
            if not current_step:
                return self.start_onboarding(recipient_id), False

            # Process the response based on current step
            if current_step == 'name':
                config.name = message
                config.preferences['onboarding_step'] = 'timezone'
                next_message = self.ONBOARDING_STEPS['timezone']
                
            elif current_step == 'timezone':
                config.personal_info['city'] = message
                config.preferences['onboarding_step'] = 'preferences'
                next_message = self.ONBOARDING_STEPS['preferences']
                
            elif current_step == 'preferences':
                if message.upper() not in ['M', 'E']:
                    return "Please reply with M for morning or E for evening.", False
                config.preferences['message_time'] = 'morning' if message.upper() == 'M' else 'evening'
                config.preferences['onboarding_step'] = 'confirmation'
                next_message = self.ONBOARDING_STEPS['confirmation']
                
            elif current_step == 'confirmation':
                if message.upper() != 'Y':
                    return "Please reply Y to confirm your registration.", False
                # Complete onboarding
                config.preferences['onboarding_complete'] = True
                config.preferences.pop('onboarding_step', None)
                next_message = f"Welcome {config.name}! You're all set to receive daily messages. Text STOP at any time to unsubscribe."
                self.db_session.commit()
                return next_message, True

            self.db_session.commit()
            return next_message, False

        except Exception as e:
            logger.error(f"Error processing onboarding response: {str(e)}")
            raise

    def is_onboarding_complete(self, recipient_id: int) -> bool:
        """Check if a user has completed onboarding."""
        try:
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            return bool(config and config.preferences.get('onboarding_complete'))
        except Exception as e:
            logger.error(f"Error checking onboarding status: {str(e)}")
            return False

    def is_in_onboarding(self, recipient_id: int) -> bool:
        """Check if a user is currently in the onboarding process."""
        try:
            config = self.db_session.query(UserConfig).filter_by(recipient_id=recipient_id).first()
            return bool(config and config.preferences.get('onboarding_step'))
        except Exception as e:
            logger.error(f"Error checking if in onboarding: {str(e)}")
            return False
