"""
Unit tests for LineupAnalyzer business logic.

Tests the core business rules for analyzing lineup discrepancies
between expected fantasy team lineups and actual match lineups.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.lineup_tracker.business.lineup_analyzer import LineupAnalyzer
from src.lineup_tracker.domain.models import Team, Player, Match, Squad, Lineup, LineupDiscrepancy
from src.lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus, AlertType
from tests.conftest import create_test_player, create_test_match


@pytest.mark.unit
class TestLineupAnalyzer:
    """Test the LineupAnalyzer business logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = LineupAnalyzer()
        
        # Create test teams
        self.liverpool = Team(name="Liverpool", abbreviation="LIV")
        self.arsenal = Team(name="Arsenal", abbreviation="ARS")
        
        # Create test players
        self.salah = create_test_player(
            "salah1", "Mohamed Salah", self.liverpool,
            Position.FORWARD, PlayerStatus.ACTIVE, 150.0, 12.5
        )
        self.backup_forward = create_test_player(
            "backup1", "Backup Forward", self.liverpool,
            Position.FORWARD, PlayerStatus.RESERVE, 50.0, 4.0
        )
        self.henderson = create_test_player(
            "henderson1", "Jordan Henderson", self.liverpool,
            Position.MIDFIELDER, PlayerStatus.ACTIVE, 80.0, 6.5
        )
        
        # Create test squad
        self.squad = Squad(players=[self.salah, self.backup_forward, self.henderson])
        
        # Create test match
        self.match = create_test_match(
            "match1", self.liverpool, self.arsenal, 
            MatchStatus.NOT_STARTED, 2
        )
    
    def test_analyze_match_lineups_no_discrepancies(self):
        """Test analysis when lineups match expectations."""
        # Create lineup with expected players starting
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[
                "Mohamed Salah", "Jordan Henderson", "Player 3", "Player 4",
                "Player 5", "Player 6", "Player 7", "Player 8",
                "Player 9", "Player 10", "Player 11"
            ]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [lineup], self.squad
        )
        
        # Should have 3 discrepancies (for all 3 players in squad)
        assert len(discrepancies) == 3
        
        # Both should be "as expected"
        for discrepancy in discrepancies:
            assert discrepancy.discrepancy_type == AlertType.LINEUP_CONFIRMED
            assert discrepancy.expected_starting == discrepancy.actually_starting
    
    def test_analyze_match_lineups_unexpected_benching(self):
        """Test detection of unexpected player benching."""
        # Create lineup without Salah (who is expected to start)
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[
                "Jordan Henderson", "Player 2", "Player 3", "Player 4",
                "Player 5", "Player 6", "Player 7", "Player 8",
                "Player 9", "Player 10", "Player 11"
            ]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [lineup], self.squad
        )
        
        # Find Salah's discrepancy
        salah_discrepancy = next(
            d for d in discrepancies 
            if d.player.name == "Mohamed Salah"
        )
        
        assert salah_discrepancy.discrepancy_type == AlertType.UNEXPECTED_BENCHING
        assert salah_discrepancy.expected_starting is True
        assert salah_discrepancy.actually_starting is False
    
    def test_analyze_match_lineups_unexpected_starting(self):
        """Test detection of unexpected player starting."""
        # Create lineup with backup forward starting
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[
                "Mohamed Salah", "Jordan Henderson", "Backup Forward", "Player 4",
                "Player 5", "Player 6", "Player 7", "Player 8",
                "Player 9", "Player 10", "Player 11"
            ]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [lineup], self.squad
        )
        
        # Find backup forward's discrepancy
        backup_discrepancy = next(
            d for d in discrepancies 
            if d.player.name == "Backup Forward"
        )
        
        assert backup_discrepancy.discrepancy_type == AlertType.UNEXPECTED_STARTING
        assert backup_discrepancy.expected_starting is False
        assert backup_discrepancy.actually_starting is True
    
    def test_analyze_match_lineups_no_relevant_players(self):
        """Test analysis when no squad players are in the match."""
        # Create match with different teams
        chelsea = Team(name="Chelsea", abbreviation="CHE")
        city = Team(name="Manchester City", abbreviation="MCI")
        different_match = create_test_match("match2", chelsea, city)
        
        lineup = Lineup(
            team=chelsea,
            starting_eleven=[f"Player {i}" for i in range(1, 12)]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            different_match, [lineup], self.squad
        )
        
        assert len(discrepancies) == 0
    
    def test_get_players_for_match(self):
        """Test getting relevant players for a match."""
        relevant_players = self.analyzer._get_players_for_match(self.match, self.squad)
        
        # Should get all Liverpool players
        assert len(relevant_players) == 3
        player_names = {p.name for p in relevant_players}
        assert "Mohamed Salah" in player_names
        assert "Backup Forward" in player_names
        assert "Jordan Henderson" in player_names
    
    def test_build_starting_players_lookup(self):
        """Test building starting players lookup."""
        lineup1 = Lineup(
            team=self.liverpool,
            starting_eleven=["Mohamed Salah", "Jordan Henderson"] + [f"Player {i}" for i in range(3, 12)]
        )
        lineup2 = Lineup(
            team=self.arsenal,
            starting_eleven=["Bukayo Saka", "Martin Odegaard"] + [f"Player {i}" for i in range(3, 12)]
        )
        
        lookup = self.analyzer._build_starting_players_lookup([lineup1, lineup2])
        
        assert "Liverpool" in lookup
        assert "Arsenal" in lookup
        assert "Mohamed Salah" in lookup["Liverpool"]
        assert "Jordan Henderson" in lookup["Liverpool"]
        assert "Bukayo Saka" in lookup["Arsenal"]
        assert "Martin Odegaard" in lookup["Arsenal"]
    
    def test_should_analyze_match(self):
        """Test rate limiting logic."""
        # First check should return True
        assert self.analyzer.should_analyze_match(self.match) is True
        
        # Simulate analysis
        self.analyzer._last_analysis_time[self.match.id] = datetime.now()
        
        # Immediate second check should return False (within 5 minutes)
        assert self.analyzer.should_analyze_match(self.match) is False
        
        # Check with longer interval should return True
        assert self.analyzer.should_analyze_match(self.match, min_interval_minutes=0) is True
    
    def test_get_analysis_summary(self):
        """Test analysis summary generation."""
        # Create discrepancies
        discrepancies = [
            LineupDiscrepancy(
                player=self.salah, match=self.match,
                expected_starting=True, actually_starting=False
            ),
            LineupDiscrepancy(
                player=self.backup_forward, match=self.match,
                expected_starting=False, actually_starting=True
            ),
            LineupDiscrepancy(
                player=self.henderson, match=self.match,
                expected_starting=True, actually_starting=True
            )
        ]
        
        summary = self.analyzer.get_analysis_summary(discrepancies)
        
        assert summary['total_players_analyzed'] == 3
        assert summary['unexpected_benchings'] == 1
        assert summary['unexpected_startings'] == 1
        assert summary['confirmed_expectations'] == 1
    
    def test_analyze_player_lineup_status(self):
        """Test individual player analysis."""
        starting_players = {"Liverpool": {"Mohamed Salah", "Jordan Henderson"}}
        
        # Test expected starter who is starting
        discrepancy = self.analyzer._analyze_player_lineup_status(
            self.salah, self.match, starting_players
        )
        
        assert discrepancy.player == self.salah
        assert discrepancy.expected_starting is True
        assert discrepancy.actually_starting is True
        assert discrepancy.discrepancy_type == AlertType.LINEUP_CONFIRMED
        
        # Test reserve player who is not starting
        discrepancy = self.analyzer._analyze_player_lineup_status(
            self.backup_forward, self.match, starting_players
        )
        
        assert discrepancy.player == self.backup_forward
        assert discrepancy.expected_starting is False
        assert discrepancy.actually_starting is False
        assert discrepancy.discrepancy_type == AlertType.LINEUP_CONFIRMED
    
    def test_multiple_lineups_analysis(self):
        """Test analysis with multiple team lineups."""
        # Create Arsenal players
        saka = create_test_player(
            "saka1", "Bukayo Saka", self.arsenal,
            Position.FORWARD, PlayerStatus.ACTIVE
        )
        arsenal_squad = Squad(players=[self.salah, saka])  # Mixed team squad
        
        # Create lineups for both teams
        liverpool_lineup = Lineup(
            team=self.liverpool,
            starting_eleven=["Mohamed Salah"] + [f"Player {i}" for i in range(2, 12)]
        )
        arsenal_lineup = Lineup(
            team=self.arsenal,
            starting_eleven=["Bukayo Saka"] + [f"Player {i}" for i in range(2, 12)]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [liverpool_lineup, arsenal_lineup], arsenal_squad
        )
        
        # Should analyze both Salah and Saka
        assert len(discrepancies) == 2
        player_names = {d.player.name for d in discrepancies}
        assert "Mohamed Salah" in player_names
        assert "Bukayo Saka" in player_names
    
    def test_edge_case_empty_lineup(self):
        """Test handling of edge cases."""
        # Empty lineup list - should still create discrepancies for all players
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [], self.squad
        )
        # Should create discrepancies for all players (no lineups means no one starting)
        assert len(discrepancies) == 3
        
        # Empty squad
        empty_squad = Squad(players=[create_test_player("dummy", "Dummy")])  # Need at least one player
        empty_squad.players = []  # Clear it after creation
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[f"Player {i}" for i in range(1, 12)]
        )
        
        # This should not crash
        try:
            discrepancies = self.analyzer.analyze_match_lineups(
                self.match, [lineup], empty_squad
            )
            assert len(discrepancies) == 0
        except Exception:
            pytest.fail("Should handle empty squad gracefully")
    
    def test_last_analysis_time_tracking(self):
        """Test that analysis time is properly tracked."""
        assert self.analyzer.get_last_analysis_time(self.match.id) is None
        
        # Run analysis
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[f"Player {i}" for i in range(1, 12)]
        )
        
        self.analyzer.analyze_match_lineups(self.match, [lineup], self.squad)
        
        # Should now have last analysis time
        last_time = self.analyzer.get_last_analysis_time(self.match.id)
        assert last_time is not None
        assert isinstance(last_time, datetime)
    
    def test_case_sensitivity_in_player_names(self):
        """Test that player name matching is handled correctly."""
        # Create lineup with different case
        lineup = Lineup(
            team=self.liverpool,
            starting_eleven=[
                "mohamed salah",  # lowercase
                "JORDAN HENDERSON",  # uppercase
            ] + [f"Player {i}" for i in range(3, 12)]
        )
        
        discrepancies = self.analyzer.analyze_match_lineups(
            self.match, [lineup], self.squad
        )
        
        # Both players should be found as not starting (due to case mismatch)
        salah_discrepancy = next(
            d for d in discrepancies if d.player.name == "Mohamed Salah"
        )
        henderson_discrepancy = next(
            d for d in discrepancies if d.player.name == "Jordan Henderson"
        )
        
        # This demonstrates that our current implementation is case-sensitive
        # In production, we might want to implement case-insensitive matching
        assert salah_discrepancy.actually_starting is False
        assert henderson_discrepancy.actually_starting is False
