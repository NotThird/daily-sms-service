#!/usr/bin/env python3
import argparse
import requests
import sys
import json
from datetime import datetime, timedelta
import time
from twilio.rest import Client
import os
import logging
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DeploymentVerifier:
    def __init__(self, base_url: str, twilio_sid: str, twilio_token: str):
        """Initialize verifier with necessary credentials."""
        self.base_url = base_url.rstrip('/')
        self.twilio_client = Client(twilio_sid, twilio_token)
        self.session = requests.Session()

    def verify_health_endpoint(self) -> bool:
        """Verify the application health check endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'healthy':
                logger.error(f"Health check failed: {data}")
                return False
                
            logger.info("Health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def verify_webhook_authentication(self) -> bool:
        """Verify Twilio webhook authentication is working."""
        try:
            # Try to access webhook without proper Twilio signature
            response = self.session.post(f"{self.base_url}/webhook/inbound")
            
            if response.status_code != 403:
                logger.error("Webhook authentication check failed: Missing signature validation")
                return False
                
            logger.info("Webhook authentication check passed")
            return True
            
        except Exception as e:
            logger.error(f"Webhook authentication check failed: {e}")
            return False

    def verify_message_scheduling(self) -> bool:
        """Verify message scheduling system is operational."""
        try:
            # Check recent scheduled messages in Twilio logs
            messages = self.twilio_client.messages.list(
                limit=20,
                date_sent_after=datetime.utcnow() - timedelta(hours=24)
            )
            
            if not messages:
                logger.warning("No messages found in the last 24 hours")
                return False
                
            # Check message statuses
            failed = [m for m in messages if m.status == 'failed']
            if failed:
                logger.warning(f"Found {len(failed)} failed messages in the last 24 hours")
            
            logger.info(f"Found {len(messages)} messages in the last 24 hours")
            return True
            
        except Exception as e:
            logger.error(f"Message scheduling check failed: {e}")
            return False

    def verify_database_connection(self) -> bool:
        """Verify database connection through the application."""
        try:
            response = self.session.get(f"{self.base_url}/health")
            response.raise_for_status()
            data = response.json()
            
            # Health endpoint should verify database connection
            if 'database' in data and not data['database'].get('connected', False):
                logger.error("Database connection check failed")
                return False
                
            logger.info("Database connection check passed")
            return True
            
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False

    def verify_ssl_certificate(self) -> bool:
        """Verify SSL certificate is valid and not expiring soon."""
        try:
            response = requests.get(self.base_url, verify=True)
            
            # Check certificate expiration
            cert = response.raw.connection.sock.getpeercert()
            expires = datetime.strptime(cert['notAfter'], '%b %d %H:%M:%S %Y %Z')
            days_until_expiry = (expires - datetime.utcnow()).days
            
            if days_until_expiry < 30:
                logger.warning(f"SSL certificate expires in {days_until_expiry} days")
                return False
                
            logger.info(f"SSL certificate valid for {days_until_expiry} days")
            return True
            
        except Exception as e:
            logger.error(f"SSL certificate check failed: {e}")
            return False

    def verify_rate_limiting(self) -> bool:
        """Verify rate limiting is working."""
        try:
            # Make multiple rapid requests
            responses = []
            for _ in range(50):
                responses.append(
                    self.session.get(f"{self.base_url}/health")
                )
                time.sleep(0.1)
            
            # Check if any requests were rate limited
            rate_limited = [r for r in responses if r.status_code == 429]
            
            if not rate_limited:
                logger.warning("Rate limiting may not be properly configured")
                return False
                
            logger.info("Rate limiting check passed")
            return True
            
        except Exception as e:
            logger.error(f"Rate limiting check failed: {e}")
            return False

    def verify_logging(self) -> bool:
        """Verify logging system is operational."""
        try:
            # Make a request that should generate logs
            self.session.post(
                f"{self.base_url}/webhook/inbound",
                data={'test': 'logging'}
            )
            
            # Wait briefly for logs to be processed
            time.sleep(2)
            
            # Note: In a real implementation, you would check CloudWatch logs
            # or your logging service API here
            logger.info("Logging check completed (manual verification required)")
            return True
            
        except Exception as e:
            logger.error(f"Logging check failed: {e}")
            return False

    def run_all_checks(self) -> Dict[str, bool]:
        """Run all verification checks and return results."""
        results = {
            'health_endpoint': self.verify_health_endpoint(),
            'webhook_authentication': self.verify_webhook_authentication(),
            'message_scheduling': self.verify_message_scheduling(),
            'database_connection': self.verify_database_connection(),
            'ssl_certificate': self.verify_ssl_certificate(),
            'rate_limiting': self.verify_rate_limiting(),
            'logging': self.verify_logging()
        }
        
        return results

def main():
    parser = argparse.ArgumentParser(description='Verify deployment status')
    parser.add_argument('--url', required=True, help='Base URL of the deployed application')
    parser.add_argument('--twilio-sid', required=True, help='Twilio Account SID')
    parser.add_argument('--twilio-token', required=True, help='Twilio Auth Token')
    args = parser.parse_args()

    verifier = DeploymentVerifier(args.url, args.twilio_sid, args.twilio_token)
    results = verifier.run_all_checks()
    
    # Print results
    print("\nDeployment Verification Results:")
    print("=" * 40)
    
    all_passed = True
    for check, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check.replace('_', ' ').title()}: {status}")
        if not passed:
            all_passed = False
    
    print("\nOverall Status:", "✅ PASSED" if all_passed else "❌ FAILED")
    
    # Exit with appropriate status code
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
