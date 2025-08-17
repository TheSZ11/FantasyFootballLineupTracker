"""
Notification service for coordinating multiple notification providers.

Manages sending alerts through various channels (email, Discord, etc.)
with proper routing based on alert urgency and provider availability.
"""

from typing import List, Dict, Optional
import logging
from datetime import datetime

from ..domain.interfaces import NotificationProvider
from ..domain.models import Alert
from ..domain.enums import AlertUrgency, NotificationType
from ..domain.exceptions import NotificationError

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service for managing and coordinating notification providers.
    
    Routes alerts to appropriate providers based on urgency and configuration,
    handles fallbacks, and provides notification statistics.
    """
    
    def __init__(self, providers: List[NotificationProvider]):
        self.providers = {provider.provider_name: provider for provider in providers}
        self._notification_stats = {
            'total_sent': 0,
            'total_failed': 0,
            'by_provider': {},
            'by_urgency': {},
            'last_notification': None
        }
        
        logger.info(f"Notification service initialized with providers: {list(self.providers.keys())}")
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert through appropriate notification channels.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if at least one notification was sent successfully
        """
        logger.info(f"Sending {alert.urgency.value} alert for {alert.player.name}")
        
        success_count = 0
        total_attempts = 0
        
        # Determine which providers to use based on urgency
        target_providers = self._get_providers_for_urgency(alert.urgency)
        
        if not target_providers:
            logger.warning(f"No providers configured for {alert.urgency.value} alerts")
            return False
        
        # Send to each target provider
        for provider_name in target_providers:
            if provider_name not in self.providers:
                logger.warning(f"Provider {provider_name} not available")
                continue
            
            provider = self.providers[provider_name]
            total_attempts += 1
            
            try:
                result = await provider.send_alert(alert)
                if result:
                    success_count += 1
                    self._record_notification_success(provider_name, alert.urgency)
                    logger.debug(f"Alert sent successfully via {provider_name}")
                else:
                    self._record_notification_failure(provider_name, alert.urgency)
                    logger.warning(f"Alert failed to send via {provider_name}")
                    
            except Exception as e:
                self._record_notification_failure(provider_name, alert.urgency)
                logger.error(f"Error sending alert via {provider_name}: {e}")
        
        # Update statistics
        if success_count > 0:
            self._notification_stats['total_sent'] += 1
        else:
            self._notification_stats['total_failed'] += 1
        
        self._notification_stats['last_notification'] = datetime.now()
        
        # Log results
        if success_count == 0:
            logger.error(f"Alert failed to send via all {total_attempts} providers")
            return False
        elif success_count < total_attempts:
            logger.warning(f"Alert sent via {success_count}/{total_attempts} providers")
            return True
        else:
            logger.info(f"Alert sent successfully via all {success_count} providers")
            return True
    
    async def send_message(self, message: str, urgency: AlertUrgency = AlertUrgency.INFO) -> bool:
        """
        Send a simple text message.
        
        Args:
            message: Text message to send
            urgency: Urgency level for routing
            
        Returns:
            True if message was sent successfully
        """
        logger.info(f"Sending {urgency.value} message")
        
        target_providers = self._get_providers_for_urgency(urgency)
        success_count = 0
        
        for provider_name in target_providers:
            if provider_name not in self.providers:
                continue
            
            provider = self.providers[provider_name]
            
            try:
                result = await provider.send_message(message, urgency)
                if result:
                    success_count += 1
                    logger.debug(f"Message sent successfully via {provider_name}")
                    
            except Exception as e:
                logger.error(f"Error sending message via {provider_name}: {e}")
        
        return success_count > 0
    
    async def send_startup_notification(self) -> bool:
        """Send notification that the monitoring system has started."""
        message = f"🚀 Fantrax Lineup Monitor started at {datetime.now().strftime('%H:%M:%S')}"
        return await self.send_message(message, AlertUrgency.INFO)
    
    async def send_shutdown_notification(self) -> bool:
        """Send notification that the monitoring system is shutting down."""
        message = f"📴 Fantrax Lineup Monitor stopped at {datetime.now().strftime('%H:%M:%S')}"
        return await self.send_message(message, AlertUrgency.INFO)
    
    async def send_error_notification(self, error_message: str) -> bool:
        """Send error notification."""
        return await self.send_message(error_message, AlertUrgency.WARNING)
    
    async def send_lineup_summary(self, match_summaries: list) -> bool:
        """Send lineup summary through Discord provider."""
        if not match_summaries:
            logger.debug("No match summaries to send")
            return True
        
        # Only send through Discord provider (avoid email spam)
        discord_providers = [name for name in self.providers.keys() if 'discord' in name.lower()]
        
        if not discord_providers:
            logger.warning("No Discord provider available for lineup summary")
            return False
        
        success_count = 0
        for provider_name in discord_providers:
            provider = self.providers[provider_name]
            
            # Check if provider has send_lineup_summary method
            if hasattr(provider, 'send_lineup_summary'):
                try:
                    result = await provider.send_lineup_summary(match_summaries)
                    if result:
                        success_count += 1
                        logger.info(f"Lineup summary sent successfully via {provider_name}")
                    else:
                        logger.warning(f"Lineup summary failed to send via {provider_name}")
                        
                except Exception as e:
                    logger.error(f"Error sending lineup summary via {provider_name}: {e}")
            else:
                logger.warning(f"Provider {provider_name} doesn't support lineup summaries")
        
        return success_count > 0

    async def send_cycle_summary(self, cycle_result: Dict) -> bool:
        """Send monitoring cycle summary."""
        if cycle_result['status'] == 'Success' and cycle_result['alerts_generated'] == 0:
            # Don't send summary for successful cycles with no alerts
            return True
        
        message = self._format_cycle_summary(cycle_result)
        urgency = AlertUrgency.WARNING if 'Error' in cycle_result['status'] else AlertUrgency.INFO
        
        return await self.send_message(message, urgency)
    
    async def test_all_providers(self) -> Dict[str, bool]:
        """
        Test all notification providers.
        
        Returns:
            Dictionary mapping provider names to test results
        """
        logger.info("Testing all notification providers")
        
        results = {}
        
        for provider_name, provider in self.providers.items():
            try:
                result = await provider.test_connection()
                results[provider_name] = result
                logger.info(f"Provider {provider_name}: {'✅ Success' if result else '❌ Failed'}")
                
            except Exception as e:
                results[provider_name] = False
                logger.error(f"Provider {provider_name} test failed: {e}")
        
        return results
    
    def _get_providers_for_urgency(self, urgency: AlertUrgency) -> List[str]:
        """Get list of provider names to use for given urgency level."""
        # Email + Discord for urgent and important alerts
        if urgency in [AlertUrgency.URGENT, AlertUrgency.IMPORTANT]:
            return [name for name in self.providers.keys()]
        
        # Discord only for info and warnings (to avoid email spam)
        else:
            return [name for name in self.providers.keys() if 'discord' in name.lower()]
    
    def _record_notification_success(self, provider_name: str, urgency: AlertUrgency):
        """Record successful notification for statistics."""
        if provider_name not in self._notification_stats['by_provider']:
            self._notification_stats['by_provider'][provider_name] = {'sent': 0, 'failed': 0}
        
        if urgency.value not in self._notification_stats['by_urgency']:
            self._notification_stats['by_urgency'][urgency.value] = {'sent': 0, 'failed': 0}
        
        self._notification_stats['by_provider'][provider_name]['sent'] += 1
        self._notification_stats['by_urgency'][urgency.value]['sent'] += 1
    
    def _record_notification_failure(self, provider_name: str, urgency: AlertUrgency):
        """Record failed notification for statistics."""
        if provider_name not in self._notification_stats['by_provider']:
            self._notification_stats['by_provider'][provider_name] = {'sent': 0, 'failed': 0}
        
        if urgency.value not in self._notification_stats['by_urgency']:
            self._notification_stats['by_urgency'][urgency.value] = {'sent': 0, 'failed': 0}
        
        self._notification_stats['by_provider'][provider_name]['failed'] += 1
        self._notification_stats['by_urgency'][urgency.value]['failed'] += 1
    
    def _format_cycle_summary(self, cycle_result: Dict) -> str:
        """Format monitoring cycle summary message."""
        status_emoji = "✅" if cycle_result['status'] == 'Success' else "⚠️"
        
        message = f"{status_emoji} Monitoring Cycle Complete\n\n"
        message += f"**Status:** {cycle_result['status']}\n"
        message += f"**Duration:** {cycle_result['duration_seconds']:.1f}s\n"
        message += f"**Matches Checked:** {cycle_result['matches_processed']}\n"
        message += f"**Alerts Generated:** {cycle_result['alerts_generated']}\n"
        
        if cycle_result.get('statistics'):
            stats = cycle_result['statistics']
            message += f"\n**Total Cycles:** {stats['cycles_run']}\n"
            message += f"**Total Matches:** {stats['matches_checked']}\n"
            message += f"**Total Alerts:** {stats['alerts_generated']}\n"
        
        return message
    
    def get_notification_statistics(self) -> Dict:
        """Get notification statistics."""
        return self._notification_stats.copy()
    
    def reset_statistics(self):
        """Reset notification statistics."""
        self._notification_stats = {
            'total_sent': 0,
            'total_failed': 0,
            'by_provider': {},
            'by_urgency': {},
            'last_notification': None
        }
    
    def get_provider_status(self) -> Dict[str, Dict]:
        """Get status of all providers."""
        status = {}
        
        for provider_name, provider in self.providers.items():
            provider_stats = self._notification_stats['by_provider'].get(provider_name, {'sent': 0, 'failed': 0})
            
            status[provider_name] = {
                'available': True,  # Provider is registered
                'total_sent': provider_stats['sent'],
                'total_failed': provider_stats['failed'],
                'success_rate': (
                    provider_stats['sent'] / (provider_stats['sent'] + provider_stats['failed'])
                    if provider_stats['sent'] + provider_stats['failed'] > 0 else 1.0
                )
            }
        
        return status
    
    def add_provider(self, provider: NotificationProvider) -> None:
        """Add a new notification provider."""
        self.providers[provider.provider_name] = provider
        logger.info(f"Added notification provider: {provider.provider_name}")
    
    def remove_provider(self, provider_name: str) -> bool:
        """Remove a notification provider."""
        if provider_name in self.providers:
            del self.providers[provider_name]
            logger.info(f"Removed notification provider: {provider_name}")
            return True
        
        logger.warning(f"Provider {provider_name} not found")
        return False
