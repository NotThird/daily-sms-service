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
    assert message == service.ONBOARDING_STEPS['timezone']
    assert not complete
    
    # Test timezone step
    message, complete = service.process_response(recipient.id, "New York")
    assert message == service.ONBOARDING_STEPS['occupation']
    assert not complete
    
    # Test occupation step
    message, complete = service.process_response(recipient.id, "Software Engineer")
    assert message == service.ONBOARDING_STEPS['interests']
    assert not complete
    
    # Test interests step
    message, complete = service.process_response(recipient.id, "coding, hiking, reading")
    assert message == service.ONBOARDING_STEPS['style']
    assert not complete
    
    # Test style step
    message, complete = service.process_response(recipient.id, "C")
    assert message == service.ONBOARDING_STEPS['timing']
    assert not complete
    
    # Test timing step
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
    assert config.personal_info['city'] == "New York"
    assert config.personal_info['occupation'] == "Software Engineer"
    assert config.personal_info['interests'] == ["coding", "hiking", "reading"]
    assert config.preferences['communication_style'] == 'casual'
    assert config.preferences['message_time'] == 'morning'
    assert config.preferences['onboarding_complete'] is True
    assert 'onboarding_step' not in config.preferences

def test_invalid_city(db_session):
    """Test handling invalid city during onboarding."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Process name
    service.process_response(recipient.id, "John Doe")
    
    # Try invalid city
    message, complete = service.process_response(recipient.id, "Invalid City")
    assert "don't recognize that city" in message
    assert not complete
    
    # Config should still be in timezone step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'timezone'

def test_invalid_style(db_session):
    """Test handling invalid communication style selection."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Get to style step
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "Software Engineer")
    service.process_response(recipient.id, "coding, hiking")
    
    # Try invalid style
    message, complete = service.process_response(recipient.id, "X")
    assert "C for Casual or P for Professional" in message
    assert not complete
    
    # Config should still be in style step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'style'

def test_invalid_timing(db_session):
    """Test handling invalid timing preference."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Get to timing step
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "Software Engineer")
    service.process_response(recipient.id, "coding, hiking")
    service.process_response(recipient.id, "C")
    
    # Try invalid timing
    message, complete = service.process_response(recipient.id, "X")
    assert "M for morning or E for evening" in message
    assert not complete
    
    # Config should still be in timing step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'timing'

def test_invalid_confirmation(db_session):
    """Test handling invalid confirmation response."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Get to confirmation step
    service.process_response(recipient.id, "John Doe")
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "Software Engineer")
    service.process_response(recipient.id, "coding, hiking")
    service.process_response(recipient.id, "C")
    service.process_response(recipient.id, "M")
    
    # Try invalid confirmation
    message, complete = service.process_response(recipient.id, "N")
    assert "reply Y to confirm" in message.lower()
    assert not complete
    
    # Config should still be in confirmation step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'confirmation'

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
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "Software Engineer")
    service.process_response(recipient.id, "coding, hiking")
    service.process_response(recipient.id, "C")
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
    service.process_response(recipient.id, "New York")
    service.process_response(recipient.id, "M")
    service.process_response(recipient.id, "Y")
    
    # Should be false after completion
    assert not service.is_in_onboarding(recipient.id)
