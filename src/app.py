from flask import Flask, request, jsonify
from flask_migrate import Migrate
from twilio.request_validator import RequestValidator
from flask_apscheduler import APScheduler
import logging
from logging.config import dictConfig
from datetime import datetime
import pytz
import os
import ssl
import certifi
import urllib3
from .rate_limiter import limiter

# Configure SSL for requests
urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()

def create_ssl_context():
    """Create a secure SSL context with system certificates."""
    context = ssl.create_default_context(cafile=certifi.where())
    context.verify_mode = ssl.CERT_REQUIRED
    context.check_hostname = True
    return context

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
scheduler = APScheduler()

# Initialize rate limiter
limiter.init_app(app)

# Configure SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/sms_app')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure APScheduler
app.config['SCHEDULER_API_ENABLED'] = False
app.config['SCHEDULER_TIMEZONE'] = 'UTC'

# Import models and initialize db
from .models import db, Recipient, UserConfig, MessageLog, ScheduledMessage

# Initialize app with SQLAlchemy and Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Import services after db initialization
from .message_generator import MessageGenerator
from .sms_service import SMSService
from .user_config_service import UserConfigService
from .onboarding_service import OnboardingService
from .scheduler import MessageScheduler

# Initialize services
message_generator = MessageGenerator(os.getenv('OPENAI_API_KEY'))
user_config_service = UserConfigService(db.session)
onboarding_service = OnboardingService(db.session, message_generator)

# Set up SSL context for Twilio requests
ssl_context = create_ssl_context()
urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()
urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context

# Configure Twilio client to use our SSL context
import twilio.http.http_client
twilio.http.http_client.CA_BUNDLE = certifi.where()

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

