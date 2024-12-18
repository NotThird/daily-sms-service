# Deployment Guide (Render) - Minimal Cost Version

This guide provides instructions for deploying the Daily Positivity SMS Service using Render's free and minimal paid tiers.

## Prerequisites

1. [Render Account](https://render.com) (sign up if needed)
2. OpenAI API key
3. Twilio account with:
   - Account SID
   - Auth Token
   - Phone number
4. GitHub repository with your code

## Cost-Effective Infrastructure Setup

### 1. Database Setup (Free Tier)

1. Log into Render Dashboard
2. Go to "New +" > "PostgreSQL"
3. Configure the database:
   - Name: `daily-positivity-db`
   - Database: `daily_positivity`
   - User: (auto-generated)
   - Region: Choose nearest to your users
   - Instance Type: "Free" ($0/month)
   - Storage: 1GB included
4. Click "Create Database"
5. Note the internal database URL

Note: Free tier limitations
- 90-day lifetime (can recreate)
- Automatic pause after 1 hour of inactivity
- Restarts on first connection
- These limitations are acceptable for a gift service

### 2. Combined Web Service Setup

Instead of separate workers, we'll use background tasks within the web service.

1. Go to "New +" > "Web Service"
2. Connect your GitHub repository
3. Configure the service:
   - Name: `daily-positivity`
   - Environment: "Docker"
   - Region: Same as database
   - Instance Type: "Starter" ($7/month)
   - Branch: `main`
   - Build Command: (leave empty, handled by Dockerfile)
   - Start Command: `./docker-entrypoint.sh web`

4. Add Environment Variables:
   ```
   FLASK_ENV=production
   FLASK_DEBUG=0
   DATABASE_URL=postgres://... (Internal Database URL from step 1)
   OPENAI_API_KEY=your_openai_api_key
   TWILIO_ACCOUNT_SID=your_twilio_sid
   TWILIO_AUTH_TOKEN=your_twilio_token
   TWILIO_FROM_NUMBER=your_twilio_number
   TWILIO_STATUS_CALLBACK_URL=https://daily-positivity.onrender.com/webhook/status
   LOG_LEVEL=INFO
   DEFAULT_TIMEZONE=UTC
   MESSAGE_WINDOW_START=12
   MESSAGE_WINDOW_END=17
   ```

5. Click "Create Web Service"

## Twilio Configuration

1. Log into [Twilio Console](https://console.twilio.com)
2. Navigate to your phone number settings
3. Update webhook URLs:
   - Messaging webhook: `https://daily-positivity.onrender.com/webhook/inbound`
   - Status callback: `https://daily-positivity.onrender.com/webhook/status`
4. Save changes

## Cost Breakdown

Minimal costs:
- PostgreSQL (Free Tier): $0/month
- Web Service (Starter): $7/month
Total: $7/month

Additional costs to consider:
- OpenAI API usage (pay as you go)
- Twilio message costs (pay as you go)

## Monitoring

### 1. Render Dashboard
- Monitor service health
- View logs
- Track resource usage

### 2. Database Management
Free tier considerations:
- Backup your data periodically (no automatic backups on free tier)
- Service pauses after 1 hour of inactivity
- Will restart automatically on first connection

## Troubleshooting

### Common Issues

1. Database Connection Issues
   - Remember free tier database pauses after 1 hour
   - First connection will take a few seconds to wake up
   - Check service logs for connection errors

2. Webhook Failures
   - Verify Twilio webhook URLs
   - Check web service logs
   - Ensure web service is running

3. Message Scheduling Issues
   - Check web service logs
   - Verify environment variables
   - Check database connectivity

## Maintenance

### Regular Tasks

1. Monitor logs for errors
2. Check database usage (stay within 1GB limit)
3. Every 90 days:
   - Export database data
   - Create new database instance
   - Import data
   - Update DATABASE_URL in web service

## Deployment Checklist

Before going live:
1. [ ] Database created (free tier)
2. [ ] Web service deployed (starter tier)
3. [ ] Environment variables set
4. [ ] Twilio webhooks configured
5. [ ] Test message flow end-to-end
6. [ ] Document production URLs
7. [ ] Set calendar reminder for 90-day database renewal

## Cost Optimization Tips

1. Monitor OpenAI API usage
2. Keep database size small
3. Clean up old messages regularly
4. Use efficient queries
5. Implement rate limiting if needed
