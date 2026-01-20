#!/usr/bin/env python3
"""
External monitoring tool for Augur Hakesch API
Monitors CPU, memory, and disk usage and sends email alerts when thresholds are exceeded.
"""

import os
import sys
import time
import json
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, List
import requests
from pathlib import Path

# Configure logging - set up basic logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Try to add file handler, but don't fail if it doesn't work
try:
    log_file = os.getenv('LOG_FILE', '/app/logs/monitor.log')
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
    logger.info(f"Logging to file: {log_file}")
except Exception as e:
    logger.warning(f"Could not set up file logging: {e}, continuing with stdout only")


class MonitorConfig:
    """Configuration for the monitoring tool"""
    
    def __init__(self):
        # Keycloak configuration - strip whitespace to avoid issues
        self.keycloak_url = os.getenv('KEYCLOAK_URL', 'https://id.augur.world').strip()
        self.keycloak_realm = os.getenv('KEYCLOAK_REALM', 'augur').strip()
        self.keycloak_client_id = os.getenv('KEYCLOAK_CLIENT_ID', '').strip()
        self.keycloak_client_secret = os.getenv('KEYCLOAK_CLIENT_SECRET', '').strip()
        self.keycloak_username = os.getenv('KEYCLOAK_USERNAME', '').strip()
        self.keycloak_password = os.getenv('KEYCLOAK_PASSWORD', '').strip()
        
        # API configuration
        self.api_url = os.getenv('API_URL', 'http://localhost:8000').strip().rstrip('/')
        self.api_path = os.getenv('API_PATH', '/api').strip()
        
        # Monitoring configuration
        self.check_interval = int(os.getenv('CHECK_INTERVAL', 300))  # 5 minutes default
        self.email_cooldown = int(os.getenv('EMAIL_COOLDOWN', 43200))  # 12 hours default
        
        # Thresholds
        self.cpu_critical = float(os.getenv('CPU_CRITICAL', 90.0))
        self.memory_critical = float(os.getenv('MEMORY_CRITICAL', 90.0))
        self.disk_critical = float(os.getenv('DISK_CRITICAL', 90.0))
        
        # Email configuration
        self.smtp_host = os.getenv('SMTP_HOST')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_from = os.getenv('SMTP_FROM')
        self.email_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        self.email_recipients = [r.strip() for r in self.email_recipients if r.strip()]
        
        # Validate required configuration
        self._validate()
    
    def _validate(self):
        """Validate that all required configuration is present"""
        errors = []
        
        logger.debug("Validating configuration...")
        
        if not self.keycloak_client_id:
            errors.append("KEYCLOAK_CLIENT_ID is required")
        # Allow either client credentials OR password grant (password grant can optionally include client_secret)
        has_client_credentials = bool(self.keycloak_client_secret and not self.keycloak_username)
        has_password_grant = bool(self.keycloak_username and self.keycloak_password)
        if not (has_client_credentials or has_password_grant):
            errors.append("Either KEYCLOAK_CLIENT_SECRET (for client credentials) OR KEYCLOAK_USERNAME/KEYCLOAK_PASSWORD (for password grant) is required")
        if not self.smtp_host:
            errors.append("SMTP_HOST is required")
        if not self.smtp_from:
            errors.append("SMTP_FROM is required")
        if not self.email_recipients:
            errors.append("EMAIL_RECIPIENTS is required (at least one recipient)")
        
        if errors:
            error_msg = "Configuration errors:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.debug("Configuration validation passed")