# Initialize message scheduler
message_scheduler = MessageScheduler(db.session, message_generator, sms_service, user_config_service)

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit exceeded errors."""
    app.logger.warning(f"Rate limit exceeded: {str(e)}")
    return jsonify({
        'error': 'Rate limit exceeded',
        'message': str(e),
        'retry_after': e.description
    }), 429

# Schedule background tasks
@scheduler.task('cron', id='schedule_messages', hour=0, minute=0)
def schedule_daily_messages():
    """Schedule messages for all active recipients."""
    with app.app_context():
        try:
            result = message_scheduler.schedule_daily_messages()
            app.logger.info(f"Daily message scheduling complete: {result}")
        except Exception as e:
            app.logger.error(f"Error in daily message scheduling: {str(e)}")

@scheduler.task('interval', id='process_messages', minutes=5)
def process_scheduled_messages():
    """Process scheduled messages that are due."""
    with app.app_context():
        try:
            result = message_scheduler.process_scheduled_messages()
            app.logger.info(f"Message processing complete: {result}")
        except Exception as e:
            app.logger.error(f"Error in message processing: {str(e)}")

@scheduler.task('cron', id='cleanup_records', hour=1, minute=0)
def cleanup_old_records():
    """Clean up old records daily."""
    with app.app_context():
        try:
            result = message_scheduler.cleanup_old_records()
            app.logger.info(f"Database cleanup complete: {result}")
        except Exception as e:
            app.logger.error(f"Error in database cleanup: {str(e)}")

def validate_twilio_request(f):
    """Decorator to validate incoming Twilio requests."""
    def decorated_function(*args, **kwargs):
        # Skip validation in debug mode
        if app.debug:
            app.logger.debug("Debug mode: Skipping Twilio request validation")
            return f(*args, **kwargs)

        validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
        
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
@limiter.limit("30/minute")  # Limit user config updates
def update_user_config():
    """Update user configuration."""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        recipient = Recipient.query.filter_by(phone_number=phone_number).first()
        
        if not recipient:
            return jsonify({'error': 'Recipient not found'}), 404

        config = user_config_service.create_or_update_config(
            recipient_id=recipient.id,
            name=data.get('name'),
            preferences=data.get('preferences'),
            personal_info=data.get('personal_info')
        )
        
        return jsonify({
            'message': 'Configuration updated successfully',
            'config': {
                'name': config.name,
                'preferences': config.preferences,
                'personal_info': config.personal_info
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error updating user config: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/inbound', methods=['POST'], endpoint='handle_inbound')
@validate_twilio_request
@limiter.limit("60/minute")  # Limit inbound messages
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
        
        if not sms_service.validate_phone_number(from_number):
            app.logger.error(f"Invalid phone number received: {from_number}")
            return jsonify({'error': 'Invalid phone number'}), 400
        
        recipient = Recipient.query.filter_by(phone_number=from_number).first()
        
        is_new_user = False
        if not recipient:
            app.logger.info(f"Creating new recipient for {from_number}")
            recipient = Recipient(
                phone_number=from_number,
                timezone='UTC',
                is_active=True
            )
            db.session.add(recipient)
            db.session.flush()
            is_new_user = True
        
        message_log = MessageLog(
            recipient_id=recipient.id,
            message_type='inbound',
            content=body,
            status='received'
        )
        db.session.add(message_log)
        
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
            
        elif upper_body == 'RESTART':
            app.logger.info(f"Processing RESTART command for {from_number}")
            response_text = onboarding_service.start_onboarding(recipient.id)
            app.logger.info(f"Restarted onboarding for user {recipient.id}")
            
        else:
            if is_new_user or not onboarding_service.is_onboarding_complete(recipient.id):
                app.logger.info(f"Handling onboarding for user {recipient.id}")
                if is_new_user or not onboarding_service.is_in_onboarding(recipient.id):
                    response_text = onboarding_service.start_onboarding(recipient.id)
                    app.logger.info(f"Started onboarding for user {recipient.id}")
                else:
                    response_text, is_complete = onboarding_service.process_response(recipient.id, body)
                    app.logger.info(f"Processed onboarding response for user {recipient.id}, complete: {is_complete}")
            else:
                app.logger.info(f"Processing regular message for user {recipient.id}")
                user_context = user_config_service.get_gpt_prompt_context(recipient.id)
                response_text = message_generator.generate_response(body, user_context)
            
        # Commit the inbound message log first
        db.session.commit()
        
        app.logger.info(f"Sending response: {response_text}")
        send_result = sms_service.send_message(from_number, response_text)
        
        # Create and commit outbound message log
        response_log = MessageLog(
            recipient_id=recipient.id,
            message_type='outbound',
            content=response_text,
            status=send_result.get('delivery_status', 'queued'),
            twilio_sid=send_result.get('message_sid'),
            error_message=send_result.get('error_message'),
            price=send_result.get('price'),
            price_unit=send_result.get('price_unit')
        )
        db.session.add(response_log)
        db.session.commit()
        return jsonify({'status': 'success'})
        
    except Exception as e:
        app.logger.error(f"Error handling inbound message: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/webhook/status', methods=['POST'], endpoint='handle_status')
@validate_twilio_request
@limiter.limit("120/minute")  # Higher limit for status callbacks
def handle_status_callback():
    """Handle SMS delivery status callbacks."""
    try:
        if not sms_service:
            raise ValueError("SMS service not properly initialized")

        app.logger.info("Received status callback")
        app.logger.debug(f"Status callback data: {request.form}")

        status_result = sms_service.process_delivery_status(request.form)
        
        if not status_result['processed']:
            app.logger.error(f"Failed to process status callback: {status_result.get('error')}")
            return jsonify({'error': 'Failed to process status'}), 400
        
        message_log = MessageLog.query.filter_by(
            twilio_sid=status_result['message_sid']
        ).first()
        
        if message_log:
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
@limiter.exempt  # No rate limit for health checks
def health_check():
    """Health check endpoint."""
    try:
        db.session.execute('SELECT 1')
        sms_service_status = "healthy" if sms_service else "unhealthy"
        scheduler_status = "healthy" if scheduler.running else "unhealthy"
        
        return jsonify({
            'status': 'healthy' if all([
                sms_service_status == "healthy",
                scheduler_status == "healthy"
            ]) else 'degraded',
            'components': {
                'database': 'healthy',
                'sms_service': sms_service_status,
                'scheduler': scheduler_status
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

def init_app():
    """Initialize the Flask application."""
    with app.app_context():
        # Initialize database
        db.create_all()
        
        # Start scheduler
        scheduler.init_app(app)
        scheduler.start()
        
        app.logger.info("Application initialized successfully")

if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
