from flask import Flask, request, jsonify
from flask_migrate import Migrate
from twilio.request_validator import RequestValidator
from flask_apscheduler import APScheduler
from asgiref.wsgi import WsgiToAsgi
import logging
from logging.config import dictConfig
from datetime import datetime
import pytz
import os
import ssl
import certifi
import urllib3
from src.features.rate_limiting.code import limiter

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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure APScheduler
app.config['SCHEDULER_API_ENABLED'] = False
app.config['SCHEDULER_TIMEZONE'] = 'UTC'

# Import models and initialize db
from src.features.core.code import db, Recipient, UserConfig, MessageLog, ScheduledMessage

# Initialize app with SQLAlchemy and Migrate
db.init_app(app)
migrate = Migrate(app, db)

# Import services after db initialization
from src.features.message_generation.code import MessageGenerator
from src.features.notification_system.code import SMSService
from src.features.user_management.code import UserConfigService, OnboardingService
from src.features.message_generation.scheduler import MessageScheduler
from src.features.preference_detection.code import PreferenceDetector
from src.features.notification_system.code import notification_manager

# Initialize services lazily to avoid interfering with migrations
message_generator = None
user_config_service = None
onboarding_service = None
sms_service = None
message_scheduler = None

def init_services():
    """Initialize all services. Called after database is ready."""
    global message_generator, user_config_service, onboarding_service, sms_service, message_scheduler
    
    if message_generator is None:
        # Log environment state
        app.logger.info("Checking environment configuration...")
        env_vars = {
            'TWILIO_ENABLED': os.getenv('TWILIO_ENABLED'),
            'OPENAI_API_KEY': bool(os.getenv('OPENAI_API_KEY')),
            'TWILIO_ACCOUNT_SID': bool(os.getenv('TWILIO_ACCOUNT_SID')),
            'TWILIO_AUTH_TOKEN': bool(os.getenv('TWILIO_AUTH_TOKEN')),
            'TWILIO_FROM_NUMBER': bool(os.getenv('TWILIO_FROM_NUMBER')),
            'FLASK_APP': os.getenv('FLASK_APP'),
            'FLASK_ENV': os.getenv('FLASK_ENV'),
            'FLASK_DEBUG': os.getenv('FLASK_DEBUG'),
            'DATABASE_URL': bool(os.getenv('DATABASE_URL'))
        }
        app.logger.info(f"Environment state: {env_vars}")
        
        # Check if Twilio is enabled (case-insensitive)
        twilio_enabled_raw = os.getenv('TWILIO_ENABLED', 'false')
        app.logger.info(f"Raw TWILIO_ENABLED value: {twilio_enabled_raw}")
        app.logger.info(f"Environment keys: {[k for k in os.environ.keys() if 'TWILIO' in k.upper()]}")
        app.logger.info("Twilio environment variables:")
        for key in ['TWILIO_ENABLED', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM_NUMBER']:
            value = os.getenv(key)
            if key in ['TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN']:
                app.logger.info(f"{key}: {'SET' if value else 'NOT SET'}")
            else:
                app.logger.info(f"{key}: {value}")
        
        # Force enable Twilio for testing
        twilio_enabled = True
        app.logger.info("Forcing Twilio enabled for testing")
        
        if not twilio_enabled:
            app.logger.info("Twilio is disabled - skipping SMS service initialization")
            return
            
        # Check required environment variables
        required_vars = {
            'OPENAI_API_KEY': os.getenv('OPENAI_API_KEY'),
            'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
            'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
            'TWILIO_FROM_NUMBER': os.getenv('TWILIO_FROM_NUMBER')
        }
        
        # Log each variable's presence (without exposing values)
        for var_name, value in required_vars.items():
            if value:
                app.logger.info(f"{var_name} is set")
                if var_name == 'TWILIO_ACCOUNT_SID':
                    app.logger.info(f"TWILIO_ACCOUNT_SID starts with: {value[:6]}...")
                elif var_name == 'TWILIO_FROM_NUMBER':
                    app.logger.info(f"TWILIO_FROM_NUMBER is: {value}")
            else:
                app.logger.error(f"{var_name} is not set")
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            app.logger.error(f"Missing required variables: {', '.join(missing_vars)}")
            app.logger.error("Please configure all required environment variables in Render")
            app.logger.error("Current environment state:")
            for key in os.environ:
                if not any(secret in key.lower() for secret in ['key', 'token', 'secret', 'password']):
                    app.logger.error(f"{key}: {os.getenv(key)}")
            return

        try:
            message_generator = MessageGenerator(required_vars['OPENAI_API_KEY'])
            user_config_service = UserConfigService(db.session)
            onboarding_service = OnboardingService(db.session, message_generator)

            # Set up SSL context for Twilio requests
            ssl_context = create_ssl_context()
            urllib3.util.ssl_.DEFAULT_CERTS = certifi.where()
            urllib3.util.ssl_.SSL_CONTEXT_FACTORY = lambda: ssl_context

            # Configure Twilio client to use our SSL context
            import twilio.http.http_client
            twilio.http.http_client.CA_BUNDLE = certifi.where()

            # Initialize SMS service with detailed error handling
            try:
                app.logger.info("Initializing SMS service...")
                app.logger.info(f"Using TWILIO_FROM_NUMBER: {required_vars['TWILIO_FROM_NUMBER']}")
                app.logger.info(f"Using TWILIO_ACCOUNT_SID: {required_vars['TWILIO_ACCOUNT_SID'][:6]}...")
                
                # Initialize SMS service through notification system
                from src.features.notification_system.code import init_sms_service
                if init_sms_service():
                    app.logger.info("SMS service initialized successfully through notification system")
                    global sms_service
                    sms_service = notification_manager.sms_service
                    app.logger.info(f"Global sms_service set: {sms_service is not None}")
                    
                    # Test SMS service initialization
                    account = sms_service.client.api.accounts(required_vars['TWILIO_ACCOUNT_SID']).fetch()
                    app.logger.info(f"Twilio account status: {account.status}")
                else:
                    app.logger.error("Failed to initialize SMS service through notification system")
                    sms_service = None
                
            except Exception as e:
                app.logger.error(f"Failed to initialize SMS service: {str(e)}")
                app.logger.error("SMS functionality will be disabled")
                sms_service = None

            # Initialize message scheduler
            message_scheduler = MessageScheduler(db.session, message_generator, sms_service, user_config_service)
            app.logger.info("Message scheduler initialized successfully")
            app.logger.info("All services initialized successfully")
        except Exception as e:
            app.logger.error(f"Error initializing services: {str(e)}")
            app.logger.warning("Services will be initialized in limited mode")

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
@scheduler.task('interval', id='schedule_messages', minutes=5)  # Run every 5 minutes
def schedule_daily_messages():
    """Schedule messages for all active recipients."""
    with app.app_context():
        try:
            # Get count of pending messages for next 24 hours
            next_day = datetime.now(pytz.UTC) + timedelta(days=1)
            pending_count = ScheduledMessage.query.filter(
                ScheduledMessage.status == 'pending',
                ScheduledMessage.scheduled_time <= next_day
            ).count()
            
            # Only schedule if we have less than expected messages
            if pending_count < 10:  # Arbitrary threshold, adjust based on user count
                app.logger.info("Low pending message count, running scheduler")
                result = message_scheduler.schedule_daily_messages()
                app.logger.info(f"Daily message scheduling complete: {result}")
            else:
                app.logger.info(f"Found {pending_count} pending messages, skipping scheduling")
                
        except Exception as e:
            app.logger.error(f"Error in daily message scheduling: {str(e)}")

@scheduler.task('interval', id='process_messages', minutes=1)  # Check every minute
def process_scheduled_messages():
    """Process scheduled messages that are due."""
    with app.app_context():
        try:
            current_time = datetime.now(pytz.UTC)
            
            # Get count of messages due in the next minute
            next_minute = current_time + timedelta(minutes=1)
            pending_count = ScheduledMessage.query.filter(
                ScheduledMessage.status == 'pending',
                ScheduledMessage.scheduled_time <= next_minute
            ).count()
            
            if pending_count > 0:
                app.logger.info(f"Found {pending_count} messages to process")
                result = message_scheduler.process_scheduled_messages()
                app.logger.info(f"Message processing complete: {result}")
                
                # Log any failures
                if result['failed'] > 0:
                    failed_messages = ScheduledMessage.query.filter_by(status='failed').all()
                    for msg in failed_messages:
                        app.logger.error(f"Failed message {msg.id} for recipient {msg.recipient_id}: {msg.error_message}")
                        
        except Exception as e:
            app.logger.error(f"Error in message processing: {str(e)}")

@scheduler.task('cron', id='cleanup_records', hour=3, minute=0)  # Run at 3 AM
def cleanup_old_records():
    """Clean up old records daily."""
    with app.app_context():
        try:
            result = message_scheduler.cleanup_old_records()
            app.logger.info(f"Database cleanup complete: {result}")
        except Exception as e:
            app.logger.error(f"Error in database cleanup: {str(e)}")

# Add periodic scheduler check
@scheduler.task('interval', id='check_scheduler', minutes=15)
def check_scheduler():
    """Periodically verify scheduler is running."""
    with app.app_context():
        try:
            if not scheduler.running:
                app.logger.warning("Scheduler not running, attempting to restart...")
                scheduler.start()
                if scheduler.running:
                    app.logger.info("Successfully restarted scheduler")
                    jobs = scheduler.get_jobs()
                    for job in jobs:
                        app.logger.info(f"Active job: {job.id} - Next run: {job.next_run_time}")
                else:
                    app.logger.error("Failed to restart scheduler")
        except Exception as e:
            app.logger.error(f"Error checking scheduler: {str(e)}")

def validate_twilio_request(f):
    """Decorator to validate incoming Twilio requests."""
    def decorated_function(*args, **kwargs):
        # Skip validation in debug mode
        if app.debug:
            app.logger.debug("Debug mode: Skipping Twilio request validation")
            return f(*args, **kwargs)

        validator = RequestValidator(os.getenv('TWILIO_AUTH_TOKEN'))
        
        # Construct the full URL that Twilio would have signed
        if request.headers.get('X-Forwarded-Proto'):
            url = f"{request.headers.get('X-Forwarded-Proto')}://{request.headers.get('Host')}{request.path}"
        else:
            url = request.url

        app.logger.info(f"Validating Twilio request for URL: {url}")
        app.logger.debug(f"Request headers: {dict(request.headers)}")
        app.logger.debug(f"Request form data: {dict(request.form)}")
        
        request_valid = validator.validate(
            url,
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
async def handle_inbound_message():
    """Handle incoming SMS messages."""
    try:
        app.logger.info("Received inbound message")
        
        if not sms_service:
            app.logger.warning("SMS service not initialized - environment variables may not be configured")
            return jsonify({
                'error': 'Service unavailable',
                'message': 'The messaging service is currently being configured. Please try again later.'
            }), 503

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
            
            # Send notification for new signup
            try:
                await notification_manager.handle_user_signup(str(recipient.id))
            except Exception as e:
                app.logger.error(f"Failed to send signup notification: {str(e)}")
        
        # Initialize preference detector
        preference_detector = PreferenceDetector(db.session)
        
        # Analyze message for preferences
        detected_prefs = preference_detector.analyze_message(body, recipient.id)
        if detected_prefs:
            app.logger.info(f"Detected preferences for user {recipient.id}: {detected_prefs}")
        
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
                # Get user context including detected preferences
                user_context = user_config_service.get_gpt_prompt_context(recipient.id)
                if detected_prefs:
                    user_context['preferences'] = {
                        **(user_context.get('preferences', {})),
                        **detected_prefs
                    }
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
        
        # Send notification for message receipt
        try:
            await notification_manager.handle_message_receipt(str(recipient.id), str(response_log.id))
        except Exception as e:
            app.logger.error(f"Failed to send message receipt notification: {str(e)}")
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
        app.logger.info("Received status callback")
        
        if not sms_service:
            app.logger.warning("SMS service not initialized - environment variables may not be configured")
            return jsonify({
                'error': 'Service unavailable',
                'message': 'The messaging service is currently being configured. Please try again later.'
            }), 503

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

def ensure_scheduler_running():
    """Ensure the scheduler is running and restart if needed."""
    if not scheduler.running:
        app.logger.warning("Scheduler not running, attempting to start...")
        try:
            scheduler.start()
            if scheduler.running:
                app.logger.info("Successfully restarted scheduler")
                jobs = scheduler.get_jobs()
                for job in jobs:
                    app.logger.info(f"Active job: {job.id} - Next run: {job.next_run_time}")
            else:
                app.logger.error("Failed to restart scheduler")
        except Exception as e:
            app.logger.error(f"Error starting scheduler: {str(e)}")

def init_app():
    """Initialize the Flask application."""
    with app.app_context():
        try:
            # Initialize database
            db.create_all()
            
            # Initialize services
            init_services()
            
            # Initialize and start scheduler only if not in migration
            if not os.getenv('FLASK_DB_MIGRATE'):
                scheduler.init_app(app)
                scheduler.start()
                
                # Verify scheduler is running
                if scheduler.running:
                    app.logger.info("Scheduler started successfully")
                    jobs = scheduler.get_jobs()
                    for job in jobs:
                        app.logger.info(f"Scheduled job: {job.id} - Next run: {job.next_run_time}")
                else:
                    app.logger.error("Failed to start scheduler")
                    
                # Add periodic scheduler check
                @scheduler.task('interval', id='check_scheduler', minutes=15)
                def check_scheduler():
                    """Periodically verify scheduler is running."""
                    ensure_scheduler_running()
            
            app.logger.info("Application initialized successfully")
            
        except Exception as e:
            app.logger.error(f"Error during application initialization: {str(e)}")
            raise

# Convert WSGI app to ASGI
asgi_app = WsgiToAsgi(app)

if __name__ == '__main__':
    init_app()
    import hypercorn.asyncio
    import asyncio
    
    config = hypercorn.Config()
    config.bind = [f"0.0.0.0:{int(os.getenv('PORT', 5000))}"]
    
    asyncio.run(hypercorn.asyncio.serve(asgi_app, config))
