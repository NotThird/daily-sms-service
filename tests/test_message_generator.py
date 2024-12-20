import pytest
from unittest.mock import Mock, patch
from src.message_generator import MessageGenerator

@pytest.fixture
def message_generator():
    return MessageGenerator("fake-api-key")

def test_build_prompt_with_user_context(message_generator):
    context = {
        "user_name": "John",
        "preferences": {
            "topics": ["motivation", "growth"],
            "style": "casual"
        },
        "personal_info": {
            "occupation": "teacher",
            "hobbies": ["reading", "hiking"]
        }
    }
    
    prompt = message_generator._build_prompt(context)
    
    assert "occupation as teacher" in prompt
    assert "reading, hiking" in prompt
    assert "motivation, growth" in prompt

def test_build_system_message_with_user_context(message_generator):
    context = {
        "user_name": "Alice",
        "preferences": {
            "style": "professional"
        },
        "personal_info": {
            "interests": ["technology", "art"]
        }
    }
    
    system_message = message_generator._build_system_message(context)
    
    assert "Alice" in system_message
    assert "professional" in system_message
    assert "technology, art" in system_message

@patch('openai.OpenAI')
def test_generate_message_with_context(mock_openai, message_generator):
    mock_client = Mock()
    mock_chat = Mock()
    mock_completions = Mock()
    mock_response = Mock(
        id="chatcmpl-123456",
        object="chat.completion",
        created=1728933352,
        model="gpt-4-0125-preview",
        choices=[
            Mock(
                index=0,
                message=Mock(
                    role="assistant",
                    content="Test message",
                    refusal=None
                ),
                logprobs=None,
                finish_reason="stop"
            )
        ],
        usage=Mock(
            prompt_tokens=19,
            completion_tokens=10,
            total_tokens=29
        ),
        system_fingerprint="fp_6b68a8204b"
    )
    mock_completions.create = Mock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat
    message_generator.client = mock_client

    context = {
        "user_name": "Bob",
        "preferences": {"style": "casual"},
        "personal_info": {"hobbies": ["gaming"]}
    }
    
    message = message_generator.generate_message(context)
    
    assert message == "Test message"
    # Verify context was used in the API call
    call_args = mock_client.chat.completions.create.call_args[1]
    system_message = call_args['messages'][0]['content']
    assert "Bob" in system_message
    assert "casual" in system_message

@patch('openai.OpenAI')
def test_generate_response_with_context(mock_openai, message_generator):
    mock_client = Mock()
    mock_chat = Mock()
    mock_completions = Mock()
    mock_response = Mock(
        id="chatcmpl-123456",
        object="chat.completion",
        created=1728933352,
        model="gpt-4-0125-preview",
        choices=[
            Mock(
                index=0,
                message=Mock(
                    role="assistant",
                    content="Test response",
                    refusal=None
                ),
                logprobs=None,
                finish_reason="stop"
            )
        ],
        usage=Mock(
            prompt_tokens=19,
            completion_tokens=10,
            total_tokens=29
        ),
        system_fingerprint="fp_6b68a8204b"
    )
    mock_completions.create = Mock(return_value=mock_response)
    mock_chat.completions = mock_completions
    mock_client.chat = mock_chat
    message_generator.client = mock_client

    context = {
        "user_name": "Carol",
        "preferences": {"style": "friendly"}
    }
    
    response = message_generator.generate_response("Hello!", context)
    
    assert response == "Test response"
    # Verify context was used in the API call
    call_args = mock_client.chat.completions.create.call_args[1]
    system_message = call_args['messages'][0]['content']
    assert "Carol" in system_message
    assert "friendly" in system_message

def test_build_prompt_with_previous_messages(message_generator):
    context = {
        "previous_messages": [
            "Have a great day!",
            "Stay positive!"
        ]
    }
    
    prompt = message_generator._build_prompt(context)
    
    assert "Have a great day!" in prompt
    assert "Stay positive!" in prompt
    assert "different from these recent messages" in prompt

def test_build_prompt_without_context(message_generator):
    prompt = message_generator._build_prompt(None)
    
    assert "Generate a short" in prompt
    assert "160 characters" in prompt
    assert "uplifting message" in prompt

def test_validate_message_length(message_generator):
    long_message = "x" * 200
    cleaned = message_generator._validate_and_clean_message(long_message)
    
    assert len(cleaned) <= 160
    assert cleaned.endswith("...")

def test_fallback_message_on_empty_response(message_generator):
    message = message_generator._validate_and_clean_message("")
    
    assert message in message_generator.fallback_messages

def test_generate_message_with_empty_context(message_generator):
    context = {}
    prompt = message_generator._build_prompt(context)
    
    assert "Generate a short" in prompt
    assert "160 characters" in prompt
    assert "uplifting message" in prompt

def test_build_system_message_with_communication_style(message_generator):
    """Test that communication style is properly incorporated into system message."""
    context = {
        "preferences": {
            "communication_style": "casual"
        }
    }
    system_message = message_generator._build_system_message(context)
    assert "casual" in system_message.lower()
    
    context["preferences"]["communication_style"] = "professional"
    system_message = message_generator._build_system_message(context)
    assert "professional" in system_message.lower()

def test_build_system_message_with_empty_context(message_generator):
    context = {}
    system_message = message_generator._build_system_message(context)
    
    assert "positive, encouraging friend" in system_message
    assert len(system_message.split()) < 20  # Should be a simple message

def test_validate_and_clean_message_removes_quotes(message_generator):
    message = '"This is a test message"'
    cleaned = message_generator._validate_and_clean_message(message)
    
    assert cleaned == "This is a test message"
    assert '"' not in cleaned

def test_validate_and_clean_message_removes_extra_spaces(message_generator):
    message = "This   has   extra   spaces"
    cleaned = message_generator._validate_and_clean_message(message)
    
    assert cleaned == "This has extra spaces"
