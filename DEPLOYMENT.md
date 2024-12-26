# Deployment Guide for Render.com

## Overview
This application uses Flask with APScheduler for message scheduling and Gunicorn for production deployment. The scheduler is integrated into the web process to ensure consistent message scheduling and delivery.

## Deployment Steps

1. Create a new Web Service on Render.com
   - Connect your GitHub repository
   - Select the branch to deploy

2. Configure Environment Variables
   Required environment variables:
   ```
   DATABASE_URL=postgresql://...
   OPENAI_API_KEY=your_openai_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_FROM_NUMBER=your_twilio_number
   FLASK_ENV=production
   GUNICORN_WORKERS=2
   GUNICORN_THREADS=4
   GUNICORN_TIMEOUT=30
   LOG_LEVEL=info
   ```

3. Build Settings
   - Build Command: Leave as default (Docker will handle this)
   - Start Command: Leave empty (Docker will handle this)

4. Advanced Settings
   - Instance Type: Recommend at least 512 MB RAM
   - Health Check Path: /health
   - Auto-Deploy: Enable

## Important Notes

1. Scheduler Configuration
   - The scheduler is integrated into the web process using Gunicorn's preload feature
   - Tasks are configured to run:
     - Daily message scheduling: Every day at midnight UTC
     - Schedule check: Every hour
     - Message processing: Every 5 minutes
     - Scheduler health check: Every 15 minutes

2. Database Considerations
   - Ensure your PostgreSQL database is properly configured
   - The application will automatically handle migrations on startup
   - Set appropriate connection pool settings in DATABASE_URL

3. Monitoring
   - Use Render's logs to monitor the application
   - The /health endpoint provides status of all components
   - Monitor the scheduler status through logs

## Troubleshooting

1. If messages aren't being scheduled:
   - Check the logs for any scheduler-related errors
   - Verify the scheduler is running via the /health endpoint
   - Ensure database connectivity is stable

2. If scheduled messages aren't being sent:
   - Check Twilio credentials and quota
   - Verify message processing logs
   - Check for any rate limiting issues

3. Common Issues:
   - Database connection timeouts: Adjust pool settings
   - Scheduler not running: Check Gunicorn worker configuration
   - Message processing delays: Monitor system resources

## Maintenance

1. Regular Tasks:
   - Monitor log output for any scheduling issues
   - Check message delivery success rates
   - Monitor database size and cleanup old records

2. Updates:
   - Test changes locally before deploying
   - Monitor logs after deployments
   - Use health checks to verify system status

## Support
For any deployment issues:
1. Check application logs in Render dashboard
2. Verify environment variables are correctly set
3. Ensure database connection is stable
4. Monitor scheduler health through the /health endpoint
