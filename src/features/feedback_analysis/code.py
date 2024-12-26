"""
Feedback Analysis System
-----------------------
Title: Feedback Analysis System
Description: Analyzes user responses to messages and adapts content generation
Authors: AI Assistant
Date Created: 2024-01-21
Dependencies:
    Internal:
        - features/core/code.py
        - features/message_generation/code.py
        - features/user_management/code.py
    External:
        - sqlalchemy
        - scikit-learn
"""

"""
Implements feedback analysis and message adaptation based on user responses.
Uses sentiment analysis and pattern recognition to improve message personalization.
"""

from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Float
from sqlalchemy.orm import relationship
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import MiniBatchKMeans

from features.core.code import Base, db_session
from features.message_generation.code import MessageGenerator
from features.user_management.code import User

class UserFeedback(Base):
    """Stores and analyzes user feedback for message personalization."""
    __tablename__ = 'user_feedback'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    message_id = Column(Integer, ForeignKey('scheduled_messages.id'), nullable=False)
    response_text = Column(String, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="feedback")
    message = relationship("ScheduledMessage", back_populates="feedback")

    # Security: Input validation
    @staticmethod
    def validate_response(response_text: str) -> bool:
        """
        Validates user response text for security.
        Prevents injection and ensures reasonable length.
        """
        if not response_text:
            return False
        if len(response_text) > 1000:  # Reasonable limit for SMS responses
            return False
        # Basic sanitization
        return all(ord(char) < 128 for char in response_text)  # ASCII only

    # Performance: Caching frequently accessed data
    _sentiment_cache = {}
    
    def calculate_sentiment(self) -> float:
        """
        Calculates sentiment score for the response.
        Uses caching for performance optimization.
        """
        if self.response_text in self._sentiment_cache:
            return self._sentiment_cache[self.response_text]
            
        # Simple sentiment analysis (production would use more sophisticated methods)
        positive_words = {'thanks', 'good', 'great', 'love', 'helpful', 'wonderful'}
        negative_words = {'bad', 'unhelpful', 'stop', 'negative', 'unnecessary'}
        
        words = set(self.response_text.lower().split())
        pos_count = len(words.intersection(positive_words))
        neg_count = len(words.intersection(negative_words))
        
        if pos_count + neg_count == 0:
            score = 0.0
        else:
            score = (pos_count - neg_count) / (pos_count + neg_count)
            
        self._sentiment_cache[self.response_text] = score
        return score

class FeedbackAnalyzer:
    """Analyzes user feedback patterns to improve message personalization."""
    
    def __init__(self):
        self.vectorizer = TfidfVectorizer(max_features=1000)
        self.clusterer = MiniBatchKMeans(n_clusters=5)
        
    def analyze_user_preferences(self, user_id: int) -> Dict[str, float]:
        """
        Analyzes user's feedback history to determine content preferences.
        Returns a dictionary of topic weights.
        """
        with db_session() as session:
            feedback_history = session.query(UserFeedback).filter(
                UserFeedback.user_id == user_id
            ).order_by(UserFeedback.created_at.desc()).limit(50).all()
            
            if not feedback_history:
                return {}
                
            # Extract responses with positive sentiment
            positive_responses = [
                f.response_text for f in feedback_history 
                if f.calculate_sentiment() > 0
            ]
            
            if not positive_responses:
                return {}
                
            # Vectorize and cluster responses
            try:
                vectors = self.vectorizer.fit_transform(positive_responses)
                clusters = self.clusterer.fit_predict(vectors)
                
                # Calculate preference weights based on cluster distribution
                cluster_counts = {i: 0 for i in range(self.clusterer.n_clusters)}
                for cluster in clusters:
                    cluster_counts[cluster] += 1
                    
                total = len(clusters)
                return {
                    f"topic_{k}": v/total 
                    for k, v in cluster_counts.items()
                }
            except Exception:
                return {}

    def get_personalization_params(self, user_id: int) -> Dict[str, any]:
        """
        Generates personalization parameters for message generation.
        Used by the message generation system to tailor content.
        """
        preferences = self.analyze_user_preferences(user_id)
        
        # Convert preferences to generation parameters
        params = {
            "tone": "positive",  # Default tone
            "length": "medium",  # Default length
            "topics": [],       # Preferred topics
        }
        
        # Adjust parameters based on preferences
        if preferences:
            # Find dominant topic
            max_topic = max(preferences.items(), key=lambda x: x[1])[0]
            params["topics"] = [max_topic]
            
            # Adjust tone based on overall preference strength
            avg_preference = sum(preferences.values()) / len(preferences)
            if avg_preference > 0.7:
                params["tone"] = "very_positive"
            elif avg_preference < 0.3:
                params["tone"] = "neutral"
                
        return params
