"""Tests for preference detection feature."""
import pytest
from unittest.mock import Mock, patch
from src.features.preference_detection.code import PreferenceDetector
from src.models import UserConfig

@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    return session

@pytest.fixture
def detector(mock_db_session):
    """Create a PreferenceDetector instance with mocked session."""
    return PreferenceDetector(mock_db_session)

def test_detect_french_language(detector):
    """Test detection of French language preference."""
    message = "Bonjour! Comment allez-vous?"
    prefs = detector._detect_preferences(message)
    assert prefs.get('language') == 'French'

def test_detect_formal_style(detector):
    """Test detection of formal communication style."""
    message = "Could you please help me? Thank you very much."
    prefs = detector._detect_preferences(message)
    assert prefs.get('communication_style') == 'formal'

def test_detect_casual_style(detector):
    """Test detection of casual communication style."""
    message = "Hey! Thanks, that's cool!"
    prefs = detector._detect_preferences(message)
    assert prefs.get('communication_style') == 'casual'

def test_detect_enthusiastic_tone(detector):
    """Test detection of enthusiastic tone."""
    message = "Wow! This is amazing!"
    prefs = detector._detect_preferences(message)
    assert prefs.get('tone') == 'enthusiastic'

def test_detect_calm_tone(detector):
    """Test detection of calm tone."""
    message = "I appreciate your thoughtful message"
    prefs = detector._detect_preferences(message)
    assert prefs.get('tone') == 'calm'

def test_update_existing_preferences(detector, mock_db_session):
    """Test updating existing user preferences."""
    # Setup mock config
    mock_config = Mock(preferences={'language': 'English'})
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_config
    
    # Update preferences
    new_prefs = {'tone': 'enthusiastic'}
    detector._update_user_preferences(1, new_prefs)
    
    # Verify preferences were merged
    assert mock_config.preferences == {
        'language': 'English',
        'tone': 'enthusiastic'
    }
    mock_db_session.commit.assert_called_once()

def test_create_new_preferences(detector, mock_db_session):
    """Test creating preferences for new user."""
    # Setup mock to return no existing config
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
    
    # Update preferences
    new_prefs = {'language': 'French'}
    detector._update_user_preferences(1, new_prefs)
    
    # Verify new config was created
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()

def test_analyze_message_flow(detector):
    """Test complete message analysis flow."""
    message = "Bonjour! This is amazing!"
    recipient_id = 1
    
    # Mock database operations
    mock_config = Mock(preferences={})
    detector.db.query.return_value.filter_by.return_value.first.return_value = mock_config
    
    # Analyze message
    result = detector.analyze_message(message, recipient_id)
    
    # Verify results
    assert result.get('language') == 'French'
    assert result.get('tone') == 'enthusiastic'
    detector.db.commit.assert_called_once()

def test_get_user_preferences(detector, mock_db_session):
    """Test retrieving user preferences."""
    # Setup mock config
    expected_prefs = {'language': 'French', 'tone': 'enthusiastic'}
    mock_config = Mock(preferences=expected_prefs)
    mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_config
    
    # Get preferences
    prefs = detector.get_user_preferences(1)
    
    # Verify results
    assert prefs == expected_prefs
