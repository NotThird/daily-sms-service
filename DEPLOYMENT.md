# Deployment Guide

This guide provides step-by-step instructions for deploying the Daily Positivity SMS Service to production using AWS services.

## Prerequisites

1. AWS Account with appropriate permissions
2. OpenAI API key
3. Twilio account with:
   - Account SID
   - Auth Token
   - Phone number
4. Domain name for webhook endpoints
5. GitHub account for CI/CD

## Infrastructure Setup

### 1. Database (AWS RDS)

1. Create a PostgreSQL database:
   ```bash
   # Using AWS CLI
   aws rds create-db-instance \
     --db-instance-identifier daily-positivity \
     --db-instance-class db.t3.micro \
     --engine postgres \
     --master-username dbadmin \
     --master-user-password <your-password> \
     --allocated-storage 20
   ```

2. Note the database endpoint URL for configuration

### 2. Secrets Management (AWS Secrets Manager)

1. Create a secret for application credentials:
   ```bash
   aws secretsmanager create-secret \
     --name daily-positivity/prod \
     --description "Production credentials" \
     --secret-string '{
       "DATABASE_URL": "postgresql://dbadmin:<password>@<endpoint>:5432/daily_positivity",
       "OPENAI_API_KEY": "your-openai-key",
       "TWILIO_ACCOUNT_SID": "your-twilio-sid",
       "TWILIO_AUTH_TOKEN": "your-twilio-token",
       "TWILIO_FROM_NUMBER": "your-twilio-number"
     }'
   ```

### 3. Container Registry (AWS ECR)

1. Create repository:
   ```bash
   aws ecr create-repository \
     --repository-name daily-positivity \
     --image-scanning-configuration scanOnPush=true
   ```

2. Note the repository URI

### 4. Application Hosting (AWS ECS Fargate)

1. Create ECS cluster:
   ```bash
   aws ecs create-cluster --cluster-name daily-positivity
   ```

2. Create task definition (save as task-definition.json):
   ```json
   {
     "family": "daily-positivity",
     "networkMode": "awsvpc",
     "requiresCompatibilities": ["FARGATE"],
     "cpu": "256",
     "memory": "512",
     "containerDefinitions": [
       {
         "name": "web",
         "image": "<ecr-repo-uri>:latest",
         "portMappings": [
           {
             "containerPort": 5000,
             "protocol": "tcp"
           }
         ],
         "logConfiguration": {
           "logDriver": "awslogs",
           "options": {
             "awslogs-group": "/ecs/daily-positivity",
             "awslogs-region": "us-east-1",
             "awslogs-stream-prefix": "web"
           }
         }
       }
     ]
   }
   ```

3. Register task definition:
   ```bash
   aws ecs register-task-definition --cli-input-json file://task-definition.json
   ```

### 5. Load Balancer and HTTPS (AWS ALB)

1. Create Application Load Balancer
2. Configure HTTPS listener with SSL certificate
3. Create target group for ECS service

### 6. DNS Configuration

1. Create Route 53 hosted zone for your domain
2. Create A record pointing to ALB
3. Obtain SSL certificate through ACM

## CI/CD Setup (GitHub Actions)

1. Create `.github/workflows/deploy.yml`:
   ```yaml
   name: Deploy to Production

   on:
     push:
       branches: [main]

   jobs:
     deploy:
       runs-on: ubuntu-latest
       
       steps:
         - uses: actions/checkout@v2
         
         - name: Configure AWS credentials
           uses: aws-actions/configure-aws-credentials@v1
           with:
             aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
             aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
             aws-region: us-east-1
             
         - name: Login to Amazon ECR
           id: login-ecr
           uses: aws-actions/amazon-ecr-login@v1
           
         - name: Build and push image
           env:
             ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
             ECR_REPOSITORY: daily-positivity
             IMAGE_TAG: ${{ github.sha }}
           run: |
             docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
             docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
             
         - name: Update ECS service
           run: |
             aws ecs update-service \
               --cluster daily-positivity \
               --service web \
               --force-new-deployment
   ```

2. Add GitHub repository secrets:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY

## Application Configuration

### 1. Environment Variables

Set these in your ECS task definition:
```json
{
  "environment": [
    {
      "name": "FLASK_ENV",
      "value": "production"
    },
    {
      "name": "AWS_SECRETS_ARN",
      "value": "arn:aws:secretsmanager:region:account:secret:daily-positivity/prod"
    }
  ]
}
```

### 2. Twilio Webhook Configuration

