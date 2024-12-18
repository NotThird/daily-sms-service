import os
import logging
from dotenv import load_dotenv
from src.message_generator import MessageGenerator
from src.sms_service import SMSService

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def verify_env_vars():
    """Verify all required environment variables are set correctly."""
    required_vars = {
        'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
        'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
        'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
        'TWILIO_FROM_NUMBER': os.getenv('TWILIO_FROM_NUMBER'),
        'DEVELOPMENT_TEST_NUMBER': os.getenv('DEVELOPMENT_TEST_NUMBER')
    }
    
    missing_vars = [k for k, v in required_vars.items() if not v]
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
    logger.info("Environment variables verified successfully")
    return required_vars

def test_complete_flow():
    # Load environment variables
    load_dotenv(override=True)
    
    try:
        # Verify environment variables
        env_vars = verify_env_vars()
        
        # Initialize message generator
        logger.info("Initializing message generator...")
        message_generator = MessageGenerator(env_vars['OPENAI_API_KEY'])
        
        # Initialize SMS service
        logger.info("Initializing SMS service...")
        sms_service = SMSService(
            env_vars['TWILIO_ACCOUNT_SID'],
            env_vars['TWILIO_AUTH_TOKEN'],
            env_vars['TWILIO_FROM_NUMBER']
        )
        
        # Generate message
        logger.info("Generating message...")
        try:
            message = message_generator.generate_message()
            logger.info(f"Generated message: {message}")
        except Exception as e:
            logger.error(f"Error generating message: {str(e)}", exc_info=True)
            raise
        
        # Send SMS
        logger.info("Sending SMS...")
        try:
            result = sms_service.send_message(env_vars['DEVELOPMENT_TEST_NUMBER'], message)
            logger.info("SMS sent successfully")
            
            # Print result
            logger.info("Result:")
            for key, value in result.items():
                logger.info(f"{key}: {value}")
                
        except Exception as e:
            logger.error(f"Error sending SMS: {str(e)}", exc_info=True)
            raise
            
    except Exception as e:
        logger.error(f"Test failed: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    try:
        test_complete_flow()
        logger.info("Test completed successfully")
    except Exception as e:
        logger.error("Test failed", exc_info=True)
        exit(1)
