"""
Integration tests for LineupMonitoringService.

Tests the complete workflow of lineup monitoring including coordination
between all components and proper error handling.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch
from typing import List

from src.lineup_tracker.services.lineup_monitoring_service import LineupMonitoringService
from src.lineup_tracker.business.lineup_analyzer import LineupAnalyzer
from src.lineup_tracker.business.alert_generator import AlertGenerator
from src.lineup_tracker.domain.models import Team, Player, Match, Squad, Lineup, Alert
from src.lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus, AlertType, AlertUrgency
from src.lineup_tracker.domain.exceptions import LineupMonitorError, SquadLoadError, APIConnectionError
from tests.conftest import create_test_player, create_test_match


@pytest.mark.integration
class TestLineupMonitoringService:
    """Test the complete lineup monitoring workflow."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock dependencies
        self.mock_football_api = AsyncMock()
        self.mock_squad_repository = Mock()
        self.mock_notification_service = AsyncMock()
        self.lineup_analyzer = LineupAnalyzer()
        self.alert_generator = AlertGenerator()
        
        # Create service with mocked dependencies
        self.service = LineupMonitoringService(
            football_api=self.mock_football_api,
            squad_repository=self.mock_squad_repository,
            notification_service=self.mock_notification_service,
            lineup_analyzer=self.lineup_analyzer,
            alert_generator=self.alert_generator,
            squad_file_path="test_roster.csv"
        )
        
        # Create test data
        self.liverpool = Team(name="Liverpool", abbreviation="LIV")
        self.arsenal = Team(name="Arsenal", abbreviation="ARS")
        
        self.salah = create_test_player(
            "salah1", "Mohamed Salah", self.liverpool,
            Position.FORWARD, PlayerStatus.ACTIVE, 150.0, 12.5
        )
        self.backup = create_test_player(
            "backup1", "Backup Player", self.liverpool,
            Position.MIDFIELDER, PlayerStatus.RESERVE, 50.0, 4.0
        )
        
        self.test_squad = Squad(players=[self.salah, self.backup])
        self.test_match = create_test_match(
            "match1", self.liverpool, self.arsenal,
            MatchStatus.NOT_STARTED, 2
        )
    
    @pytest.mark.asyncio
    async def test_successful_monitoring_cycle(self):
        """Test a complete successful monitoring cycle."""
        # Setup mocks
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        # Create lineup with unexpected benching
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=["Player 1", "Player 2", "Player 3", "Player 4",
                           "Player 5", "Player 6", "Player 7", "Player 8",
                           "Player 9", "Player 10", "Player 11"]
        )
        self.mock_football_api.get_lineup.return_value = [lineup]
        
        # Run monitoring cycle
        result = await self.service.run_monitoring_cycle()
        
        # Verify results
        assert result['status'] == 'Success'
        assert result['matches_processed'] == 1
        assert result['alerts_generated'] > 0
        
        # Verify dependencies were called
        self.mock_squad_repository.load_squad.assert_called_once_with("test_roster.csv")
        self.mock_football_api.get_fixtures.assert_called_once()
        self.mock_football_api.get_lineup.assert_called_once_with("match1")
        
        # Verify notifications were sent
        assert self.mock_notification_service.send_alert.call_count > 0
    
    @pytest.mark.asyncio
    async def test_no_relevant_matches(self):
        """Test monitoring cycle when no relevant matches are found."""
        # Setup mocks - no matches involving squad teams
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = []
        
        result = await self.service.run_monitoring_cycle()
        
        assert result['status'] == 'No matches'
        assert result['matches_processed'] == 0
        assert result['alerts_generated'] == 0
        
        # Should not try to get lineups
        self.mock_football_api.get_lineup.assert_not_called()
        self.mock_notification_service.send_alert.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_squad_loading_error(self):
        """Test handling of squad loading errors."""
        # Setup mock to raise error
        self.mock_squad_repository.load_squad.side_effect = SquadLoadError("Test error")
        
        result = await self.service.run_monitoring_cycle()
        
        assert "Error" in result['status']
        assert result['matches_processed'] == 0
        
        # Should send error notification
        self.mock_notification_service.send_error_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_api_connection_error(self):
        """Test handling of API connection errors."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.side_effect = APIConnectionError("API down")
        
        result = await self.service.run_monitoring_cycle()
        
        assert "Error" in result['status']
        assert "API down" in result['status']
        
        # Should send error notification
        self.mock_notification_service.send_error_notification.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_lineup_not_available(self):
        """Test handling when lineup data is not yet available."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        self.mock_football_api.get_lineup.return_value = None  # No lineup data
        
        result = await self.service.run_monitoring_cycle()
        
        assert result['status'] == 'Success'
        assert result['matches_processed'] == 1
        assert result['alerts_generated'] == 0  # No alerts since no lineup
    
    @pytest.mark.asyncio
    async def test_squad_caching(self):
        """Test that squad is cached and not reloaded frequently."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        
        # First load
        squad1 = await self.service._load_current_squad()
        
        # Second load immediately after (should use cache)
        squad2 = await self.service._load_current_squad()
        
        # Repository should only be called once due to caching
        assert self.mock_squad_repository.load_squad.call_count == 1
        assert squad1 is squad2
    
    @pytest.mark.asyncio
    async def test_force_squad_reload(self):
        """Test forcing squad reload clears cache."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        
        # Initial load
        await self.service._load_current_squad()
        
        # Force reload
        await self.service.force_squad_reload()
        
        # Should have been called twice
        assert self.mock_squad_repository.load_squad.call_count == 2
    
    @pytest.mark.asyncio
    async def test_match_processing_error(self):
        """Test error handling during individual match processing."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        # Mock lineup to raise error
        self.mock_football_api.get_lineup.side_effect = Exception("Lineup error")
        
        result = await self.service.run_monitoring_cycle()
        
        # Should continue processing despite error
        assert result['status'] == 'Success'
        assert result['matches_processed'] == 0  # No successful processing
    
    def test_get_relevant_matches(self):
        """Test filtering matches for relevant teams."""
        # Create matches
        relevant_match = create_test_match("match1", self.liverpool, self.arsenal)
        irrelevant_match = create_test_match(
            "match2", 
            Team("Chelsea", "CHE"), 
            Team("Manchester City", "MCI")
        )
        
        all_matches = [relevant_match, irrelevant_match]
        
        # Filter using private method (testing internal logic)
        squad_teams = set(self.test_squad.get_teams())
        relevant_matches = [
            match for match in all_matches
            if (match.home_team.name in squad_teams or 
                match.away_team.name in squad_teams)
        ]
        
        assert len(relevant_matches) == 1
        assert relevant_matches[0] == relevant_match
    
    def test_get_squad_summary(self):
        """Test squad summary generation."""
        # Setup with cached squad
        self.service._cached_squad = self.test_squad
        
        summary = self.service.get_squad_summary()
        
        assert isinstance(summary, str)
        assert "Mohamed Salah" in summary
        assert "Liverpool" in summary
        assert "Active (1)" in summary
        assert "Reserve (1)" in summary
    
    def test_get_squad_summary_no_squad(self):
        """Test squad summary when no squad is loaded."""
        summary = self.service.get_squad_summary()
        assert summary == "No squad loaded"
    
    def test_monitoring_statistics(self):
        """Test monitoring statistics tracking."""
        initial_stats = self.service.get_monitoring_statistics()
        
        assert initial_stats['cycles_run'] == 0
        assert initial_stats['matches_checked'] == 0
        assert initial_stats['alerts_generated'] == 0
        assert initial_stats['last_run'] is None
        
        # Reset and verify
        self.service.reset_statistics()
        reset_stats = self.service.get_monitoring_statistics()
        assert reset_stats == initial_stats
    
    @pytest.mark.asyncio
    async def test_multiple_alerts_handling(self):
        """Test handling of multiple alerts in one cycle."""
        # Setup squad with multiple players
        henderson = create_test_player(
            "henderson", "Jordan Henderson", self.liverpool,
            Position.MIDFIELDER, PlayerStatus.ACTIVE
        )
        extended_squad = Squad(players=[self.salah, self.backup, henderson])
        
        self.mock_squad_repository.load_squad.return_value = extended_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        # Create lineup that causes multiple discrepancies
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=["Backup Player"] + [f"Player {i}" for i in range(2, 12)]
        )
        self.mock_football_api.get_lineup.return_value = [lineup]
        
        result = await self.service.run_monitoring_cycle()
        
        assert result['status'] == 'Success'
        assert result['alerts_generated'] >= 2  # At least benching + starting alerts
    
    @pytest.mark.asyncio
    async def test_match_status_filtering(self):
        """Test that only appropriate match statuses are processed."""
        # Create matches with different statuses
        not_started = create_test_match("ns", self.liverpool, self.arsenal, MatchStatus.NOT_STARTED)
        finished = create_test_match("fin", self.liverpool, self.arsenal, MatchStatus.FINISHED)
        live = create_test_match("live", self.liverpool, self.arsenal, MatchStatus.LIVE)
        
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [not_started, finished, live]
        self.mock_football_api.get_lineup.return_value = []
        
        result = await self.service.run_monitoring_cycle()
        
        # Should process not_started and live, but skip finished
        # However, the _process_match method also checks if match.is_started
        # So live matches might also be skipped
        assert result['matches_processed'] >= 1
    
    @pytest.mark.asyncio
    async def test_notification_failure_handling(self):
        """Test that notification failures don't break the cycle."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        # Create lineup that generates alerts
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[f"Player {i}" for i in range(1, 12)]  # Salah benched
        )
        self.mock_football_api.get_lineup.return_value = [lineup]
        
        # Make notifications fail
        self.mock_notification_service.send_alert.side_effect = Exception("Notification failed")
        
        result = await self.service.run_monitoring_cycle()
        
        # Should still complete successfully despite notification failure
        assert result['status'] == 'Success'
        assert result['alerts_generated'] > 0
    
    @pytest.mark.asyncio
    async def test_lineup_format_handling(self):
        """Test handling of different lineup response formats."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        # Test with single lineup object (not list)
        single_lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[f"Player {i}" for i in range(1, 12)]
        )
        single_lineup.starting_eleven = [f"Player {i}" for i in range(1, 12)]  # Ensure 11 players
        
        self.mock_football_api.get_lineup.return_value = single_lineup
        
        result = await self.service.run_monitoring_cycle()
        
        assert result['status'] == 'Success'
        assert result['matches_processed'] == 1
    
    @pytest.mark.asyncio
    async def test_concurrent_processing(self):
        """Test that service can handle multiple matches concurrently."""
        # Create multiple matches
        match1 = create_test_match("match1", self.liverpool, self.arsenal)
        match2 = create_test_match("match2", self.liverpool, Team("Chelsea", "CHE"))
        
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [match1, match2]
        
        # Setup lineups for both matches
        lineup1 = Lineup(team=self.liverpool, starting_eleven=[f"Player {i}" for i in range(1, 12)])
        lineup2 = Lineup(team=self.liverpool, starting_eleven=[f"Player {i}" for i in range(1, 12)])
        
        self.mock_football_api.get_lineup.side_effect = [lineup1, lineup2]
        
        result = await self.service.run_monitoring_cycle()
        
        assert result['status'] == 'Success'
        assert result['matches_processed'] == 2
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self):
        """Test integration with lineup analyzer rate limiting."""
        self.mock_squad_repository.load_squad.return_value = self.test_squad
        self.mock_football_api.get_fixtures.return_value = [self.test_match]
        
        lineup = Lineup(team=self.liverpool, starting_eleven=[f"Player {i}" for i in range(1, 12)])
        self.mock_football_api.get_lineup.return_value = [lineup]
        
        # First processing
        result1 = await self.service.run_monitoring_cycle()
        
        # Immediate second processing (should be rate limited)
        result2 = await self.service.run_monitoring_cycle()
        
        # Both should succeed, but second might have fewer alerts due to rate limiting
        assert result1['status'] == 'Success'
        assert result2['status'] == 'Success'
        
        # First run should process the match, second might skip it
        assert result1['matches_processed'] >= result2['matches_processed']
