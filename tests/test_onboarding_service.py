import pytest
from src.onboarding_service import OnboardingService
from src.models import Recipient, UserConfig

def test_start_onboarding(db_session):
    """Test starting the onboarding process."""
    # Create a test recipient
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    
    # Start onboarding
    first_message = service.start_onboarding(recipient.id)
    
    # Verify the response and state
    assert first_message == service.ONBOARDING_STEPS['name']
    
    # Check that UserConfig was created
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config is not None
    assert config.preferences['onboarding_step'] == 'name'

def test_process_responses(db_session):
    """Test processing responses through the onboarding flow."""
    # Create a test recipient and config
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Test name step
    message, complete = service.process_response(recipient.id, "John Doe")
    assert message == service.ONBOARDING_STEPS['email']
    assert not complete
    
    # Test email step
    message, complete = service.process_response(recipient.id, "john@example.com")
    assert message == service.ONBOARDING_STEPS['timezone']
    assert not complete
    
    # Test timezone step
    message, complete = service.process_response(recipient.id, "New York")
    assert message == service.ONBOARDING_STEPS['preferences']
    assert not complete
    
    # Test preferences step
    message, complete = service.process_response(recipient.id, "M")
    assert message == service.ONBOARDING_STEPS['confirmation']
    assert not complete
    
    # Test confirmation step
    message, complete = service.process_response(recipient.id, "Y")
    assert "Welcome John Doe!" in message
    assert complete
    
    # Verify final state
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.name == "John Doe"
    assert config.email == "john@example.com"
    assert config.personal_info['city'] == "New York"
    assert config.preferences['message_time'] == 'morning'
    assert config.preferences['onboarding_complete'] is True
    assert 'onboarding_step' not in config.preferences

def test_invalid_email(db_session):
    """Test handling invalid email during onboarding."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Process name
    service.process_response(recipient.id, "John Doe")
    
    # Try invalid email
    message, complete = service.process_response(recipient.id, "invalid-email")
    assert "valid email" in message.lower()
    assert not complete
    
    # Config should still be in email step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'email'

def test_invalid_preference(db_session):
    """Test handling invalid preference selection."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Get to preferences step
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "john@example.com")
    service.process_response(recipient.id, "New York")
    
    # Try invalid preference
    message, complete = service.process_response(recipient.id, "X")
    assert "M for morning or E for evening" in message
    assert not complete
    
    # Config should still be in preferences step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'preferences'

def test_is_onboarding_complete(db_session):
    """Test checking onboarding completion status."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    
    # Should be false for new user
    assert not service.is_onboarding_complete(recipient.id)
    
    # Complete onboarding
    service.start_onboarding(recipient.id)
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "john@example.com")
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "M")
    service.process_response(recipient.id, "Y")
    
    # Should be true after completion
    assert service.is_onboarding_complete(recipient.id)

def test_is_in_onboarding(db_session):
    """Test checking if user is in onboarding process."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    
    # Should be false for new user
    assert not service.is_in_onboarding(recipient.id)
    
    # Start onboarding
    service.start_onboarding(recipient.id)
    assert service.is_in_onboarding(recipient.id)
    
    # Complete onboarding
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "john@example.com")
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "M")
    service.process_response(recipient.id, "Y")
    
    # Should be false after completion
    assert not service.is_in_onboarding(recipient.id)
