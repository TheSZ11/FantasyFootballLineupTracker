"""
Integration tests for NotificationService.

Tests the coordination of multiple notification providers and
proper routing based on alert urgency.
"""

import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime

from src.lineup_tracker.services.notification_service import NotificationService
from src.lineup_tracker.domain.models import Alert, Team, Player, Match
from src.lineup_tracker.domain.enums import AlertType, AlertUrgency, Position, PlayerStatus, MatchStatus
from src.lineup_tracker.domain.exceptions import NotificationError
from tests.conftest import create_test_player, create_test_match


@pytest.mark.integration
class TestNotificationService:
    """Test the notification service coordination."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock providers
        self.mock_discord_provider = AsyncMock()
        self.mock_discord_provider.provider_name = "discord"
        self.mock_discord_provider.send_alert.return_value = True
        self.mock_discord_provider.send_message.return_value = True
        self.mock_discord_provider.test_connection.return_value = True
        
        self.mock_email_provider = AsyncMock()
        self.mock_email_provider.provider_name = "email"
        self.mock_email_provider.send_alert.return_value = True
        self.mock_email_provider.send_message.return_value = True
        self.mock_email_provider.test_connection.return_value = True
        
        # Create service with both providers
        self.service = NotificationService([
            self.mock_discord_provider,
            self.mock_email_provider
        ])
        
        # Create test data
        self.liverpool = Team(name="Liverpool", abbreviation="LIV")
        self.arsenal = Team(name="Arsenal", abbreviation="ARS")
        
        self.salah = create_test_player(
            "salah1", "Mohamed Salah", self.liverpool,
            Position.FORWARD, PlayerStatus.ACTIVE, 150.0, 12.5
        )
        
        self.test_match = create_test_match(
            "match1", self.liverpool, self.arsenal,
            MatchStatus.NOT_STARTED, 2
        )
        
        # Create test alerts
        self.urgent_alert = Alert(
            player=self.salah,
            match=self.test_match,
            alert_type=AlertType.UNEXPECTED_BENCHING,
            urgency=AlertUrgency.URGENT,
            message="Test urgent alert"
        )
        
        self.info_alert = Alert(
            player=self.salah,
            match=self.test_match,
            alert_type=AlertType.LINEUP_CONFIRMED,
            urgency=AlertUrgency.INFO,
            message="Test info alert"
        )
    
    @pytest.mark.asyncio
    async def test_urgent_alert_routing(self):
        """Test that urgent alerts go to all providers."""
        result = await self.service.send_alert(self.urgent_alert)
        
        assert result is True
        
        # Both providers should receive urgent alerts
        self.mock_discord_provider.send_alert.assert_called_once_with(self.urgent_alert)
        self.mock_email_provider.send_alert.assert_called_once_with(self.urgent_alert)
    
    @pytest.mark.asyncio
    async def test_info_alert_routing(self):
        """Test that info alerts only go to Discord (not email)."""
        result = await self.service.send_alert(self.info_alert)
        
        assert result is True
        
        # Only Discord should receive info alerts
        self.mock_discord_provider.send_alert.assert_called_once_with(self.info_alert)
        self.mock_email_provider.send_alert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_provider_failure_handling(self):
        """Test handling when one provider fails."""
        # Make email provider fail
        self.mock_email_provider.send_alert.return_value = False
        
        result = await self.service.send_alert(self.urgent_alert)
        
        # Should still return True if at least one provider succeeds
        assert result is True
        
        # Both should be attempted
        self.mock_discord_provider.send_alert.assert_called_once()
        self.mock_email_provider.send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_all_providers_fail(self):
        """Test handling when all providers fail."""
        self.mock_discord_provider.send_alert.return_value = False
        self.mock_email_provider.send_alert.return_value = False
        
        result = await self.service.send_alert(self.urgent_alert)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_provider_exception_handling(self):
        """Test handling when providers raise exceptions."""
        self.mock_email_provider.send_alert.side_effect = Exception("Email failed")
        
        result = await self.service.send_alert(self.urgent_alert)
        
        # Should still succeed if Discord works
        assert result is True
        
        # Both should be attempted despite exception
        self.mock_discord_provider.send_alert.assert_called_once()
        self.mock_email_provider.send_alert.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_routing(self):
        """Test message routing based on urgency."""
        # Urgent message should go to all providers
        result = await self.service.send_message("Urgent message", AlertUrgency.URGENT)
        assert result is True
        
        self.mock_discord_provider.send_message.assert_called_with("Urgent message", AlertUrgency.URGENT)
        self.mock_email_provider.send_message.assert_called_with("Urgent message", AlertUrgency.URGENT)
        
        # Reset mocks
        self.mock_discord_provider.reset_mock()
        self.mock_email_provider.reset_mock()
        
        # Info message should only go to Discord
        result = await self.service.send_message("Info message", AlertUrgency.INFO)
        assert result is True
        
        self.mock_discord_provider.send_message.assert_called_with("Info message", AlertUrgency.INFO)
        self.mock_email_provider.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_startup_notification(self):
        """Test startup notification."""
        result = await self.service.send_startup_notification()
        
        assert result is True
        
        # Should only go to Discord (info level)
        self.mock_discord_provider.send_message.assert_called_once()
        self.mock_email_provider.send_message.assert_not_called()
        
        # Check message content
        call_args = self.mock_discord_provider.send_message.call_args
        message = call_args[0][0]
        urgency = call_args[0][1]
        
        assert "started" in message.lower()
        assert urgency == AlertUrgency.INFO
    
    @pytest.mark.asyncio
    async def test_shutdown_notification(self):
        """Test shutdown notification."""
        result = await self.service.send_shutdown_notification()
        
        assert result is True
        
        call_args = self.mock_discord_provider.send_message.call_args
        message = call_args[0][0]
        
        assert "stopped" in message.lower()
    
    @pytest.mark.asyncio
    async def test_error_notification(self):
        """Test error notification routing."""
        result = await self.service.send_error_notification("Test error")
        
        assert result is True
        
        # Should only go to Discord (warning level)
        self.mock_discord_provider.send_message.assert_called_once()
        self.mock_email_provider.send_message.assert_not_called()
        
        call_args = self.mock_discord_provider.send_message.call_args
        urgency = call_args[0][1]
        assert urgency == AlertUrgency.WARNING
    
    @pytest.mark.asyncio
    async def test_cycle_summary_with_errors(self):
        """Test cycle summary for failed cycles."""
        cycle_result = {
            'status': 'Error: API failed',
            'duration_seconds': 5.5,
            'matches_processed': 0,
            'alerts_generated': 0,
            'statistics': {'cycles_run': 1}
        }
        
        result = await self.service.send_cycle_summary(cycle_result)
        
        assert result is True
        
        # Should be sent as warning
        call_args = self.mock_discord_provider.send_message.call_args
        urgency = call_args[0][1]
        assert urgency == AlertUrgency.WARNING
    
    @pytest.mark.asyncio
    async def test_cycle_summary_successful_no_alerts(self):
        """Test that successful cycles with no alerts don't send notifications."""
        cycle_result = {
            'status': 'Success',
            'alerts_generated': 0,
            'matches_processed': 2
        }
        
        result = await self.service.send_cycle_summary(cycle_result)
        
        # Should return True but not actually send anything
        assert result is True
        self.mock_discord_provider.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_test_all_providers(self):
        """Test provider testing functionality."""
        results = await self.service.test_all_providers()
        
        assert len(results) == 2
        assert results["discord"] is True
        assert results["email"] is True
        
        self.mock_discord_provider.test_connection.assert_called_once()
        self.mock_email_provider.test_connection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_test_providers_with_failures(self):
        """Test provider testing when some providers fail."""
        self.mock_email_provider.test_connection.return_value = False
        
        results = await self.service.test_all_providers()
        
        assert results["discord"] is True
        assert results["email"] is False
    
    @pytest.mark.asyncio
    async def test_test_providers_with_exceptions(self):
        """Test provider testing when exceptions occur."""
        self.mock_email_provider.test_connection.side_effect = Exception("Test failed")
        
        results = await self.service.test_all_providers()
        
        assert results["discord"] is True
        assert results["email"] is False
    
    def test_notification_statistics_tracking(self):
        """Test that notification statistics are properly tracked."""
        initial_stats = self.service.get_notification_statistics()
        
        assert initial_stats['total_sent'] == 0
        assert initial_stats['total_failed'] == 0
        assert len(initial_stats['by_provider']) == 0
        assert len(initial_stats['by_urgency']) == 0
    
    @pytest.mark.asyncio
    async def test_statistics_updates_on_success(self):
        """Test that statistics update correctly on successful notifications."""
        await self.service.send_alert(self.urgent_alert)
        
        stats = self.service.get_notification_statistics()
        
        assert stats['total_sent'] == 1
        assert stats['total_failed'] == 0
        assert 'discord' in stats['by_provider']
        assert 'email' in stats['by_provider']
        assert 'urgent' in stats['by_urgency']
    
    @pytest.mark.asyncio
    async def test_statistics_updates_on_failure(self):
        """Test that statistics update correctly on failed notifications."""
        self.mock_discord_provider.send_alert.return_value = False
        self.mock_email_provider.send_alert.return_value = False
        
        await self.service.send_alert(self.urgent_alert)
        
        stats = self.service.get_notification_statistics()
        
        assert stats['total_sent'] == 0
        assert stats['total_failed'] == 1
    
    def test_provider_status(self):
        """Test provider status reporting."""
        status = self.service.get_provider_status()
        
        assert 'discord' in status
        assert 'email' in status
        
        discord_status = status['discord']
        assert discord_status['available'] is True
        assert discord_status['total_sent'] == 0
        assert discord_status['total_failed'] == 0
        assert discord_status['success_rate'] == 1.0
    
    def test_add_remove_providers(self):
        """Test dynamic provider management."""
        # Create new mock provider
        new_provider = AsyncMock()
        new_provider.provider_name = "sms"
        
        # Add provider
        self.service.add_provider(new_provider)
        assert "sms" in self.service.providers
        
        # Remove provider
        result = self.service.remove_provider("sms")
        assert result is True
        assert "sms" not in self.service.providers
        
        # Try to remove non-existent provider
        result = self.service.remove_provider("nonexistent")
        assert result is False
    
    def test_reset_statistics(self):
        """Test statistics reset functionality."""
        # Manually set some stats
        self.service._notification_stats['total_sent'] = 5
        self.service._notification_stats['by_provider']['discord'] = {'sent': 3, 'failed': 1}
        
        self.service.reset_statistics()
        
        stats = self.service.get_notification_statistics()
        assert stats['total_sent'] == 0
        assert len(stats['by_provider']) == 0
    
    @pytest.mark.asyncio
    async def test_single_provider_service(self):
        """Test service with only one provider."""
        # Create service with only Discord
        discord_only_service = NotificationService([self.mock_discord_provider])
        
        result = await discord_only_service.send_alert(self.urgent_alert)
        
        assert result is True
        self.mock_discord_provider.send_alert.assert_called_once()
        self.mock_email_provider.send_alert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_no_providers_service(self):
        """Test service with no providers."""
        empty_service = NotificationService([])
        
        result = await empty_service.send_alert(self.urgent_alert)
        
        assert result is False
    
    def test_get_providers_for_urgency(self):
        """Test provider selection logic."""
        # Urgent should get all providers
        urgent_providers = self.service._get_providers_for_urgency(AlertUrgency.URGENT)
        assert len(urgent_providers) == 2
        assert "discord" in urgent_providers
        assert "email" in urgent_providers
        
        # Important should get all providers
        important_providers = self.service._get_providers_for_urgency(AlertUrgency.IMPORTANT)
        assert len(important_providers) == 2
        
        # Info should only get Discord
        info_providers = self.service._get_providers_for_urgency(AlertUrgency.INFO)
        assert len(info_providers) == 1
        assert "discord" in info_providers
        
        # Warning should only get Discord
        warning_providers = self.service._get_providers_for_urgency(AlertUrgency.WARNING)
        assert len(warning_providers) == 1
        assert "discord" in warning_providers
    
    def test_format_cycle_summary(self):
        """Test cycle summary formatting."""
        cycle_result = {
            'status': 'Success',
            'duration_seconds': 12.5,
            'matches_processed': 3,
            'alerts_generated': 2,
            'statistics': {
                'cycles_run': 10,
                'matches_checked': 25,
                'alerts_generated': 15
            }
        }
        
        message = self.service._format_cycle_summary(cycle_result)
        
        assert "✅" in message  # Success emoji
        assert "Success" in message
        assert "12.5s" in message
        assert "3" in message  # matches processed
        assert "2" in message  # alerts generated
        assert "10" in message  # total cycles
    
    def test_format_cycle_summary_error(self):
        """Test cycle summary formatting for errors."""
        cycle_result = {
            'status': 'Error: API failed',
            'duration_seconds': 5.0,
            'matches_processed': 0,
            'alerts_generated': 0
        }
        
        message = self.service._format_cycle_summary(cycle_result)
        
        assert "⚠️" in message  # Warning emoji
        assert "Error: API failed" in message
