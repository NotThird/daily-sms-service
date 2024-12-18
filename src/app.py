from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from twilio.request_validator import RequestValidator
from twilio.twiml.messaging_response import MessagingResponse
import logging
from logging.config import dictConfig
from datetime import datetime
import pytz
import os

# Configure logging
dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
        }
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = Flask(__name__)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/sms_app')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy()

# Import models after db initialization
from .models import Base, Recipient, UserConfig, MessageLog
from .message_generator import MessageGenerator
from .sms_service import SMSService
from .user_config_service import UserConfigService
from .onboarding_service import OnboardingService

# Initialize app with SQLAlchemy
db.init_app(app)
migrate = Migrate(app, db)

# Initialize services
message_generator = MessageGenerator(os.getenv('OPENAI_API_KEY'))
user_config_service = UserConfigService(db.session)
onboarding_service = OnboardingService(db.session)

try:
    sms_service = SMSService(
        os.getenv('TWILIO_ACCOUNT_SID'),
        os.getenv('TWILIO_AUTH_TOKEN'),
        os.getenv('TWILIO_FROM_NUMBER')
    )
    app.logger.info("SMS service initialized successfully")
except ValueError as e:
    app.logger.error(f"Failed to initialize SMS service: {str(e)}")
    sms_service = None

def validate_twilio_request(f):
    """Decorator to validate incoming Twilio requests."""
    def decorated_function(*args, **kwargs):
        # Skip validation in debug mode
        if app.debug:
            app.logger.debug("Debug mode: Skipping Twilio request validation")
            return f(*args, **kwargs)

        validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
        
        # Get the request URL and POST data
        request_valid = validator.validate(
            request.url,
            request.form,
            request.headers.get('X-Twilio-Signature', '')
        )
        
        if request_valid:
            return f(*args, **kwargs)
        else:
            app.logger.warning("Invalid Twilio request signature")
            return jsonify({'error': 'Invalid request signature'}), 403
            
    return decorated_function

