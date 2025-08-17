"""
Discord notification provider implementation.

Sends notifications to Discord using webhooks with rich formatting
and proper error handling.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from discord_webhook import DiscordWebhook, DiscordEmbed
    DISCORD_AVAILABLE = True
except ImportError:
    DISCORD_AVAILABLE = False
    DiscordWebhook = None
    DiscordEmbed = None

from ..domain.interfaces import BaseNotificationProvider
from ..domain.models import Alert
from ..domain.enums import AlertUrgency, AlertType
from ..domain.exceptions import DiscordNotificationError, NotificationProviderNotConfiguredError

logger = logging.getLogger(__name__)


class DiscordProvider(BaseNotificationProvider):
    """
    Discord notification provider using webhooks.
    
    Sends formatted messages to Discord with rich embeds for better visibility.
    """
    
    def __init__(self, webhook_url: str):
        super().__init__("discord")
        
        if not DISCORD_AVAILABLE:
            raise NotificationProviderNotConfiguredError(
                "discord-webhook package not available. Install with: pip install discord-webhook"
            )
        
        if not webhook_url or not webhook_url.startswith('https://'):
            raise NotificationProviderNotConfiguredError(
                "Valid Discord webhook URL required"
            )
        
        self.webhook_url = webhook_url
        self._color_map = self._create_color_map()
        self._emoji_map = self._create_emoji_map()
        
        logger.info("Discord provider initialized")
    
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert to Discord with rich formatting."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)
            
            # Create rich embed for the alert
            embed = self._create_alert_embed(alert)
            webhook.add_embed(embed)
            
            # Execute webhook
            response = webhook.execute()
            
            if response.status_code == 200:
                logger.debug(f"Discord alert sent successfully for {alert.player.name}")
                return True
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            raise DiscordNotificationError(
                "Failed to send Discord notification",
                details=str(e)
            )
    
    async def send_message(self, message: str, urgency: AlertUrgency = AlertUrgency.INFO) -> bool:
        """Send a simple text message to Discord."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)
            
            # Create simple embed for the message
            embed = self._create_message_embed(message, urgency)
            webhook.add_embed(embed)
            
            response = webhook.execute()
            
            if response.status_code == 200:
                logger.debug(f"Discord message sent successfully")
                return True
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
    
    async def send_lineup_summary(self, match_summaries: list) -> bool:
        """Send a comprehensive lineup summary for all matches with confirmed lineups."""
        try:
            webhook = DiscordWebhook(url=self.webhook_url)
            
            # Create rich embed for lineup summary
            embed = self._create_lineup_summary_embed(match_summaries)
            webhook.add_embed(embed)
            
            response = webhook.execute()
            
            if response.status_code == 200:
                logger.debug(f"Discord lineup summary sent successfully")
                return True
            else:
                logger.error(f"Discord webhook failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Discord lineup summary: {e}")
            return False

    async def test_connection(self) -> bool:
        """Test Discord webhook connection."""
        try:
            test_message = f"🧪 Discord connection test - {datetime.now().strftime('%H:%M:%S')}"
            return await self.send_message(test_message, AlertUrgency.INFO)
            
        except Exception as e:
            logger.error(f"Discord connection test failed: {e}")
            return False
    
    def _create_alert_embed(self, alert: Alert) -> DiscordEmbed:
        """Create a rich Discord embed for an alert."""
        embed = DiscordEmbed(
            title=f"{alert.emoji} {alert.alert_type.value.replace('_', ' ').title()}",
            description=alert.message,
            color=self._color_map.get(alert.urgency, 0x808080)
        )
        
        # Add player information
        embed.add_embed_field(
            name="Player",
            value=f"**{alert.player.name}**\n{alert.player.position.value}",
            inline=True
        )
        
        # Add team information
        embed.add_embed_field(
            name="Team",
            value=f"**{alert.player.team.name}**\n({alert.player.team.abbreviation})",
            inline=True
        )
        
        # Add match information
        match_info = f"**{alert.match.home_team.name}** vs **{alert.match.away_team.name}**\n"
        match_info += f"🕐 {alert.match.kickoff.strftime('%H:%M')}"
        
        embed.add_embed_field(
            name="Match",
            value=match_info,
            inline=True
        )
        
        # Add fantasy data if available
        if alert.player.average_points > 0:
            fantasy_info = f"**Avg Points:** {alert.player.average_points:.1f}\n"
            fantasy_info += f"**Total Points:** {alert.player.fantasy_points:.1f}"
            
            if alert.player.games_played:
                fantasy_info += f"\n**Games:** {alert.player.games_played}"
            
            embed.add_embed_field(
                name="Fantasy Stats",
                value=fantasy_info,
                inline=True
            )
        
        # Add timestamp and footer
        embed.set_timestamp()
        embed.set_footer(text="Fantrax Lineup Monitor")
        
        return embed
    
    def _create_message_embed(self, message: str, urgency: AlertUrgency) -> DiscordEmbed:
        """Create a simple Discord embed for a text message."""
        emoji = self._emoji_map.get(urgency, "📝")
        title = f"{emoji} {urgency.value.title()} Update"
        
        embed = DiscordEmbed(
            title=title,
            description=message,
            color=self._color_map.get(urgency, 0x808080)
        )
        
        embed.set_timestamp()
        embed.set_footer(text="Fantrax Lineup Monitor")
        
        return embed
    
    def _create_lineup_summary_embed(self, match_summaries: list) -> DiscordEmbed:
        """Create a rich Discord embed for lineup summaries."""
        total_matches = len(match_summaries)
        total_players = sum(len(summary.get('players', [])) for summary in match_summaries)
        
        embed = DiscordEmbed(
            title="📋 Lineup Summary - Confirmed Lineups",
            description=f"**{total_matches}** matches with confirmed lineups • **{total_players}** squad players tracked",
            color=0x36a64f  # Green
        )
        
        for match_summary in match_summaries:
            match_info = match_summary.get('match', {})
            players = match_summary.get('players', [])
            
            # Match header
            match_title = f"{match_info.get('home_team', 'TBD')} vs {match_info.get('away_team', 'TBD')}"
            kickoff_time = match_info.get('kickoff', 'TBD')
            if kickoff_time != 'TBD':
                match_title += f" • {kickoff_time}"
            
            # Separate starting and benched players
            starting_players = [p for p in players if p.get('is_starting', False)]
            benched_players = [p for p in players if not p.get('is_starting', False)]
            
            # Format player lists
            lineup_text = ""
            
            if starting_players:
                lineup_text += "🟢 **Starting:**\n"
                for player in starting_players:
                    lineup_text += f"• {player.get('name', 'Unknown')} ({player.get('position', 'Unknown')})\n"
            
            if benched_players:
                if starting_players:
                    lineup_text += "\n"
                lineup_text += "🔴 **Benched:**\n"
                for player in benched_players:
                    lineup_text += f"• {player.get('name', 'Unknown')} ({player.get('position', 'Unknown')})\n"
            
            if not lineup_text:
                lineup_text = "No squad players in this match"
            
            # Add field for this match
            embed.add_embed_field(
                name=match_title,
                value=lineup_text[:1024],  # Discord field value limit
                inline=False
            )
        
        embed.set_timestamp()
        embed.set_footer(text="Fantrax Lineup Monitor • SofaScore Data")
        
        return embed
    
    def _create_color_map(self) -> Dict[AlertUrgency, int]:
        """Create color mapping for Discord embeds."""
        return {
            AlertUrgency.URGENT: 0xff0000,    # Red
            AlertUrgency.IMPORTANT: 0xff9900, # Orange
            AlertUrgency.WARNING: 0xffaa00,   # Yellow
            AlertUrgency.INFO: 0x36a64f       # Green
        }
    
    def _create_emoji_map(self) -> Dict[AlertUrgency, str]:
        """Create emoji mapping for urgency levels."""
        return {
            AlertUrgency.URGENT: "🚨",
            AlertUrgency.IMPORTANT: "⚡",
            AlertUrgency.WARNING: "⚠️",
            AlertUrgency.INFO: "ℹ️"
        }


class DiscordProviderFactory:
    """Factory for creating Discord providers with validation."""
    
    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> Optional[DiscordProvider]:
        """
        Create Discord provider from configuration.
        
        Args:
            config: Configuration dictionary with 'webhook_url' key
            
        Returns:
            DiscordProvider if configuration is valid, None otherwise
        """
        if not config.get('webhook_url'):
            logger.warning("Discord webhook URL not configured")
            return None
        
        try:
            return DiscordProvider(config['webhook_url'])
        except Exception as e:
            logger.error(f"Failed to create Discord provider: {e}")
            return None
    
    @staticmethod
    def is_available() -> bool:
        """Check if Discord provider dependencies are available."""
        return DISCORD_AVAILABLE
