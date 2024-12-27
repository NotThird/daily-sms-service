"""
User Management
--------------
Description: Handles user configuration, preferences, and onboarding
Authors: AI Assistant
Date Created: 2024-01-09
Dependencies:
  - core
  - message_generation
"""

from typing import Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from src.features.core.code import UserConfig, Recipient
from src.features.message_generation.code import MessageGenerator

class UserConfigService:
    """Manages user configuration and preferences."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def create_or_update_config(
        self,
        recipient_id: int,
        name: Optional[str] = None,
        preferences: Optional[Dict[str, Any]] = None,
        personal_info: Optional[Dict[str, Any]] = None
    ) -> UserConfig:
        """Create or update user configuration."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        
        if not config:
            config = UserConfig(recipient_id=recipient_id)
            self.db.add(config)
            
        if name is not None:
            config.name = name
        if preferences is not None:
            config.preferences = preferences
        if personal_info is not None:
            config.personal_info = personal_info
            
        self.db.commit()
        return config
        
    def get_config(self, recipient_id: int) -> Optional[UserConfig]:
        """Get user configuration."""
        return self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        
    def get_gpt_prompt_context(self, recipient_id: int) -> Dict[str, Any]:
        """Get context for GPT prompt generation."""
        config = self.get_config(recipient_id)
        if not config:
            return {}
            
        context = {}
        if config.name:
            context['user_name'] = config.name
        if config.preferences:
            context['preferences'] = config.preferences
        if config.personal_info:
            context['personal_info'] = config.personal_info
            
        return context

class OnboardingService:
    """Manages user onboarding process."""
    
    def __init__(self, db_session: Session, message_generator: MessageGenerator):
        self.db = db_session
        self.message_generator = message_generator
        
    def start_onboarding(self, recipient_id: int) -> str:
        """Start onboarding process for a new user."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        
        if not config:
            config = UserConfig(
                recipient_id=recipient_id,
                preferences={'onboarding_stage': 'name'}
            )
            self.db.add(config)
            self.db.commit()
            return (
                "Welcome! 👋 I'm your daily positivity companion. "
                "To personalize your experience, what's your name?"
            )
            
        # Resume onboarding from last stage
        stage = config.preferences.get('onboarding_stage', 'name')
        if stage == 'name':
            return "What's your name?"
        elif stage == 'interests':
            return (
                "Great! What are some of your interests or hobbies? "
                "This helps me make messages more relevant to you."
            )
        elif stage == 'style':
            return (
                "How would you prefer your messages? Choose: \n"
                "1. Professional and motivational\n"
                "2. Friendly and casual\n"
                "3. Short and direct\n"
                "(Just reply with the number)"
            )
        else:
            return "Let's start over. What's your name?"
            
    def process_response(self, recipient_id: int, response: str) -> Tuple[str, bool]:
        """
        Process user response during onboarding.
        Returns (next_message, is_complete).
        """
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        if not config:
            return self.start_onboarding(recipient_id), False
            
        stage = config.preferences.get('onboarding_stage', 'name')
        
        if stage == 'name':
            config.name = response.strip()
            config.preferences['onboarding_stage'] = 'interests'
            self.db.commit()
            return (
                f"Nice to meet you, {config.name}! "
                "What are some of your interests or hobbies?"
            ), False
            
        elif stage == 'interests':
            interests = [i.strip() for i in response.split(',')]
            if not config.personal_info:
                config.personal_info = {}
            config.personal_info['interests'] = interests
            config.preferences['onboarding_stage'] = 'style'
            self.db.commit()
            return (
                "Great! How would you prefer your messages? Choose:\n"
                "1. Professional and motivational\n"
                "2. Friendly and casual\n"
                "3. Short and direct\n"
                "(Just reply with the number)"
            ), False
            
        elif stage == 'style':
            style_map = {
                '1': 'professional',
                '2': 'casual',
                '3': 'direct'
            }
            style = style_map.get(response.strip(), 'casual')
            config.preferences['communication_style'] = style
            config.preferences['onboarding_complete'] = True
            del config.preferences['onboarding_stage']
            self.db.commit()
            
            # Generate personalized welcome message
            try:
                welcome = self.message_generator.generate_message(
                    self.get_gpt_prompt_context(recipient_id)
                )
            except Exception:
                welcome = (
                    "Perfect! You're all set to receive daily positive messages. "
                    "They'll be personalized just for you!"
                )
                
            return welcome, True
            
        return "I didn't quite get that. Let's start over.", False
        
    def is_in_onboarding(self, recipient_id: int) -> bool:
        """Check if user is currently in onboarding."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        return bool(
            config and 
            config.preferences and 
            'onboarding_stage' in config.preferences
        )
        
    def is_onboarding_complete(self, recipient_id: int) -> bool:
        """Check if user has completed onboarding."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        return bool(
            config and 
            config.preferences and 
            config.preferences.get('onboarding_complete', False)
        )
        
    def get_gpt_prompt_context(self, recipient_id: int) -> Dict[str, Any]:
        """Get context for GPT prompt generation."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        if not config:
            return {}
            
        context = {}
        if config.name:
            context['user_name'] = config.name
        if config.preferences:
            context['preferences'] = config.preferences
        if config.personal_info:
            context['personal_info'] = config.personal_info
            
        return context