class KeycloakAuth:
    """Handles Keycloak authentication"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.token_url = f"{config.keycloak_url}/realms/{config.keycloak_realm}/protocol/openid-connect/token"
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    def get_token(self) -> str:
        """Get or refresh access token"""
        if self.access_token and self.token_expires_at and datetime.now() < self.token_expires_at:
            return self.access_token
        
        logger.info("Authenticating with Keycloak...")
        logger.debug(f"Token URL: {self.token_url}")
        logger.debug(f"Client ID: {self.config.keycloak_client_id}")
        
        # Determine authentication method
        has_client_secret = bool(self.config.keycloak_client_secret)
        has_username_password = bool(self.config.keycloak_username and self.config.keycloak_password)
        
        logger.info(f"Auth config - Has client_secret: {has_client_secret}, Has username/password: {has_username_password}")
        
        if not has_client_secret and not has_username_password:
            raise ValueError("No authentication method configured")
        
        # Use password grant if username/password are provided (even if client_secret is also available)
        # Use client credentials only if ONLY client_secret is provided
        if has_username_password:
            logger.info("Using password grant flow")
            # Password grant typically requires client_secret for confidential clients
            token_data = {
                'grant_type': 'password',
                'client_id': self.config.keycloak_client_id,
                'username': self.config.keycloak_username,
                'password': self.config.keycloak_password
            }
            # Add client_secret if available (required for confidential clients)
            if has_client_secret:
                logger.info("Including client_secret in password grant (client is confidential)")
                token_data['client_secret'] = self.config.keycloak_client_secret
            else:
                logger.warning("Password grant without client_secret - client must be 'public' or Direct Access Grants must be enabled")
        elif has_client_secret:
            # Only use client credentials if username/password are NOT provided
            logger.info("Using client credentials flow")
            token_data = {
                'grant_type': 'client_credentials',
                'client_id': self.config.keycloak_client_id,
                'client_secret': self.config.keycloak_client_secret
            }
        else:
            raise ValueError("Invalid authentication configuration")
        
        try:
            # Determine which method we're using based on token_data
            auth_method = token_data.get('grant_type', 'unknown')
            logger.info(f"Using {auth_method} authentication method")
            
            # Enable requests debug logging if DEBUG level is set
            if logger.level == logging.DEBUG:
                import http.client
                http.client.HTTPConnection.debuglevel = 1
                logging.getLogger("requests.packages.urllib3").setLevel(logging.DEBUG)
                logging.getLogger("requests.packages.urllib3").propagate = True
            logger.debug(f"Token URL: {self.token_url}")
            logger.debug(f"Client ID: {self.config.keycloak_client_id}")
            logger.debug(f"Has client_secret: {'Yes' if 'client_secret' in token_data else 'No'}")
            logger.debug(f"Has username: {'Yes' if 'username' in token_data else 'No'}")
            
            # Log request details (without sensitive data)
            request_data_safe = {k: ('***' if k in ['password', 'client_secret'] else v) for k, v in token_data.items()}
            logger.debug(f"Request data: {request_data_safe}")
            
            # Send request - requests library will automatically URL-encode the dict
            # This should match curl's behavior
            # Prepare request for debugging
            import urllib.parse
            debug_data = urllib.parse.urlencode(token_data)
            logger.debug(f"Request body (first 100 chars): {debug_data[:100]}...")
            
            response = requests.post(
                self.token_url,
                data=token_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                },
                timeout=10,
                verify=True  # Verify SSL certificates
            )
            
            logger.debug(f"Response status: {response.status_code}")
            logger.debug(f"Response headers: {dict(response.headers)}")
            
            # Always log response details for debugging before raising
            if response.status_code != 200:
                logger.error(f"Keycloak authentication failed with status {response.status_code}")
                logger.error(f"Request URL: {self.token_url}")
                logger.error(f"Client ID: {self.config.keycloak_client_id}")
                
                try:
                    error_response = response.json()
                    error_description = error_response.get('error_description', 'No error description')
                    error_type = error_response.get('error', 'Unknown error')
                    logger.error(f"Error type: {error_type}")
                    logger.error(f"Error description: {error_description}")
                    
                    # Provide helpful hints
                    error_lower = error_type.lower()
                    grant_type = token_data.get('grant_type', 'unknown')
                    if 'invalid_client' in error_lower:
                        logger.error("Hint: Check that KEYCLOAK_CLIENT_ID and KEYCLOAK_CLIENT_SECRET are correct")
                    elif 'invalid_grant' in error_lower:
                        logger.error("=" * 60)
                        logger.error("TROUBLESHOOTING 'invalid_grant' ERROR:")
                        logger.error("=" * 60)
                        logger.error("This error can occur even with correct credentials if:")
                        logger.error("")
                        logger.error("1. Direct Access Grants is NOT enabled:")
                        logger.error("   → Go to Keycloak Admin Console")
                        logger.error("   → Clients > [your-client-id] > Settings")
                        logger.error("   → Enable 'Direct Access Grants Enabled'")
                        logger.error("   → Click 'Save'")
                        logger.error("")
                        if grant_type == 'password':
                            logger.error("2. Client configuration mismatch:")
                            if 'client_secret' in token_data:
                                logger.error("   → You're sending client_secret, so client MUST be 'confidential'")
                                logger.error("   → Check: Clients > [your-client-id] > Settings > Access Type = 'confidential'")
                            else:
                                logger.error("   → You're NOT sending client_secret, so client MUST be 'public'")
                                logger.error("   → Check: Clients > [your-client-id] > Settings > Access Type = 'public'")
                            logger.error("")
                        logger.error("3. User account issues:")
                        logger.error("   → User account might be disabled")
                        logger.error("   → User might not have required roles")
                        logger.error("   → Password might have expired")
                        logger.error("")
                        logger.error("4. Test with curl to verify:")
                        logger.error(f"   curl -X POST '{self.token_url}' \\")
                        logger.error("     -d 'grant_type=password' \\")
                        logger.error(f"     -d 'client_id={self.config.keycloak_client_id}' \\")
                        if 'client_secret' in token_data:
                            logger.error("     -d 'client_secret=***' \\")
                        logger.error("     -d 'username=YOUR_USERNAME' \\")
                        logger.error("     -d 'password=YOUR_PASSWORD'")
                        logger.error("=" * 60)
                    elif 'unauthorized_client' in error_lower:
                        logger.error("=" * 60)
                        logger.error("TROUBLESHOOTING 'unauthorized_client' ERROR:")
                        logger.error("=" * 60)
                        logger.error("This usually means the client_secret is incorrect or client configuration issue")
                        logger.error("")
                        logger.error("1. Verify client_secret matches Keycloak:")
                        logger.error(f"   → Check: Clients > {self.config.keycloak_client_id} > Credentials > Secret")
                        logger.error("   → Make sure there are no extra spaces or newlines in .env file")
                        logger.error("")
                        logger.error("2. Check client configuration:")
                        if grant_type == 'password':
                            logger.error("   → Enable 'Direct Access Grants Enabled'")
                            logger.error("   → Set 'Access Type' to 'confidential' (since you're using client_secret)")
                        else:
                            logger.error("   → Ensure client is 'confidential' and has client secret")
                        logger.error("")
                        logger.error("3. Test with exact curl command:")
                        logger.error(f"   curl -X POST '{self.token_url}' \\")
                        logger.error("     -d 'grant_type=password' \\")
                        logger.error(f"     -d 'client_id={self.config.keycloak_client_id}' \\")
                        logger.error("     -d 'client_secret=YOUR_SECRET' \\")
                        logger.error("     -d 'username=YOUR_USERNAME' \\")
                        logger.error("     -d 'password=YOUR_PASSWORD'")
                        logger.error("")
                        logger.error("4. Check .env file format:")
                        logger.error("   → No quotes around values")
                        logger.error("   → No trailing spaces")
                        logger.error("   → No newlines in values")
                        logger.error("=" * 60)
                except Exception as parse_error:
                    logger.error(f"Could not parse error response: {parse_error}")
                    logger.error(f"Response status: {response.status_code}")
                    logger.error(f"Response headers: {dict(response.headers)}")
                    logger.error(f"Response text (first 500 chars): {response.text[:500]}")
                
                # Raise after logging
                response.raise_for_status()
            
            token_response = response.json()
            self.access_token = token_response['access_token']
            expires_in = token_response.get('expires_in', 3600)
            self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
            
            # Validate token format
            if not self.access_token or len(self.access_token) < 10:
                raise ValueError("Invalid token received from Keycloak")
            
            logger.info("Successfully authenticated with Keycloak")
            logger.debug(f"Token length: {len(self.access_token)}")
            logger.debug(f"Token preview: {self.access_token[:20]}...")
            return self.access_token
        except requests.HTTPError as e:
            # This should not happen if we already logged above, but catch it anyway
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 401:
                logger.error("Authentication failed - 401 Unauthorized")
                logger.error("This usually means:")
                logger.error("  1. Invalid credentials (client_id/client_secret or username/password)")
                logger.error("  2. Client not configured for the requested grant type")
                logger.error("  3. Direct Access Grants not enabled (for password grant)")
            logger.error(f"HTTP error during Keycloak authentication: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Request error during Keycloak authentication: {e}")
            raise


class EmailSender:
    """Handles sending email alerts"""
    
    def __init__(self, config: MonitorConfig):
        self.config = config
        self.last_email_sent: Dict[str, datetime] = {}
    
    def can_send_email(self, alert_type: str) -> bool:
        """Check if enough time has passed since last email for this alert type"""
        if alert_type not in self.last_email_sent:
            return True
        
        time_since_last = datetime.now() - self.last_email_sent[alert_type]
        return time_since_last.total_seconds() >= self.config.email_cooldown
    
    def send_alert(self, subject: str, body: str, alert_type: str = "general") -> bool:
        """Send email alert"""
        if not self.can_send_email(alert_type):
            logger.info(f"Email cooldown active for {alert_type}, skipping email")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_from
            msg['To'] = ', '.join(self.config.email_recipients)
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.smtp_port == 587:
                    server.starttls()
                if self.config.smtp_user and self.config.smtp_password:
                    server.login(self.config.smtp_user, self.config.smtp_password)
                
                server.send_message(msg)
            
            self.last_email_sent[alert_type] = datetime.now()
            logger.info(f"Alert email sent: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


class SystemMonitor:
    """Monitors system metrics via API"""
    
    def __init__(self, config: MonitorConfig, auth: KeycloakAuth, email_sender: EmailSender):
        self.config = config
        self.auth = auth
        self.email_sender = email_sender
        # Construct API base URL - ensure no double slashes
        api_url = config.api_url.rstrip('/')
        api_path = config.api_path.strip('/')
        self.api_base_url = f"{api_url}/{api_path}" if api_path else api_url
        logger.info(f"API base URL: {self.api_base_url}")
    
    def get_monitoring_data(self) -> Optional[Dict]:
        """Fetch monitoring summary from API"""
        try:
            token = self.auth.get_token()
            if not token:
                logger.error("No access token available")
                return None
            
            url = f"{self.api_base_url}/monitoring/summary"
            
            # Ensure token is clean (no extra whitespace)
            token = token.strip()
            
            # Build Authorization header - ensure proper format (Bearer with space)
            if not token.startswith('Bearer'):
                auth_header = f'Bearer {token}'
            else:
                auth_header = token  # Already has Bearer prefix
            
            headers = {
                'Authorization': auth_header,
                'Accept': 'application/json'
            }
            
            logger.info(f"Fetching monitoring data from: {url}")
            logger.debug(f"Authorization header format: {auth_header[:30]}...")
            logger.debug(f"Token length: {len(token)}")
            logger.debug(f"Full headers: {dict((k, v[:50] + '...' if len(str(v)) > 50 else v) for k, v in headers.items())}")
            
            response = requests.get(
                url,
                headers=headers,
                timeout=30
            )
            
            logger.debug(f"API response status: {response.status_code}")
            
            if response.status_code == 401:
                logger.error("API returned 401 Unauthorized")
                error_text = response.text[:500]
                logger.error(f"Response: {error_text}")
                
                # Check if it's an AuthClaimMissing error
                if 'AuthClaimMissing' in error_text:
                    logger.error("=" * 60)
                    logger.error("AUTH CLAIM MISSING ERROR:")
                    logger.error("=" * 60)
                    logger.error("The Keycloak middleware is not recognizing the bearer token.")
                    logger.error("")
                    logger.error("Possible causes:")
                    logger.error("1. API_PATH might be incorrect")
                    logger.error(f"   Current API_PATH: '{self.config.api_path}'")
                    logger.error(f"   Full URL: {url}")
                    logger.error("   Try setting API_PATH=/abfluss_api in your .env file")
                    logger.error("")
                    logger.error("2. Token format issue")
                    logger.error(f"   Token length: {len(token)}")
                    logger.error(f"   Token preview: {token[:30]}...")
                    logger.error("   Verify token is a valid JWT")
                    logger.error("=" * 60)
                
                # Try to refresh token
                logger.info("Attempting to refresh token...")
                self.auth.access_token = None  # Force refresh
                self.auth.token_expires_at = None
                token = self.auth.get_token()
                if token:
                    token = token.strip()
                    headers['Authorization'] = f'Bearer {token}'
                    logger.info("Retrying with new token...")
                    response = requests.get(url, headers=headers, timeout=30)
            
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            logger.error(f"HTTP error fetching monitoring data: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"Response text: {e.response.text[:500]}")
            return None
        except requests.RequestException as e:
            logger.error(f"Request error fetching monitoring data: {e}")
            return None
    
    def check_thresholds(self, data: Dict) -> List[Dict]:
        """Check if any thresholds are exceeded"""
        alerts = []
        timestamp = datetime.now().isoformat()
        
        # Check CPU
        cpu_percent = data.get('cpu', {}).get('percent', 0)
        if cpu_percent >= self.config.cpu_critical:
            alerts.append({
                'type': 'cpu',
                'severity': 'critical',
                'value': cpu_percent,
                'threshold': self.config.cpu_critical,
                'message': f"CPU usage is critical: {cpu_percent:.1f}% (threshold: {self.config.cpu_critical}%)"
            })
        
        # Check Memory
        memory_percent = data.get('memory', {}).get('used_percent', 0)
        if memory_percent >= self.config.memory_critical:
            alerts.append({
                'type': 'memory',
                'severity': 'critical',
                'value': memory_percent,
                'threshold': self.config.memory_critical,
                'message': f"Memory usage is critical: {memory_percent:.1f}% (threshold: {self.config.memory_critical}%)"
            })
        
        # Check Disk
        disk_percent = data.get('disk', {}).get('used_percent', 0)
        if disk_percent >= self.config.disk_critical:
            alerts.append({
                'type': 'disk',
                'severity': 'critical',
                'value': disk_percent,
                'threshold': self.config.disk_critical,
                'message': f"Disk usage is critical: {disk_percent:.1f}% (threshold: {self.config.disk_critical}%)"
            })
        
        return alerts
    
    def format_alert_email(self, alerts: List[Dict], data: Dict) -> tuple[str, str]:
        """Format alert email subject and body"""
        alert_types = [a['type'].upper() for a in alerts]
        subject = f"[AUGUR MONITOR] Critical Alert: {', '.join(alert_types)}"
        
        body = f"""
