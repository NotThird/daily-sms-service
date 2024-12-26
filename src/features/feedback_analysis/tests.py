"""
Test suite for feedback analysis functionality.
Covers typical and edge cases for UserFeedback and FeedbackAnalyzer classes.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from features.core.code import db_session
from features.feedback_analysis.code import UserFeedback, FeedbackAnalyzer
from features.user_management.code import User

@pytest.fixture
def sample_user():
    """Creates a test user."""
    user = User(id=1, phone_number="+1234567890")
    return user

@pytest.fixture
def sample_feedback(sample_user):
    """Creates a test feedback instance."""
    feedback = UserFeedback(
        id=1,
        user_id=sample_user.id,
        message_id=1,
        response_text="Thanks for the great message!",
        created_at=datetime.utcnow()
    )
    return feedback

class TestUserFeedback:
    """Test cases for UserFeedback class."""
    
    def test_validate_response_valid(self):
        """Test response validation with valid input."""
        valid_responses = [
            "Thank you for the message!",
            "This was very helpful",
            "1234567890"
        ]
        for response in valid_responses:
            assert UserFeedback.validate_response(response) is True
            
    def test_validate_response_invalid(self):
        """Test response validation with invalid input."""
        invalid_responses = [
            "",  # Empty string
            "x" * 1001,  # Too long
            "Invalid UTF-8 \x80",  # Non-ASCII characters
            None  # None value
        ]
        for response in invalid_responses:
            if response is not None:  # Skip None as it would raise TypeError
                assert UserFeedback.validate_response(response) is False
                
    def test_calculate_sentiment(self, sample_feedback):
        """Test sentiment calculation."""
        # Positive sentiment
        sample_feedback.response_text = "This is great and helpful!"
        assert sample_feedback.calculate_sentiment() > 0
        
        # Negative sentiment
        sample_feedback.response_text = "This is bad and unhelpful"
        assert sample_feedback.calculate_sentiment() < 0
        
        # Neutral sentiment
        sample_feedback.response_text = "Message received"
        assert sample_feedback.calculate_sentiment() == 0
        
    def test_sentiment_caching(self, sample_feedback):
        """Test sentiment score caching."""
        sample_feedback.response_text = "This is wonderful!"
        
        # First calculation
        score1 = sample_feedback.calculate_sentiment()
        
        # Should use cached value
        score2 = sample_feedback.calculate_sentiment()
        
        assert score1 == score2
        assert sample_feedback.response_text in UserFeedback._sentiment_cache

class TestFeedbackAnalyzer:
    """Test cases for FeedbackAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Creates a FeedbackAnalyzer instance."""
        return FeedbackAnalyzer()
        
    @pytest.fixture
    def mock_feedback_history(self):
        """Creates mock feedback history."""
        return [
            UserFeedback(
                user_id=1,
                message_id=i,
                response_text=f"Test response {i}",
                created_at=datetime.utcnow() - timedelta(days=i)
            )
            for i in range(5)
        ]
        
    def test_analyze_user_preferences_empty(self, analyzer):
        """Test preference analysis with no feedback history."""
        with patch('features.feedback_analysis.code.db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
            
            preferences = analyzer.analyze_user_preferences(1)
            assert preferences == {}
            
    def test_analyze_user_preferences(self, analyzer, mock_feedback_history):
        """Test preference analysis with feedback history."""
        with patch('features.feedback_analysis.code.db_session') as mock_session:
            mock_session.return_value.__enter__.return_value.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_feedback_history
            
            preferences = analyzer.analyze_user_preferences(1)
            
            assert isinstance(preferences, dict)
            assert all(k.startswith('topic_') for k in preferences.keys())
            assert all(isinstance(v, float) for v in preferences.values())
            assert sum(preferences.values()) == pytest.approx(1.0)
            
    def test_get_personalization_params(self, analyzer):
        """Test personalization parameter generation."""
        with patch.object(analyzer, 'analyze_user_preferences') as mock_analyze:
            # Test with no preferences
            mock_analyze.return_value = {}
            params = analyzer.get_personalization_params(1)
            assert params["tone"] == "positive"
            assert params["length"] == "medium"
            assert params["topics"] == []
            
            # Test with strong preferences
            mock_analyze.return_value = {
                "topic_1": 0.8,
                "topic_2": 0.2
            }
            params = analyzer.get_personalization_params(1)
            assert params["tone"] == "very_positive"
            assert "topic_1" in params["topics"]
            
            # Test with weak preferences
            mock_analyze.return_value = {
                "topic_1": 0.2,
                "topic_2": 0.2
            }
            params = analyzer.get_personalization_params(1)
            assert params["tone"] == "neutral"
