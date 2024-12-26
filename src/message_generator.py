from openai import OpenAI
import random
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError
from typing import Optional, Dict, List, TypedDict
from .rate_limiter import rate_limit_openai

class UserContext(TypedDict, total=False):
    user_name: str
    preferences: Dict
    personal_info: Dict
    previous_messages: List[str]

class MessageGenerator:
    """Handles generation of positive messages using GPT-4."""
    
    def __init__(self, api_key: str):
        """Initialize with OpenAI API key."""
        self.client = OpenAI(api_key=api_key)
        self.fallback_messages = [
            "Believe in yourself! Every day is a new opportunity to shine.",
            "You are stronger than you know and braver than you believe.",
            "Today is full of endless possibilities. Make it amazing!",
            "Your potential is limitless. Keep pushing forward!",
            "You've got this! Today is your day to be awesome.",
        ]

    def generate_message(self, context: Optional[UserContext] = None) -> str:
        """
        Generate a positive message using GPT-4.
        Falls back to pre-written messages if generation fails.
        """
        try:
            return self._try_generate_message(context)
        except (Exception, RetryError) as e:
            print(f"Error generating message: {str(e)}")
            return self._get_fallback_message()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    @rate_limit_openai(estimated_tokens=200)  # Lower token estimate for gpt-4o-mini
    def _try_generate_message(self, context: Optional[UserContext] = None, stream: bool = False) -> str:
        """
        Internal method to attempt message generation with retries.
        
        Args:
            context: Optional user context for personalization
            stream: Whether to stream the response. If True, returns a generator.
        """
        # Construct the prompt with any context
        prompt = self._build_prompt(context)
        system_message = self._build_system_message(context)
        
        if stream:
            return self._stream_completion(system_message, prompt)
            
        completion = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.7,
            top_p=0.9,
            stream=False
        )
        
        message = completion.choices[0].message.content.strip()
        if not message:  # If message is empty after stripping
            raise ValueError("Empty message received from API")
            
        return self._validate_and_clean_message(message)

    def _stream_completion(self, system_message: str, prompt: str) -> str:
        """Stream the completion and accumulate the response."""
        stream = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7,
            top_p=0.9,
            stream=True
        )
        
        accumulated_message = []
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                accumulated_message.append(chunk.choices[0].delta.content)
                
        message = ''.join(accumulated_message).strip()
        if not message:
            raise ValueError("Empty message received from API")
            
        return self._validate_and_clean_message(message)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    @rate_limit_openai(estimated_tokens=150)  # Lower token estimate for gpt-4o-mini
    def generate_response(self, user_message: str, context: Optional[UserContext] = None, stream: bool = False) -> str:
        """Generate a response to a user's inbound message."""
        try:
            system_message = self._build_system_message(context)
            if stream:
                return self._stream_completion(
                    system_message,
                    f"Respond briefly and positively to this message: {user_message}"
                )
                
            completion = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": f"Respond briefly and positively to this message: {user_message}"}
                ],
                max_tokens=100,
                temperature=0.7,
                stream=False
            )
            
            message = completion.choices[0].message.content.strip()
            if not message:  # If message is empty after stripping
                raise ValueError("Empty message received from API")
                
            return self._validate_and_clean_message(message)
            
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return "Thank you for your message! Sending you positive vibes! 🌟"

    def _build_system_message(self, context: Optional[UserContext] = None) -> str:
        """Build the system message incorporating user context."""
        base_message = (
            "You are a positive, encouraging friend who sends uplifting messages. "
            "You have a great memory and adapt your communication style based on user preferences. "
            "You notice patterns in how users like to communicate - for example, if they often use French "
            "or prefer certain styles of communication. You remember these preferences and incorporate them "
            "naturally in your responses."
        )
        
        if not context:
            return base_message

        if context.get('user_name'):
            base_message += f" You're talking to {context['user_name']}."
            
        if context.get('preferences'):
            prefs = context['preferences']
            if 'communication_style' in prefs:
                base_message += f" Use a {prefs['communication_style']} communication style."
            if 'language' in prefs:
                base_message += f" Communicate in {prefs['language']}."
            if 'tone' in prefs:
                base_message += f" Use a {prefs['tone']} tone."
                
        if context.get('personal_info'):
            info = context['personal_info']
            if 'interests' in info:
                base_message += f" Reference their interests when relevant: {', '.join(info['interests'])}."
            if 'occupation' in info:
                base_message += f" Consider their work as {info['occupation']}."
            
        if context.get('previous_messages'):
            base_message += " Maintain consistency with previous interactions while staying fresh and engaging."
            
        return base_message

    def _build_prompt(self, context: Optional[UserContext] = None) -> str:
        """Build the prompt for message generation."""
        base_prompt = "Generate a short, unique, and uplifting message for today. "
        base_prompt += "Keep it under 160 characters, personal, and inspiring. "
        base_prompt += "Don't use hashtags or emojis."
        
        if not context:
            return base_prompt

        if context.get('personal_info'):
            info = context['personal_info']
            if 'occupation' in info:
                base_prompt += f" Consider their occupation as {info['occupation']}."
            if 'interests' in info:
                base_prompt += f" They enjoy: {', '.join(info['interests'])}."

        if context.get('preferences'):
            prefs = context['preferences']
            if 'communication_style' in prefs:
                base_prompt += f" Use a {prefs['communication_style']} tone."
            if 'message_time' in prefs:
                base_prompt += f" This message is for {prefs['message_time']} delivery."
        
        if context.get('previous_messages'):
            base_prompt += " Make it different from these recent messages: "
            base_prompt += str(context['previous_messages'])
            
        return base_prompt

    def _validate_and_clean_message(self, message: str) -> str:
        """Validate and clean the generated message."""
        if not message:
            return self._get_fallback_message()
            
        # Remove any newlines or extra spaces
        message = ' '.join(message.split())
        
        # Remove quotes if present
        message = message.strip('"').strip()
        
        # Ensure message isn't too long for SMS
        if len(message) > 160:
            message = message[:157] + "..."
            
        return message

    def _get_fallback_message(self) -> str:
        """Get a random fallback message."""
        return random.choice(self.fallback_messages)

    def add_fallback_message(self, message: str) -> None:
        """Add a new fallback message to the collection."""
        if message and len(message) <= 160:
            self.fallback_messages.append(message)

    def get_fallback_messages(self) -> List[str]:
        """Get the list of fallback messages."""
        return self.fallback_messages.copy()
