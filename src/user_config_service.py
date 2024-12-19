from typing import Dict, Optional
from sqlalchemy.orm import Session
from .models import UserConfig, Recipient

class UserConfigService:
    def __init__(self, db_session: Session):
        self.db = db_session

    def create_or_update_config(
        self,
        recipient_id: int,
        name: Optional[str] = None,
        preferences: Optional[Dict] = None,
        personal_info: Optional[Dict] = None
    ) -> UserConfig:
        """Create or update a user's configuration."""
        config = self.db.query(UserConfig).filter(
            UserConfig.recipient_id == recipient_id
        ).first()

        if not config:
            config = UserConfig(
                recipient_id=recipient_id,
                name=name,
                preferences=preferences or {},
                personal_info=personal_info or {}
            )
            self.db.add(config)
        else:
            if name is not None:
                config.name = name
            if preferences is not None:
                config.preferences = preferences
            if personal_info is not None:
                config.personal_info = personal_info

        self.db.commit()
        return config

    def get_config(self, recipient_id: int) -> Optional[UserConfig]:
        """Get a user's configuration."""
        return self.db.query(UserConfig).filter(
            UserConfig.recipient_id == recipient_id
        ).first()

    def update_preferences(
        self,
        recipient_id: int,
        preferences: Dict
    ) -> Optional[UserConfig]:
        """Update just the preferences portion of a user's config."""
        config = self.get_config(recipient_id)
        if config:
            config.preferences = preferences
            self.db.commit()
        return config

    def update_personal_info(
        self,
        recipient_id: int,
        personal_info: Dict
    ) -> Optional[UserConfig]:
        """Update just the personal_info portion of a user's config."""
        config = self.get_config(recipient_id)
        if config:
            config.personal_info = personal_info
            self.db.commit()
        return config

    def get_gpt_prompt_context(self, recipient_id: int) -> Dict:
        """Get personalized context for GPT prompts."""
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
