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
        'name': "Hi! 👋 I'm your personal positivity messenger. What should I call you?",
        'occupation': "Nice to meet you! What's your profession or work situation? (Examples: software engineer, student, retired, stay-at-home parent)",
        'interests': "What are your hobbies and interests outside of work? (Examples: reading, hiking, cooking, gaming)",
        'style': "Quick question: Do you prefer casual messages (like from a friend) or professional ones?\nJust reply with 1 for casual or 2 for professional.",
        'timing': "Last thing: When would you like to receive your daily messages?\nReply with 1 for morning or 2 for evening.",
        'confirmation': "Perfect! I'm ready to start sending you personalized daily messages. Reply OK to begin!"
    }

    def __init__(self, db_session: Session, message_generator=None):
        self.db_session = db_session
        self.message_generator = message_generator

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
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() if k != 'onboarding_step'}
                
                # Store name and move to next step
                config.name = message
                config.personal_info['name'] = message
                config.preferences = {
                    'onboarding_step': 'occupation',
                    **existing_prefs
                }
                self.db_session.commit()
                return self.ONBOARDING_STEPS['occupation'], False
                
            elif current_step == 'occupation':
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() if k != 'onboarding_step'}
                
                # Store occupation and move to next step
                config.personal_info['occupation'] = message
                config.preferences = {
                    'onboarding_step': 'interests',
                    **existing_prefs
                }
                self.db_session.commit()
                return self.ONBOARDING_STEPS['interests'], False
                
            elif current_step == 'interests':
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() if k != 'onboarding_step'}
                
                # Handle different formats of interests input
                if ',' in message:
                    interests = [interest.strip() for interest in message.split(',')]
                else:
                    interests = [interest.strip() for interest in message.split()]
                
                # Store interests and move to next step
                config.personal_info['interests'] = interests
                config.preferences = {
                    'onboarding_step': 'style',
                    **existing_prefs
                }
                self.db_session.commit()
                return self.ONBOARDING_STEPS['style'], False
                
            elif current_step == 'style':
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() if k != 'onboarding_step'}
                
                # Super simple style check - just look for "2", everything else is casual
                style_value = 'professional' if '2' in message else 'casual'
                
                # Update preferences
                config.preferences = {
                    'onboarding_step': 'timing',
                    'communication_style': style_value,
                    **existing_prefs
                }
                self.db_session.commit()
                return self.ONBOARDING_STEPS['timing'], False
                
            elif current_step == 'timing':
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() if k != 'onboarding_step'}
                
                # Super simple timing check - just look for "2", everything else is morning
                time_value = 'evening' if '2' in message else 'morning'
                
                # Update preferences
                config.preferences = {
                    'onboarding_step': 'confirmation',
                    'message_time': time_value,
                    **existing_prefs
                }
                self.db_session.commit()
                return self.ONBOARDING_STEPS['confirmation'], False
                
            elif current_step == 'confirmation':
                # Save any existing preferences
                existing_prefs = {k: v for k, v in config.preferences.items() 
                                if k not in ['onboarding_step', 'onboarding_complete']}
                
                # Accept any response that's not explicitly negative
                negative_words = ['NO', 'NOPE', 'NAH', 'STOP', 'CANCEL', 'QUIT']
                if not any(word in message.upper() for word in negative_words):
                    config.preferences = {
                        'onboarding_complete': True,
                        **existing_prefs
                    }
                    self.db_session.commit()
                    # Generate a personalized welcome message
                    welcome_text = f"Welcome {config.name}! You're all set to receive daily messages. Text STOP at any time to unsubscribe."
                    
                    # If we have a message generator, add a personalized message
                    if self.message_generator:
                        try:
                            context = {
                                'user_name': config.name,
                                'preferences': config.preferences,
                                'personal_info': config.personal_info
                            }
                            personalized_msg = self.message_generator.generate_message(context)
                            welcome_text += f"\n\nHere's your first message:\n{personalized_msg}"
                        except Exception as e:
                            logger.error(f"Error generating first message: {str(e)}")
                    
                    return welcome_text, True
                else:
                    return "No problem! Just reply with anything when you're ready to start receiving messages.", False

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
