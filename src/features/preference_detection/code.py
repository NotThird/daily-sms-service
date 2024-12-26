"""
---
title: Preference Detection Service
description: Analyzes user messages to detect and update communication preferences
authors: AI Assistant
date_created: 2024-01-20
dependencies:
  - user_management
  - message_generation
---
"""

from typing import Dict, Optional
from sqlalchemy.orm import Session
from src.models import UserConfig

class PreferenceDetector:
    """Detects and manages user preferences from message interactions."""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        
    def analyze_message(self, user_message: str, recipient_id: int) -> Dict:
        """
        Analyze a user message to detect preferences and update user config.
        
        Args:
            user_message: The message to analyze
            recipient_id: The ID of the message recipient
            
        Returns:
            Dict of detected preferences
        """
        detected_prefs = self._detect_preferences(user_message)
        if detected_prefs:
            self._update_user_preferences(recipient_id, detected_prefs)
        return detected_prefs
    
    def _detect_preferences(self, message: str) -> Dict:
        """
        Detect preferences from a message.
        
        Detects:
        - Language preferences (e.g., French usage)
        - Communication style (formal, casual, etc.)
        - Tone preferences (enthusiastic, calm, etc.)
        """
        prefs = {}
        
        # Detect language preferences
        if any(french_word in message.lower() for french_word in 
               ['bonjour', 'merci', 'oui', 'non', 'je', 'tu', 'vous']):
            prefs['language'] = 'French'
            
        # Detect formality level
        formal_indicators = ['please', 'thank you', 'would you', 'could you']
        casual_indicators = ['hey', 'hi', 'thanks', 'cool']
        
        formal_count = sum(1 for word in formal_indicators if word in message.lower())
        casual_count = sum(1 for word in casual_indicators if word in message.lower())
        
        if formal_count > casual_count:
            prefs['communication_style'] = 'formal'
        elif casual_count > formal_count:
            prefs['communication_style'] = 'casual'
            
        # Detect tone preferences
        if any(word in message.lower() for word in ['!', 'wow', 'amazing', 'awesome']):
            prefs['tone'] = 'enthusiastic'
        elif all(word not in message.lower() for word in ['!', '?']) and len(message.split()) > 3:
            prefs['tone'] = 'calm'
            
        return prefs
    
    def _update_user_preferences(self, recipient_id: int, new_prefs: Dict) -> None:
        """Update user preferences in the database."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        
        if not config:
            config = UserConfig(recipient_id=recipient_id, preferences={})
            self.db.add(config)
            
        # Merge new preferences with existing ones
        current_prefs = config.preferences or {}
        for key, value in new_prefs.items():
            # Only update if we have high confidence (could add confidence scoring later)
            current_prefs[key] = value
            
        config.preferences = current_prefs
        self.db.commit()
    
    def get_user_preferences(self, recipient_id: int) -> Optional[Dict]:
        """Get current preferences for a user."""
        config = self.db.query(UserConfig).filter_by(recipient_id=recipient_id).first()
        return config.preferences if config else None
