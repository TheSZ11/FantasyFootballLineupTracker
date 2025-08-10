"""
Unit tests for AlertGenerator business logic.

Tests the core business rules for generating alerts from lineup discrepancies
with proper message formatting and context enrichment.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from src.lineup_tracker.business.alert_generator import AlertGenerator
from src.lineup_tracker.domain.models import Team, Player, Match, LineupDiscrepancy, Alert
from src.lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus, AlertType, AlertUrgency
from tests.conftest import create_test_player, create_test_match


@pytest.mark.unit
class TestAlertGenerator:
    """Test the AlertGenerator business logic."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.generator = AlertGenerator()
        
        # Create test teams
        self.liverpool = Team(name="Liverpool", abbreviation="LIV")
        self.arsenal = Team(name="Arsenal", abbreviation="ARS")
        
        # Create test player with rich fantasy data
        self.salah = create_test_player(
            "salah1", "Mohamed Salah", self.liverpool,
            Position.FORWARD, PlayerStatus.ACTIVE, 150.0, 12.5
        )
        self.salah.age = 31
        self.salah.games_played = 20
        self.salah.draft_percentage = "100"
        self.salah.opponent = "ARS H"
        
        # Create backup player
        self.backup = create_test_player(
            "backup1", "Backup Player", self.liverpool,
            Position.MIDFIELDER, PlayerStatus.RESERVE, 50.0, 4.0
        )
        self.backup.draft_percentage = "25"
        
        # Create test match
        self.match = create_test_match(
            "match1", self.liverpool, self.arsenal,
            MatchStatus.NOT_STARTED, 2
        )
    
    def test_generate_alerts_unexpected_benching(self):
        """Test alert generation for unexpected benching."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=False
        )
        
        alerts = self.generator.generate_alerts([discrepancy])
        
        assert len(alerts) == 1
        alert = alerts[0]
        
        assert alert.player == self.salah
        assert alert.match == self.match
        assert alert.alert_type == AlertType.UNEXPECTED_BENCHING
        assert alert.urgency == AlertUrgency.URGENT
        assert "BENCHED" in alert.message.upper()
        assert "Mohamed Salah" in alert.message
        assert "Liverpool" in alert.message
        assert "12.5" in alert.message  # Average points
        assert alert.should_send_email is True
        assert alert.should_send_discord is True
    
    def test_generate_alerts_unexpected_starting(self):
        """Test alert generation for unexpected starting."""
        discrepancy = LineupDiscrepancy(
            player=self.backup,
            match=self.match,
            expected_starting=False,
            actually_starting=True
        )
        
        alerts = self.generator.generate_alerts([discrepancy])
        
        assert len(alerts) == 1
        alert = alerts[0]
        
        assert alert.player == self.backup
        assert alert.alert_type == AlertType.UNEXPECTED_STARTING
        assert alert.urgency == AlertUrgency.IMPORTANT
        assert "STARTING" in alert.message.upper()
        assert "Backup Player" in alert.message
        assert "25%" in alert.message  # Draft percentage
        assert alert.should_send_email is True
        assert alert.should_send_discord is True
    
    def test_generate_alerts_lineup_confirmed(self):
        """Test alert generation for confirmed expectations."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=True
        )
        
        alerts = self.generator.generate_alerts([discrepancy])
        
        assert len(alerts) == 1
        alert = alerts[0]
        
        assert alert.alert_type == AlertType.LINEUP_CONFIRMED
        assert alert.urgency == AlertUrgency.INFO
        assert "confirmed starting" in alert.message.lower()
        assert alert.should_send_email is False
        assert alert.should_send_discord is True
    
    def test_create_alert_from_discrepancy(self):
        """Test creating individual alerts from discrepancies."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=False
        )
        
        alert = self.generator._create_alert_from_discrepancy(discrepancy)
        
        assert isinstance(alert, Alert)
        assert alert.player == self.salah
        assert alert.match == self.match
        assert alert.alert_type == AlertType.UNEXPECTED_BENCHING
        assert alert.urgency == AlertUrgency.URGENT
        assert len(alert.message) > 0
        assert isinstance(alert.extra_context, dict)
        assert alert.timestamp is not None
    
    def test_format_alert_message_benching(self):
        """Test alert message formatting for benching."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=False
        )
        
        message = self.generator._format_alert_message(discrepancy)
        
        # Check that all expected information is in the message
        assert "🚨" in message
        assert "Mohamed Salah" in message
        assert "BENCHED" in message
        assert "Liverpool" in message
        assert "Forward" in message
        assert "Liverpool vs Arsenal" in message
        assert "12.5" in message  # Average points
        assert "150.0" in message  # Total points
        assert "20" in message  # Games played
    
    def test_format_alert_message_starting(self):
        """Test alert message formatting for unexpected starting."""
        discrepancy = LineupDiscrepancy(
            player=self.backup,
            match=self.match,
            expected_starting=False,
            actually_starting=True
        )
        
        message = self.generator._format_alert_message(discrepancy)
        
        assert "⚡" in message
        assert "Backup Player" in message
        assert "STARTING" in message
        assert "25%" in message  # Draft percentage
        assert "4.0" in message  # Average points
    
    def test_build_extra_context(self):
        """Test building extra context for alerts."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=False
        )
        
        context = self.generator._build_extra_context(discrepancy)
        
        assert isinstance(context, dict)
        assert context['player_id'] == 'salah1'
        assert context['team_abbreviation'] == 'LIV'
        assert context['match_id'] == 'match1'
        assert 'kickoff_timestamp' in context
        assert 'fantasy_data' in context
        assert 'discrepancy_details' in context
        
        fantasy_data = context['fantasy_data']
        assert fantasy_data['fantasy_points'] == 150.0
        assert fantasy_data['average_points'] == 12.5
        assert fantasy_data['games_played'] == 20
        assert fantasy_data['age'] == 31
        
        discrepancy_details = context['discrepancy_details']
        assert discrepancy_details['expected_starting'] is True
        assert discrepancy_details['actually_starting'] is False
        assert discrepancy_details['discrepancy_type'] == 'unexpected_benching'
    
    def test_filter_alerts_by_importance(self):
        """Test filtering alerts by urgency level."""
        # Create alerts with different urgencies
        urgent_discrepancy = LineupDiscrepancy(
            player=self.salah, match=self.match,
            expected_starting=True, actually_starting=False
        )
        info_discrepancy = LineupDiscrepancy(
            player=self.backup, match=self.match,
            expected_starting=False, actually_starting=False
        )
        
        alerts = self.generator.generate_alerts([urgent_discrepancy, info_discrepancy])
        
        # Filter for urgent only
        urgent_alerts = self.generator.filter_alerts_by_importance(
            alerts, AlertUrgency.URGENT
        )
        assert len(urgent_alerts) == 1
        assert urgent_alerts[0].urgency == AlertUrgency.URGENT
        
        # Filter for important and above
        important_alerts = self.generator.filter_alerts_by_importance(
            alerts, AlertUrgency.IMPORTANT
        )
        assert len(important_alerts) == 1  # Only urgent qualifies
        
        # Filter for info and above (should get all)
        all_alerts = self.generator.filter_alerts_by_importance(
            alerts, AlertUrgency.INFO
        )
        assert len(all_alerts) == 2
    
    def test_group_alerts_by_team(self):
        """Test grouping alerts by team."""
        # Create alerts for different teams
        chelsea = Team(name="Chelsea", abbreviation="CHE")
        chelsea_player = create_test_player(
            "chelsea1", "Chelsea Player", chelsea, 
            Position.MIDFIELDER, PlayerStatus.ACTIVE
        )
        
        discrepancies = [
            LineupDiscrepancy(
                player=self.salah, match=self.match,
                expected_starting=True, actually_starting=False
            ),
            LineupDiscrepancy(
                player=self.backup, match=self.match,
                expected_starting=False, actually_starting=True
            ),
            LineupDiscrepancy(
                player=chelsea_player, match=self.match,
                expected_starting=True, actually_starting=False
            )
        ]
        
        alerts = self.generator.generate_alerts(discrepancies)
        grouped = self.generator.group_alerts_by_team(alerts)
        
        assert "Liverpool" in grouped
        assert "Chelsea" in grouped
        assert len(grouped["Liverpool"]) == 2
        assert len(grouped["Chelsea"]) == 1
    
    def test_get_alert_summary(self):
        """Test alert summary generation."""
        discrepancies = [
            LineupDiscrepancy(
                player=self.salah, match=self.match,
                expected_starting=True, actually_starting=False  # Benching
            ),
            LineupDiscrepancy(
                player=self.backup, match=self.match,
                expected_starting=False, actually_starting=True  # Starting
            ),
            LineupDiscrepancy(
                player=create_test_player("confirmed", "Confirmed Player"),
                match=self.match,
                expected_starting=True, actually_starting=True  # Confirmed
            )
        ]
        
        alerts = self.generator.generate_alerts(discrepancies)
        summary = self.generator.get_alert_summary(alerts)
        
        assert summary['total_alerts'] == 3
        assert summary['urgent'] == 1  # Benching
        assert summary['important'] == 1  # Starting
        assert summary['info'] == 1  # Confirmed
        assert summary['benchings'] == 1
        assert summary['unexpected_starts'] == 1
        assert summary['confirmations'] == 1
    
    def test_create_confirmation_alert(self):
        """Test creating confirmation alerts for expected lineups."""
        discrepancy = LineupDiscrepancy(
            player=self.salah,
            match=self.match,
            expected_starting=True,
            actually_starting=True
        )
        
        alert = self.generator._create_confirmation_alert(discrepancy)
        
        assert alert.alert_type == AlertType.LINEUP_CONFIRMED
        assert alert.urgency == AlertUrgency.INFO
        assert "confirmed starting" in alert.message.lower()
        assert "Mohamed Salah" in alert.message
        assert "Liverpool" in alert.message
        assert "Arsenal" in alert.message  # Opponent
    
    def test_format_confirmation_message(self):
        """Test formatting of confirmation messages."""
        # Starting as expected
        starting_discrepancy = LineupDiscrepancy(
            player=self.salah, match=self.match,
            expected_starting=True, actually_starting=True
        )
        
        message = self.generator._format_confirmation_message(starting_discrepancy)
        assert "✅" in message
        assert "confirmed starting" in message
        assert "Mohamed Salah" in message
        assert "vs Arsenal" in message
        
        # Not starting as expected
        bench_discrepancy = LineupDiscrepancy(
            player=self.backup, match=self.match,
            expected_starting=False, actually_starting=False
        )
        
        message = self.generator._format_confirmation_message(bench_discrepancy)
        assert "✅" in message
        assert "lineup status as expected" in message
        assert "Backup Player" in message
    
    def test_alert_templates(self):
        """Test that alert templates are properly initialized."""
        templates = self.generator._alert_templates
        
        assert 'unexpected_benching' in templates
        assert 'unexpected_starting' in templates
        assert 'default' in templates
        
        # Check template structure
        benching_template = templates['unexpected_benching']
        assert "🚨" in benching_template
        assert "{player_name}" in benching_template
        assert "{team_name}" in benching_template
        assert "{avg_points}" in benching_template
        
        starting_template = templates['unexpected_starting']
        assert "⚡" in starting_template
        assert "{draft_percentage}" in starting_template
    
    def test_opponent_determination(self):
        """Test correct opponent determination for home/away teams."""
        # Liverpool home vs Arsenal away
        home_match = Match(
            id="home_match",
            home_team=self.liverpool,
            away_team=self.arsenal,
            kickoff=datetime.now(),
            status=MatchStatus.NOT_STARTED
        )
        
        discrepancy = LineupDiscrepancy(
            player=self.salah, match=home_match,
            expected_starting=True, actually_starting=False
        )
        
        message = self.generator._format_alert_message(discrepancy)
        # Should show Arsenal as opponent for Liverpool player
        assert "Arsenal" in message
        
        # Arsenal away vs Liverpool home
        away_match = Match(
            id="away_match",
            home_team=self.arsenal,
            away_team=self.liverpool,
            kickoff=datetime.now(),
            status=MatchStatus.NOT_STARTED
        )
        
        discrepancy = LineupDiscrepancy(
            player=self.salah, match=away_match,
            expected_starting=True, actually_starting=False
        )
        
        message = self.generator._format_alert_message(discrepancy)
        # Should show Arsenal as opponent for Liverpool player
        assert "Arsenal" in message
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty discrepancies list
        alerts = self.generator.generate_alerts([])
        assert len(alerts) == 0
        
        # Player with minimal data
        minimal_player = Player(
            id="minimal",
            name="Minimal Player",
            team=self.liverpool,
            position=Position.MIDFIELDER,
            status=PlayerStatus.ACTIVE,
            fantasy_points=0.0,
            average_points=0.0
        )
        
        discrepancy = LineupDiscrepancy(
            player=minimal_player, match=self.match,
            expected_starting=True, actually_starting=False
        )
        
        # Should not crash with minimal data
        alerts = self.generator.generate_alerts([discrepancy])
        assert len(alerts) == 1
        assert alerts[0].message is not None
    
    def test_alert_emoji_property(self):
        """Test that alerts have correct emoji based on type."""
        benching_discrepancy = LineupDiscrepancy(
            player=self.salah, match=self.match,
            expected_starting=True, actually_starting=False
        )
        
        starting_discrepancy = LineupDiscrepancy(
            player=self.backup, match=self.match,
            expected_starting=False, actually_starting=True
        )
        
        confirmed_discrepancy = LineupDiscrepancy(
            player=self.salah, match=self.match,
            expected_starting=True, actually_starting=True
        )
        
        alerts = self.generator.generate_alerts([
            benching_discrepancy, starting_discrepancy, confirmed_discrepancy
        ])
        
        benching_alert = next(a for a in alerts if a.alert_type == AlertType.UNEXPECTED_BENCHING)
        starting_alert = next(a for a in alerts if a.alert_type == AlertType.UNEXPECTED_STARTING)
        confirmed_alert = next(a for a in alerts if a.alert_type == AlertType.LINEUP_CONFIRMED)
        
        assert benching_alert.emoji == "🚨"
        assert starting_alert.emoji == "⚡"
        assert confirmed_alert.emoji == "✅"
