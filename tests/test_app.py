import pytest
from src.app import app
from src.models import Recipient, UserConfig, MessageLog
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_new_user_starts_onboarding(client, db_session, mocker):
    """Test that a new user is started on the onboarding flow."""
    # Mock Twilio validation
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    
    # Mock SMS service
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    
    # Send first message
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Hello'
    })
    
    # Check response
    assert response.status_code == 200
    assert "Welcome to our service" in response.get_data(as_text=True)
    
    # Verify recipient was created
    recipient = db_session.query(Recipient).filter_by(phone_number='+1234567890').first()
    assert recipient is not None
    
    # Verify UserConfig was created with onboarding step
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config is not None
    assert config.preferences['onboarding_step'] == 'name'
    assert config.personal_info == {}
    assert config.name is None

def test_complete_onboarding_flow(client, db_session, mocker):
    """Test completing the entire onboarding flow."""
    # Mock Twilio validation and SMS service
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    
    # Start onboarding
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Hello'
    })
    assert "Welcome to our service" in response.get_data(as_text=True)
    
    # Send name
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'John Doe'
    })
    assert "city" in response.get_data(as_text=True).lower()
    
    # Verify name storage
    recipient = db_session.query(Recipient).filter_by(phone_number='+1234567890').first()
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.name == "John Doe"
    assert config.personal_info['name'] == "John Doe"
    
    # Send city
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'New York'
    })
    assert "occupation" in response.get_data(as_text=True).lower()
    
    # Verify city and timezone storage
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    recipient = db_session.query(Recipient).filter_by(id=recipient.id).first()
    assert config.personal_info['city'] == "New York"
    assert config.personal_info['timezone'] == "America/New_York"
    assert recipient.timezone == "America/New_York"
    
    # Send occupation
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Software Engineer'
    })
    assert "interests" in response.get_data(as_text=True).lower()
    
    # Send interests
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'coding, hiking'
    })
    assert "style" in response.get_data(as_text=True).lower()
    
    # Send style preference
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'C'
    })
    assert "morning" in response.get_data(as_text=True).lower()
    
    # Send timing preference
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'M'
    })
    assert "confirm" in response.get_data(as_text=True).lower()
    
    # Send confirmation
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Y'
    })
    assert "Welcome John Doe!" in response.get_data(as_text=True)
    
    # Verify final state
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.name == "John Doe"
    assert config.personal_info['name'] == "John Doe"
    assert config.personal_info['city'] == "New York"
    assert config.personal_info['timezone'] == "America/New_York"
    assert config.personal_info['occupation'] == "Software Engineer"
    assert config.personal_info['interests'] == ["coding", "hiking"]
    assert config.preferences['communication_style'] == 'casual'
    assert config.preferences['message_time'] == 'morning'
    assert config.preferences['onboarding_complete'] is True
    assert 'onboarding_step' not in config.preferences
    
    # Verify message logs were created
    logs = db_session.query(MessageLog).filter_by(recipient_id=recipient.id).all()
    assert len(logs) == 16  # 8 inbound + 8 outbound messages

def test_restart_onboarding(client, db_session, mocker):
    """Test restarting onboarding for an existing user."""
    # Mock services
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    
    # Create user with existing config
    recipient = Recipient(phone_number='+1234567890', timezone='UTC', is_active=True)
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
    
    # Start new onboarding
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'START'
    })
    
    # Verify state was reset
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences == {'onboarding_step': 'name'}
    assert config.personal_info == {}
    assert config.name is None

def test_opt_out_during_onboarding(client, db_session, mocker):
    """Test that a user can opt out during onboarding."""
    # Mock Twilio validation and SMS service
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    mocker.patch('src.app.sms_service.handle_opt_out', return_value=True)
    
    # Start onboarding
    client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Hello'
    })
    
    # Send STOP
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'STOP'
    })
    
    assert "unsubscribed" in response.get_data(as_text=True).lower()
    
    # Verify recipient is inactive
    recipient = db_session.query(Recipient).filter_by(phone_number='+1234567890').first()
    assert not recipient.is_active

def test_invalid_phone_number(client, db_session, mocker):
    """Test handling invalid phone numbers."""
    # Mock Twilio validation
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    
    # Mock SMS service to reject number
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=False)
    
    response = client.post('/webhook/inbound', data={
        'From': 'invalid',
        'Body': 'Hello'
    })
    
    assert response.status_code == 400
    assert 'Invalid phone number' in response.get_json()['error']

def test_regular_message_after_onboarding(client, db_session, mocker):
    """Test that completed users get normal responses."""
    # Mock services
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    mocker.patch('src.app.message_generator.generate_response', return_value="AI response")
    
    # Create completed user
    recipient = Recipient(phone_number='+1234567890', timezone='America/New_York', is_active=True)
    db_session.add(recipient)
    db_session.flush()
    
    config = UserConfig(
        recipient_id=recipient.id,
        name="John Doe",
        preferences={
            'onboarding_complete': True,
            'communication_style': 'casual',
            'message_time': 'morning'
        },
        personal_info={
            'name': 'John Doe',
            'city': 'New York',
            'timezone': 'America/New_York',
            'occupation': 'Software Engineer',
            'interests': ['coding', 'hiking']
        }
    )
    db_session.add(config)
    db_session.commit()
    
    # Send regular message
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'How are you?'
    })
    
    # Should get AI response
    assert "AI response" in response.get_data(as_text=True)

def test_invalid_city_during_onboarding(client, db_session, mocker):
    """Test handling invalid city input during onboarding."""
    # Mock services
    mocker.patch('src.app.RequestValidator.validate', return_value=True)
    mocker.patch('src.app.sms_service.validate_phone_number', return_value=True)
    mocker.patch('src.app.sms_service.send_message', return_value={
        'status': 'success',
        'delivery_status': 'sent',
        'message_sid': 'test_sid'
    })
    
    # Start onboarding and provide name
    client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Hello'
    })
    client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'John Doe'
    })
    
    # Try invalid city
    response = client.post('/webhook/inbound', data={
        'From': '+1234567890',
        'Body': 'Invalid City'
    })
    
    assert "don't recognize that city" in response.get_data(as_text=True).lower()
    
    # Verify still in timezone step
    recipient = db_session.query(Recipient).filter_by(phone_number='+1234567890').first()
    config = db_session.query(UserConfig).filter_by(recipient_id=recipient.id).first()
    assert config.preferences['onboarding_step'] == 'timezone'
    assert 'city' not in config.personal_info
    assert 'timezone' not in config.personal_info
