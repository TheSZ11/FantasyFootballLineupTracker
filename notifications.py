import requests
import json
import os
import smtplib
import logging
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from discord_webhook import DiscordWebhook, DiscordEmbed

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self):
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        self.discord_webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
        self.email_config = {
            'smtp_server': os.getenv('EMAIL_SMTP_SERVER'),
            'smtp_port': int(os.getenv('EMAIL_SMTP_PORT', 587)),
            'username': os.getenv('EMAIL_USERNAME'),
            'password': os.getenv('EMAIL_PASSWORD'),
            'recipient': os.getenv('EMAIL_RECIPIENT')
        }
    
    def send_email(self, subject, message, urgency="info"):
        """Send email notification"""
        
        # Check if email is configured
        if not all([self.email_config['smtp_server'], self.email_config['username'], 
                   self.email_config['password'], self.email_config['recipient']]):
            logger.warning("Email not fully configured - skipping email notification")
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['username']
            msg['To'] = self.email_config['recipient']
            
            # Add urgency indicator to subject
            urgency_prefix = {
                "urgent": "🚨 URGENT",
                "important": "⚡ IMPORTANT", 
                "info": "✅ INFO",
                "warning": "⚠️ WARNING"
            }
            
            msg['Subject'] = f"{urgency_prefix.get(urgency, '')} {subject}"
            
            # Create HTML body for better formatting
            urgency_colors = {
                "urgent": "#ff0000",
                "important": "#ff9900", 
                "info": "#36a64f",
                "warning": "#ffaa00"
            }
            
            html_body = f"""
            <html>
                <body>
                    <h3 style="color: {urgency_colors.get(urgency, '#333')};">
                        Fantrax Lineup Alert
                    </h3>
                    <p><strong>Time:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p><strong>Alert Level:</strong> {urgency.upper()}</p>
                    <div style="background-color: #f5f5f5; padding: 15px; border-left: 4px solid {urgency_colors.get(urgency, '#333')}; margin: 10px 0;">
                        {message.replace('\n', '<br>')}
                    </div>
                    <hr>
                    <small style="color: #666;">
                        Fantrax Lineup Monitor - Automated Alert System
                    </small>
                </body>
            </html>
            """
            
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['username'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent successfully: {urgency}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_discord_message(self, message, urgency="info"):
        """Send message to Discord with rich formatting"""
        
        if not self.discord_webhook_url:
            logger.warning("No Discord webhook configured - skipping Discord notification")
            return False
            
        try:
            webhook = DiscordWebhook(url=self.discord_webhook_url)
            
            # Color coding and emoji based on urgency
            colors = {
                "urgent": 0xff0000,    # Red
                "important": 0xff9900, # Orange  
                "info": 0x36a64f,      # Green
                "warning": 0xffaa00    # Yellow
            }
            
            emoji_map = {
                "urgent": "🚨",
                "important": "⚡", 
                "info": "✅",
                "warning": "⏳"
            }
            
            # Create embed for better formatting
            embed = DiscordEmbed(
                title=f"{emoji_map.get(urgency, '📝')} Fantrax Lineup Alert",
                description=message,
                color=colors.get(urgency, 0x808080)
            )
            
            embed.set_timestamp()
            embed.set_footer(text="Fantrax Lineup Monitor")
            
            webhook.add_embed(embed)
            
            response = webhook.execute()
            
            if response.status_code == 200:
                logger.info(f"Discord notification sent: {urgency}")
                return True
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def send_notification(self, subject, message, urgency="info"):
        """Send notification via both email and Discord based on urgency"""
        email_success = False
        discord_success = False
        
        # Send email for urgent and important alerts
        if urgency in ["urgent", "important"]:
            email_success = self.send_email(subject, message, urgency)
        
        # Always send Discord (if configured)
        discord_success = self.send_discord_message(message, urgency)
        
        # Log if both failed
        if urgency in ["urgent", "important"] and not email_success and not discord_success:
            logger.error("ALL notification methods failed for critical alert!")
            
        return email_success or discord_success
    
    def send_urgent_alert(self, message):
        """Send urgent notification for unexpected benching - both email and Discord"""
        return self.send_notification("Player Benched Alert", message, "urgent")
    
    def send_important_alert(self, message):
        """Send important notification for unexpected starter - both email and Discord"""
        return self.send_notification("Unexpected Starter", message, "important")
    
    def send_info_update(self, message):
        """Send informational update - Discord only to avoid email spam"""
        return self.send_discord_message(message, "info")
        
    def send_warning(self, message):
        """Send warning about missing data - Discord only"""
        return self.send_discord_message(message, "warning")
    
    def test_notifications(self):
        """Test both notification methods"""
        logger.info("Testing notification systems...")
        
        test_message = f"Test notification sent at {datetime.now().strftime('%H:%M:%S')}"
        
        email_result = self.send_email("Test Email", test_message, "info")
        discord_result = self.send_discord_message(test_message, "info")
        
        logger.info(f"Email test: {'✅ Success' if email_result else '❌ Failed'}")
        logger.info(f"Discord test: {'✅ Success' if discord_result else '❌ Failed'}")
        
        return email_result or discord_result