AUGUR HAKESCH - System Monitoring Alert

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

CRITICAL ALERTS:
"""
        for alert in alerts:
            body += f"\n{alert['message']}\n"
        
        body += f"""

CURRENT SYSTEM STATUS:
----------------------
CPU Usage: {data.get('cpu', {}).get('percent', 0):.1f}%
Memory Usage: {data.get('memory', {}).get('used_percent', 0):.1f}% ({data.get('memory', {}).get('used_gb', 0):.2f} GB / {data.get('memory', {}).get('total_gb', 0):.2f} GB)
Disk Usage: {data.get('disk', {}).get('used_percent', 0):.1f}% ({data.get('disk', {}).get('used_gb', 0):.2f} GB / {data.get('disk', {}).get('total_gb', 0):.2f} GB)
Uptime: {data.get('uptime_formatted', 'N/A')}

THRESHOLDS:
-----------
CPU Critical: {self.config.cpu_critical}%
Memory Critical: {self.config.memory_critical}%
Disk Critical: {self.config.disk_critical}%

Please investigate the system immediately.

---
This is an automated message from the Augur Hakesch monitoring system.
"""
        return subject, body
    
    def run_check(self):
        """Run a single monitoring check"""
        logger.info("Running monitoring check...")
        
        data = self.get_monitoring_data()
        if not data:
            logger.warning("Could not fetch monitoring data, skipping check")
            return
        
        logger.info(
            f"System status - CPU: {data.get('cpu', {}).get('percent', 0):.1f}%, "
            f"Memory: {data.get('memory', {}).get('used_percent', 0):.1f}%, "
            f"Disk: {data.get('disk', {}).get('used_percent', 0):.1f}%"
        )
        
        alerts = self.check_thresholds(data)
        
        if alerts:
            logger.warning(f"Found {len(alerts)} critical alert(s)")
            subject, body = self.format_alert_email(alerts, data)
            
            # Send email for each alert type (they share cooldown per type)
            for alert in alerts:
                self.email_sender.send_alert(subject, body, alert_type=alert['type'])
        else:
            logger.info("All metrics within acceptable thresholds")
    
    def run(self):
        """Run monitoring loop"""
        logger.info("Starting monitoring service...")
        logger.info(f"Check interval: {self.config.check_interval} seconds")
        logger.info(f"Email cooldown: {self.config.email_cooldown} seconds ({self.config.email_cooldown / 3600:.1f} hours)")
        logger.info(f"Thresholds - CPU: {self.config.cpu_critical}%, Memory: {self.config.memory_critical}%, Disk: {self.config.disk_critical}%")
        
        while True:
            try:
                self.run_check()
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error in monitoring loop: {e}", exc_info=True)
            
            logger.info(f"Waiting {self.config.check_interval} seconds until next check...")
            time.sleep(self.config.check_interval)


def main():
    """Main entry point"""
    logger.info("=" * 60)
    logger.info("Augur Hakesch Monitor - Starting up")
    logger.info("=" * 60)
    
    try:
        logger.info("Loading configuration...")
        config = MonitorConfig()
        logger.info("Configuration loaded successfully")
        
        logger.info("Initializing Keycloak authentication...")
        auth = KeycloakAuth(config)
        logger.info("Keycloak authentication initialized")
        
        logger.info("Initializing email sender...")
        email_sender = EmailSender(config)
        logger.info("Email sender initialized")
        
        logger.info("Initializing system monitor...")
        monitor = SystemMonitor(config, auth, email_sender)
        logger.info("System monitor initialized")
        
        logger.info("Starting monitoring loop...")
        monitor.run()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        logger.error("Please check your environment variables and .env file")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        logger.error("Monitor will exit")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        # Last resort error handling
        print(f"CRITICAL: Monitor failed to start: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
