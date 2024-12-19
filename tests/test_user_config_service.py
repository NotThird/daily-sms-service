import pytest
from src.models import UserConfig, Recipient
from src.user_config_service import UserConfigService

def test_create_config(db_session):
    service = UserConfigService(db_session)
    
    # Create a test recipient first
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    # Test creating new config
    config = service.create_or_update_config(
        recipient_id=recipient.id,
        name="Test User",
        preferences={"language": "en", "topics": ["tech", "science"]},
        personal_info={"age": 25, "occupation": "developer"}
    )

    assert config.recipient_id == recipient.id
    assert config.name == "Test User"
    assert config.preferences == {"language": "en", "topics": ["tech", "science"]}
    assert config.personal_info == {"age": 25, "occupation": "developer"}

def test_update_config(db_session):
    service = UserConfigService(db_session)
    
    # Create initial data
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    config = service.create_or_update_config(
        recipient_id=recipient.id,
        name="Test User",
        preferences={"language": "en"}
    )

    # Test updating config
    updated_config = service.create_or_update_config(
        recipient_id=recipient.id,
        name="Updated User",
        preferences={"language": "es"}
    )

    assert updated_config.name == "Updated User"
    assert updated_config.preferences == {"language": "es"}
    assert updated_config.id == config.id  # Should update existing record

def test_get_config(db_session):
    service = UserConfigService(db_session)
    
    # Create test data
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    original_config = service.create_or_update_config(
        recipient_id=recipient.id,
        name="Test User"
    )

    # Test retrieving config
    config = service.get_config(recipient.id)
    assert config is not None
    assert config.id == original_config.id
    assert config.name == "Test User"

def test_update_preferences(db_session):
    service = UserConfigService(db_session)
    
    # Create test data
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    config = service.create_or_update_config(
        recipient_id=recipient.id,
        preferences={"theme": "light"}
    )

    # Test updating just preferences
    updated_config = service.update_preferences(
        recipient_id=recipient.id,
        preferences={"theme": "dark", "notifications": True}
    )

    assert updated_config.preferences == {"theme": "dark", "notifications": True}
    assert updated_config.id == config.id

def test_update_personal_info(db_session):
    service = UserConfigService(db_session)
    
    # Create test data
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    config = service.create_or_update_config(
        recipient_id=recipient.id,
        personal_info={"city": "New York"}
    )

    # Test updating just personal info
    updated_config = service.update_personal_info(
        recipient_id=recipient.id,
        personal_info={"city": "San Francisco", "interests": ["hiking"]}
    )

    assert updated_config.personal_info == {"city": "San Francisco", "interests": ["hiking"]}
    assert updated_config.id == config.id

def test_get_gpt_prompt_context(db_session):
    service = UserConfigService(db_session)
    
    # Create test data
    recipient = Recipient(phone_number="+1234567890", timezone="UTC")
    db_session.add(recipient)
    db_session.commit()

    service.create_or_update_config(
        recipient_id=recipient.id,
        name="Test User",
        preferences={"style": "casual"},
        personal_info={"hobbies": ["reading"]}
    )

    # Test getting GPT prompt context
    context = service.get_gpt_prompt_context(recipient.id)
    
    assert context["user_name"] == "Test User"
    assert context["preferences"] == {"style": "casual"}
    assert context["personal_info"] == {"hobbies": ["reading"]}

def test_get_nonexistent_config(db_session):
    service = UserConfigService(db_session)
    
    # Test getting config for non-existent recipient
    config = service.get_config(999)
    assert config is None

    # Test getting GPT context for non-existent recipient
    context = service.get_gpt_prompt_context(999)
    assert context == {}
