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
                "Welcome! 👋 I'm your daily positivity companion, powered by AI. "
                "I'll send you personalized messages to brighten your day. "
                "First, what's your name?"
            )
            
        # Resume onboarding from last stage
        stage = config.preferences.get('onboarding_stage', 'name')
        if stage == 'name':
            return (
                "Let's get started with personalizing your experience! "
                "What's your name?"
            )
        elif stage == 'interests':
            return (
                "Great! To make your messages more meaningful, "
                "what are some of your interests or hobbies? "
                "(Separate multiple interests with commas)"
            )
        elif stage == 'style':
            return (
                "How would you like your daily messages? Choose a style:\n\n"
                "1. Professional & Motivational - Focused on growth and achievement\n"
                "2. Friendly & Casual - Like a supportive friend\n"
                "3. Short & Direct - Brief, impactful messages\n\n"
                "Reply with 1, 2, or 3"
            )
        elif stage == 'time':
            return (
                "Last step! When would you like to receive your daily message?\n\n"
                "Enter a time in 24-hour format (e.g., 09:00 for 9 AM, 14:30 for 2:30 PM)\n"
                "I'll send your personalized message at this time each day."
            )
        else:
            return (
                "Let's start fresh with your personalization! "
                "What's your name?"
            )
            
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
                f"Nice to meet you, {config.name}! 👋\n\n"
                "Now, tell me about your interests or hobbies. "
                "This helps me create messages that resonate with you. "
                "For example: reading, fitness, cooking, travel"
            ), False
            
        elif stage == 'interests':
            interests = [i.strip() for i in response.split(',')]
            if not config.personal_info:
                config.personal_info = {}
            config.personal_info['interests'] = interests
            config.preferences['onboarding_stage'] = 'style'
            self.db.commit()
            return (
                "Thanks for sharing your interests! 🌟\n\n"
                "How would you like your daily messages?\n\n"
                "1. Professional & Motivational - Focused on growth and achievement\n"
                "2. Friendly & Casual - Like a supportive friend\n"
                "3. Short & Direct - Brief, impactful messages\n\n"
                "Reply with 1, 2, or 3"
            ), False
            
        elif stage == 'style':
            style_map = {
                '1': 'professional',
                '2': 'casual',
                '3': 'direct'
            }
            style = style_map.get(response.strip(), 'casual')
            config.preferences['communication_style'] = style
            config.preferences['onboarding_stage'] = 'time'
            self.db.commit()
            return (
                "What time would you like to receive your daily message? (24-hour format)\n"
                "For example: 09:00 for 9 AM, 14:30 for 2:30 PM"
            ), False
            
        elif stage == 'time':
            try:
                # Validate time format
                import re
                if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', response.strip()):
                    return "Please enter a valid time in 24-hour format (e.g., 09:00, 14:30)", False
                
                hour, minute = map(int, response.strip().split(':'))
                config.preferences['message_time'] = f"{hour:02d}:{minute:02d}"
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
                        f"Perfect! You're all set to receive daily positive messages at {config.preferences['message_time']}. 🎉\n\n"
                        f"I'll craft messages that match your {style} style and interests. "
                        "Text STOP anytime to pause messages, or RESTART to update your preferences.\n\n"
                        "Your first personalized message is coming soon!"
                    )
                    
                return welcome, True
                
            except ValueError:
                return "Please enter a valid time in 24-hour format (e.g., 09:00, 14:30)", False
            
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