1. Log into Twilio Console
2. Configure webhook URLs:
   - Messaging webhook: `https://your-domain.com/webhook/inbound`
   - Status callback: `https://your-domain.com/webhook/status`
3. Ensure webhooks use HTTPS

## Scheduler Setup (AWS EventBridge)

1. Create rules for scheduling:
   ```bash
   # Daily scheduling rule (runs at 11 AM UTC)
   aws events put-rule \
     --name daily-positivity-scheduler \
     --schedule-expression "cron(0 11 * * ? *)" \
     --state ENABLED

   # Message processing rule (runs every 5 minutes)
   aws events put-rule \
     --name daily-positivity-processor \
     --schedule-expression "rate(5 minutes)" \
     --state ENABLED
   ```

2. Create ECS tasks for scheduler:
   ```bash
   # Task definition for scheduler
   aws ecs register-task-definition \
     --family daily-positivity-scheduler \
     --container-definitions '[{
       "name": "scheduler",
       "image": "<ecr-repo-uri>:latest",
       "command": ["python", "-m", "src.cli", "schedule_messages"],
       "logConfiguration": {
         "logDriver": "awslogs",
         "options": {
           "awslogs-group": "/ecs/daily-positivity",
           "awslogs-region": "us-east-1",
           "awslogs-stream-prefix": "scheduler"
         }
       }
     }]'
   ```

## Monitoring and Logging

### 1. CloudWatch Logs

1. Create log group:
   ```bash
   aws logs create-log-group --log-group-name /ecs/daily-positivity
   ```

2. Create log streams for different components:
   ```bash
   aws logs create-log-stream \
     --log-group-name /ecs/daily-positivity \
     --log-stream-name web

   aws logs create-log-stream \
     --log-group-name /ecs/daily-positivity \
     --log-stream-name scheduler
   ```

### 2. CloudWatch Alarms

1. Create alarm for failed messages:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name daily-positivity-failed-messages \
     --metric-name FailedMessages \
     --namespace DailyPositivity \
     --statistic Sum \
     --period 300 \
     --evaluation-periods 1 \
     --threshold 5 \
     --comparison-operator GreaterThanThreshold \
     --alarm-actions <your-sns-topic-arn>
   ```

## Testing Deployment

1. Deploy initial version:
   ```bash
   git push origin main
   ```

2. Run database migrations:
   ```bash
   aws ecs run-task \
     --cluster daily-positivity \
     --task-definition daily-positivity \
     --overrides '{
       "containerOverrides": [{
         "name": "web",
         "command": ["poetry", "run", "alembic", "upgrade", "head"]
       }]
     }'
   ```

3. Test webhook endpoints:
   ```bash
   curl -X POST https://your-domain.com/health
   ```

4. Send test message:
   ```bash
   aws ecs run-task \
     --cluster daily-positivity \
     --task-definition daily-positivity \
     --overrides '{
       "containerOverrides": [{
         "name": "web",
         "command": ["python", "-m", "src.cli", "test_message", "+1234567890", "Test message"]
       }]
     }'
   ```

## Maintenance

### 1. Database Backups

RDS automatically handles daily backups. Additional manual snapshots:
```bash
aws rds create-db-snapshot \
  --db-instance-identifier daily-positivity \
  --db-snapshot-identifier daily-positivity-manual-1
```

### 2. Log Rotation

CloudWatch Logs automatically handles log rotation. Set retention period:
```bash
aws logs put-retention-policy \
  --log-group-name /ecs/daily-positivity \
  --retention-in-days 30
```

### 3. Monitoring Costs

1. Set up AWS Budget alerts
2. Monitor OpenAI API usage
3. Track Twilio message costs

### 4. Scaling

To scale the application:
1. Adjust ECS service desired count
2. Modify RDS instance class if needed
3. Adjust task CPU/memory allocation

## Troubleshooting

### Common Issues

1. Database Connection Issues
   - Check security group rules
   - Verify credentials in Secrets Manager
   - Test connection from ECS task

2. Webhook Failures
   - Verify SSL certificate
   - Check Twilio webhook logs
   - Ensure correct URL configuration

3. Message Scheduling Issues
   - Check EventBridge rule status
   - Verify task execution role permissions
   - Review CloudWatch Logs

### Getting Help

1. Check CloudWatch Logs
2. Review ECS task status
3. Verify secrets and configuration
4. Check application logs for specific error messages

## Security Considerations

1. Regular security updates
2. Rotate credentials periodically
3. Monitor AWS CloudTrail
4. Review IAM permissions
5. Keep dependencies updated
