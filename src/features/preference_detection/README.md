# Preference Detection Feature

This feature analyzes user interactions and messages to automatically detect and update user preferences for message customization.

## Purpose

The preference detection feature is responsible for:
- Analyzing user message responses
- Detecting topic preferences
- Identifying preferred message styles
- Updating user preferences automatically
- Learning from user interactions

## Components

### Preference Analyzer (code.py)
- Message content analysis
- Sentiment detection
- Topic classification
- Preference scoring
- Automatic updates

## Usage

### Analyzing User Response

```python
from features.preference_detection.code import PreferenceAnalyzer

analyzer = PreferenceAnalyzer()
preferences = await analyzer.analyze_response(
    user_id=123,
    message="Really enjoyed today's message about personal growth!"
)
```

### Batch Analysis

```python
from features.preference_detection.code import analyze_user_history

preferences = await analyze_user_history(
    user_id=123,
    days=30  # Analyze last 30 days
)
```

## Dependencies

### Internal Dependencies
- features/core/code.py: Database models
- features/user_management/config.py: User preferences

### External Dependencies
- nltk: Natural language processing
- scikit-learn: Machine learning
- pandas: Data analysis

## Configuration

The feature can be configured through environment variables:

```bash
# Analysis Settings
MIN_CONFIDENCE_SCORE=0.7
MAX_TOPICS_PER_USER=5
ANALYSIS_BATCH_SIZE=100

# Model Settings
SENTIMENT_MODEL=vader
TOPIC_MODEL=lda
```

## Analysis Components

1. **Topic Detection**
   ```python
   TOPIC_CATEGORIES = {
       'personal_growth': ['growth', 'improvement', 'goals'],
       'motivation': ['inspire', 'achieve', 'success'],
       'mindfulness': ['peace', 'present', 'calm']
   }
   ```

2. **Sentiment Analysis**
   ```python
   SENTIMENT_WEIGHTS = {
       'positive': 1.0,
       'neutral': 0.5,
       'negative': 0.0
   }
   ```

## Testing

The feature includes comprehensive tests covering:
- Message analysis
- Preference detection
- Sentiment analysis
- Topic classification
- Integration tests

```bash
# Run preference detection tests
pytest src/features/preference_detection/tests.py
```

## Error Handling

1. **Analysis Errors**
   - Invalid message format
   - Processing failures
   - Model errors
   - Low confidence scores

2. **Update Failures**
   - Database errors
   - Invalid preferences
   - Conflicting updates
   - Version conflicts

3. **Resource Issues**
   - Model loading failures
   - Memory constraints
   - Processing timeouts

## Performance Considerations

1. **Processing Optimization**
   - Batch processing
   - Caching of models
   - Efficient text analysis
   - Resource management

2. **Update Management**
   - Throttled updates
   - Confidence thresholds
   - Change validation
   - History tracking

3. **Resource Usage**
   - Model size optimization
   - Memory management
   - Processing limits
   - Cleanup routines
