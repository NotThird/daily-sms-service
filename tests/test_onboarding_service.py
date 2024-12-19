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
    assert config.personal_info == {}
    assert config.name is None

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
    
    # Verify name storage
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.name == "John Doe"
    assert config.personal_info['name'] == "John Doe"
    
    # Test timezone step
    message, complete = service.process_response(recipient.id, "New York")
    assert message == service.ONBOARDING_STEPS['occupation']
    assert not complete
    
    # Verify city and timezone storage
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    recipient = db_session.query(Recipient).filter_by(id=recipient.id).first()
    assert config.personal_info['city'] == "New York"
    assert config.personal_info['timezone'] == "America/New_York"
    assert recipient.timezone == "America/New_York"
    
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
    assert config.personal_info['name'] == "John Doe"
    assert config.personal_info['city'] == "New York"
    assert config.personal_info['timezone'] == "America/New_York"
    assert config.personal_info['occupation'] == "Software Engineer"
    assert config.personal_info['interests'] == ["coding", "hiking", "reading"]
    assert config.preferences['communication_style'] == 'casual'
    assert config.preferences['message_time'] == 'morning'
    assert config.preferences['onboarding_complete'] is True
    assert 'onboarding_step' not in config.preferences

def test_invalid_city_with_known_timezone(db_session):
    """Test handling invalid city when user's timezone is known."""
    # Create recipient with known timezone
    recipient = Recipient(phone_number='+1234567890', timezone='America/Chicago', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Process name
    service.process_response(recipient.id, "John Doe")
    
    # Try invalid city
    message, complete = service.process_response(recipient.id, "Invalid City")
    assert "Since you're in the America/Chicago timezone" in message
    assert "Dallas" in message  # Should suggest a major city in Central timezone
    assert not complete
    
    # Config should still be in timezone step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'timezone'
    assert 'city' not in config.personal_info
    assert 'timezone' not in config.personal_info

def test_invalid_city_without_known_timezone(db_session):
    """Test handling invalid city when user's timezone is unknown."""
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Process name
    service.process_response(recipient.id, "John Doe")
    
    # Try invalid city
    message, complete = service.process_response(recipient.id, "Invalid City")
    assert "major US city" in message
    assert "New York" in message
    assert "Chicago" in message
    assert "Los Angeles" in message
    assert not complete
    
    # Config should still be in timezone step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'timezone'
    assert 'city' not in config.personal_info
    assert 'timezone' not in config.personal_info

def test_smaller_city_in_known_timezone(db_session):
    """Test suggesting nearby cities when user enters a smaller city."""
    # Create recipient in Central timezone
    recipient = Recipient(phone_number='+1234567890', timezone='America/Chicago', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    service = OnboardingService(db_session)
    service.start_onboarding(recipient.id)
    
    # Process name
    service.process_response(recipient.id, "John Doe")
    
    # Try smaller city
    message, complete = service.process_response(recipient.id, "Waco")  # Smaller Texas city
    assert "America/Chicago timezone" in message
    assert any(city in message for city in ['Dallas', 'Houston', 'San Antonio'])  # Should suggest major Texas cities
    assert not complete

def test_restart_onboarding(db_session):
    """Test restarting onboarding for an existing user."""
    # Create user with existing config
    recipient = Recipient(phone_number='+1234567890', timezone='America/Chicago', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    config = UserConfig(
        recipient_id=recipient.id,
        name="Old Name",
        preferences={'some_pref': 'value'},
        personal_info={'some_info': 'value'}
    )
    db_session.add(config)
    db_session.commit()
    
    service = OnboardingService(db_session)
    
    # Restart onboarding
    first_message = service.start_onboarding(recipient.id)
    
    # Verify state was reset
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences == {'onboarding_step': 'name'}
    assert config.personal_info == {}
    assert config.name is None
    
    # Verify timezone wasn't lost in Recipient
    recipient = db_session.query(Recipient).filter_by(id=recipient.id).first()
    assert recipient.timezone == 'America/Chicago'