@app.route('/api/user-config', methods=['POST'])
def update_user_config():
    """Update user configuration."""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        # Get recipient
        recipient = Recipient.query.filter_by(phone_number=phone_number).first()
        
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404

        # Update user config
        config = user_config_service.create_or_update_config(
            recipient_id=recipient.id,
            name=data.get('name'),
            email=data.get('email'),
            preferences=data.get('preferences'),
            personal_info=data.get('personal_info')
        )
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'config': {
                'name': config.name,
                'email': config.email,
                'preferences': config.preferences,
                'personal_info': config.personal_info
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error updating user config: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/inbound', methods=['POST'], endpoint='handle_inbound')
@validate_twilio_request
def handle_inbound_message():
    """Handle incoming SMS messages."""
    try:
        if not sms_service:
            raise ValueError("SMS service not properly initialized")

        app.logger.info("Received inbound message")
        app.logger.debug(f"Request form data: {request.form}")

        from_number = request.form['From']
        body = request.form['Body'].strip()
        upper_body = body.upper()
        
        # Validate phone number
        if not sms_service.validate_phone_number(from_number):
            app.logger.error(f"Invalid phone number received: {from_number}")
            return jsonify({'error': 'Invalid phone number'}), 400
        
        # Get or create recipient
        recipient = Recipient.query.filter_by(phone_number=from_number).first()
        
        is_new_user = False
        if not recipient:
            app.logger.info(f"Creating new recipient for {from_number}")
            # New recipient
            recipient = Recipient(
                phone_number=from_number,
                timezone='UTC',  # Default timezone
                is_active=True
            )
            db.session.add(recipient)
            db.session.flush()  # Get the ID without committing
            is_new_user = True
        
        # Log the inbound message
        message_log = MessageLog(
            recipient_id=recipient.id,
            message_type='inbound',
            content=body,
            status='received'
        )
        db.session.add(message_log)
        
        # Handle commands
        resp = MessagingResponse()
        if upper_body == 'STOP':
            app.logger.info(f"Processing STOP command for {from_number}")
            recipient.is_active = False
            sms_service.handle_opt_out(from_number)
            response_text = "You've been unsubscribed from daily messages. Text START to resubscribe."
            
        elif upper_body == 'START':
            app.logger.info(f"Processing START command for {from_number}")
            recipient.is_active = True
            sms_service.handle_opt_in(from_number)
            response_text = "Welcome back! You'll start receiving daily positive messages again."
            
        else:
            # Check if user needs onboarding
            if is_new_user or not onboarding_service.is_onboarding_complete(recipient.id):
                app.logger.info(f"Handling onboarding for user {recipient.id}")
                # Handle onboarding flow
                if is_new_user or not onboarding_service.is_in_onboarding(recipient.id):
                    # Start onboarding for new users
                    response_text = onboarding_service.start_onboarding(recipient.id)
                    app.logger.info(f"Started onboarding for user {recipient.id}")
                else:
                    # Process onboarding response
                    response_text, is_complete = onboarding_service.process_response(recipient.id, body)
                    app.logger.info(f"Processed onboarding response for user {recipient.id}, complete: {is_complete}")
            else:
                app.logger.info(f"Processing regular message for user {recipient.id}")
                # Regular message handling for onboarded users
                user_context = user_config_service.get_gpt_prompt_context(recipient.id)
                response_text = message_generator.generate_response(body, user_context)
            
        # Send and log the response
        app.logger.info(f"Sending response: {response_text}")
        resp.message(response_text)
        send_result = sms_service.send_message(from_number, response_text)
        
        response_log = MessageLog(
            recipient_id=recipient.id,
            message_type='outbound',
            content=response_text,
            status=send_result['delivery_status'],
            twilio_sid=send_result.get('message_sid'),
            error_message=send_result.get('error_message'),
            price=send_result.get('price'),
            price_unit=send_result.get('price_unit')
        )
        db.session.add(response_log)
        
        db.session.commit()
        return str(resp)
        
    except Exception as e:
        app.logger.error(f"Error handling inbound message: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/status', methods=['POST'], endpoint='handle_status')
@validate_twilio_request
def handle_status_callback():
    """Handle SMS delivery status callbacks."""
    try:
        if not sms_service:
            raise ValueError("SMS service not properly initialized")

        app.logger.info("Received status callback")
        app.logger.debug(f"Status callback data: {request.form}")

        # Process the status update
        status_result = sms_service.process_delivery_status(request.form)
        
        if not status_result['processed']:
            app.logger.error(f"Failed to process status callback: {status_result.get('error')}")
            return jsonify({'error': 'Failed to process status'}), 400
        
        # Update message log
        message_log = MessageLog.query.filter_by(
            twilio_sid=status_result['message_sid']
        ).first()
        
        if message_log:
            # Get detailed message status
            status_details = sms_service.get_message_status(status_result['message_sid'])
            
            message_log.status = status_details['status']
            message_log.error_message = status_details.get('error_message')
            message_log.price = status_details.get('price')
            message_log.price_unit = status_details.get('price_unit')
            
            db.session.commit()
            app.logger.info(f"Updated message status: {status_details['status']} for SID: {status_result['message_sid']}")
        else:
            app.logger.warning(f"Message log not found for SID: {status_result['message_sid']}")
        
        return jsonify({'status': 'success'})
        
    except Exception as e:
        app.logger.error(f"Error handling status callback: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/health', methods=['GET'], endpoint='health_check')
def health_check():
    """Health check endpoint."""
    try:
        # Test database connection
        db.session.execute('SELECT 1')
        
        # Test SMS service
        sms_service_status = "healthy" if sms_service else "unhealthy"
        
        return jsonify({
            'status': 'healthy' if sms_service_status == "healthy" else 'degraded',
            'components': {
                'database': 'healthy',
                'sms_service': sms_service_status
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
