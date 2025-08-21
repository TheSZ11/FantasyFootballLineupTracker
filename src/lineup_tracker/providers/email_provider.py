"""
Email notification provider implementation.

Sends email notifications using SMTP with HTML formatting
and proper error handling.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
from datetime import datetime

from ..domain.interfaces import BaseNotificationProvider
from ..domain.models import Alert
from ..domain.enums import AlertUrgency
from ..domain.exceptions import EmailNotificationError, NotificationProviderNotConfiguredError

logger = logging.getLogger(__name__)


class EmailProvider(BaseNotificationProvider):
    """
    Email notification provider using SMTP.
    
    Sends HTML-formatted emails for urgent and important alerts.
    """
    
    def __init__(
        self,
        smtp_server: str,
        smtp_port: int,
        username: str,
        password: str,
        recipient: str,
        sender_name: str = "Fantrax Lineup Monitor"
    ):
        super().__init__("email")
        
        # Validate configuration
        if not all([smtp_server, username, password, recipient]):
            raise NotificationProviderNotConfiguredError(
                "All email configuration fields are required"
            )
        
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.recipient = recipient
        self.sender_name = sender_name
        
        # Email configuration
        self._urgency_colors = self._create_urgency_colors()
        self._urgency_prefixes = self._create_urgency_prefixes()
        
        logger.info(f"Email provider initialized for {recipient}")
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert via email."""
        try:
            subject = self._create_alert_subject(alert)
            html_body = self._create_alert_html(alert)
            
            return await self._send_email(subject, html_body, alert.urgency)
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            raise EmailNotificationError(
                "Failed to send email notification",
                details=str(e)
            )
    
    async def send_message(self, message: str, urgency: AlertUrgency = AlertUrgency.INFO) -> bool:
        """Send a simple text message via email."""
        try:
            subject = f"{self._urgency_prefixes.get(urgency, '')} Lineup Monitor Update"
            html_body = self._create_message_html(message, urgency)
            
            return await self._send_email(subject, html_body, urgency)
            
        except Exception as e:
            logger.error(f"Failed to send email message: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test email connection."""
        try:
            test_message = f"Email connection test - {datetime.now().strftime('%H:%M:%S')}"
            return await self.send_message(test_message, AlertUrgency.INFO)
            
        except Exception as e:
            logger.error(f"Email connection test failed: {e}")
            return False
    
    async def _send_email(self, subject: str, html_body: str, urgency: AlertUrgency) -> bool:
        """Send email with HTML content."""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.username}>"
            msg['To'] = self.recipient
            msg['Subject'] = subject
            
            # Create HTML part
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.debug(f"Email sent successfully: {urgency.value}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except Exception as e:
            logger.error(f"Email sending error: {e}")
            return False
    
    def _create_alert_subject(self, alert: Alert) -> str:
        """Create email subject for alert."""
        prefix = self._urgency_prefixes.get(alert.urgency, "📋")
        player_name = alert.player.name
        
        if alert.alert_type.value == "unexpected_benching":
            return f"{prefix} {player_name} BENCHED!"
        elif alert.alert_type.value == "unexpected_starting":
            return f"{prefix} {player_name} STARTING!"
        else:
            return f"{prefix} Lineup Update: {player_name}"
    
    def _create_alert_html(self, alert: Alert) -> str:
        """Create HTML body for alert email."""
        color = self._urgency_colors.get(alert.urgency, '#333333')
        
        html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: {color}; color: white; padding: 20px; text-align: center; }}
                    .content {{ background-color: #f9f9f9; padding: 20px; }}
                    .player-info {{ background-color: white; padding: 15px; margin: 10px 0; border-left: 4px solid {color}; }}
                    .match-info {{ background-color: white; padding: 15px; margin: 10px 0; }}
                    .fantasy-stats {{ background-color: #e8f4f8; padding: 10px; margin: 10px 0; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>{alert.emoji} Fantrax Lineup Alert</h2>
                        <p>{alert.urgency.value.upper()}</p>
                    </div>
                    
                    <div class="content">
                        <div class="player-info">
                            <h3>{alert.player.name}</h3>
                            <p><strong>Team:</strong> {alert.player.team.name} ({alert.player.team.abbreviation})</p>
                            <p><strong>Position:</strong> {alert.player.position.value}</p>
                        </div>
                        
                        <div class="match-info">
                            <h4>Match Information</h4>
                            <p><strong>Match:</strong> {alert.match.home_team.name} vs {alert.match.away_team.name}</p>
                            <p><strong>Kickoff:</strong> {alert.match.kickoff.strftime('%H:%M on %B %d, %Y')}</p>
                        </div>
                        
                        {self._create_fantasy_stats_html(alert.player)}
                        
                        <div style="margin: 20px 0; padding: 15px; background-color: white; border: 1px solid {color};">
                            <h4>Alert Details</h4>
                            <p>{alert.message}</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Fantrax Lineup Monitor - Sent at {alert.timestamp.strftime('%H:%M:%S on %B %d, %Y')}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return html
    
    def _create_message_html(self, message: str, urgency: AlertUrgency) -> str:
        """Create HTML body for simple message."""
        color = self._urgency_colors.get(urgency, '#333333')
        emoji = "📧" if urgency == AlertUrgency.INFO else "⚠️"
        
        html = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; }}
                    .container {{ max-width: 600px; margin: 0 auto; }}
                    .header {{ background-color: {color}; color: white; padding: 15px; text-align: center; }}
                    .content {{ background-color: #f9f9f9; padding: 20px; }}
                    .message {{ background-color: white; padding: 15px; border-left: 4px solid {color}; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h3>{emoji} Fantrax Lineup Monitor</h3>
                    </div>
                    
                    <div class="content">
                        <div class="message">
                            <p>{message.replace(chr(10), '<br>')}</p>
                        </div>
                    </div>
                    
                    <div class="footer">
                        <p>Sent at {datetime.now().strftime('%H:%M:%S on %B %d, %Y')}</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        return html
    
    def _create_fantasy_stats_html(self, player) -> str:
        """Create HTML section for player statistics."""
        stats_data = []
        
        if player.games_played:
            stats_data.append(f"<p><strong>Games Played:</strong> {player.games_played}</p>")
        
        if player.draft_percentage:
            stats_data.append(f"<p><strong>Draft Percentage:</strong> {player.draft_percentage}%</p>")
        
        if not stats_data:
            return ""
        
        html = """
        <div class="player-stats">
            <h4>Player Statistics</h4>
        """
        html += "".join(stats_data)
        html += "</div>"
        return html
    
    def _create_urgency_colors(self) -> Dict[AlertUrgency, str]:
        """Create color mapping for email styling."""
        return {
            AlertUrgency.URGENT: "#dc3545",     # Red
            AlertUrgency.IMPORTANT: "#fd7e14",  # Orange
            AlertUrgency.WARNING: "#ffc107",    # Yellow
            AlertUrgency.INFO: "#17a2b8"        # Blue
        }
    
    def _create_urgency_prefixes(self) -> Dict[AlertUrgency, str]:
        """Create subject line prefixes for urgency levels."""
        return {
            AlertUrgency.URGENT: "🚨 URGENT",
            AlertUrgency.IMPORTANT: "⚡ IMPORTANT",
            AlertUrgency.WARNING: "⚠️ WARNING",
            AlertUrgency.INFO: "✅ INFO"
        }


class EmailProviderFactory:
    """Factory for creating email providers with validation."""
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> Optional[EmailProvider]:
        """
        Create email provider from configuration.
        
        Args:
            config: Configuration dictionary with email settings
            
        Returns:
            EmailProvider if configuration is valid, None otherwise
        """
        required_fields = ['smtp_server', 'smtp_port', 'username', 'password', 'recipient']
        
        if not all(config.get(field) for field in required_fields):
            logger.warning("Email configuration incomplete")
            return None
        
        try:
            return EmailProvider(
                smtp_server=config['smtp_server'],
                smtp_port=int(config['smtp_port']),
                username=config['username'],
                password=config['password'],
                recipient=config['recipient']
            )
        except Exception as e:
            logger.error(f"Failed to create email provider: {e}")
            return None
