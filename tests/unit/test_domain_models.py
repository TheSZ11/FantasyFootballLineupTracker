"""
Unit tests for domain models.

Tests the core domain models to ensure they work correctly with
proper validation and business rules.
"""

import pytest
from datetime import datetime

from src.lineup_tracker.domain.models import Team, Player, Match, Squad, Alert, Lineup
from src.lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus, AlertType, AlertUrgency
from src.lineup_tracker.domain.exceptions import DomainValidationError, InvalidDataError


class TestTeam:
    """Test the Team model."""
    
    def test_create_valid_team(self):
        """Test creating a valid team."""
        team = Team(name="Liverpool", abbreviation="LIV")
        assert team.name == "Liverpool"
        assert team.abbreviation == "LIV"
    
    def test_team_requires_name_and_abbreviation(self):
        """Test that team requires both name and abbreviation."""
        with pytest.raises(InvalidDataError):
            Team(name="", abbreviation="LIV")
        
        with pytest.raises(InvalidDataError):
            Team(name="Liverpool", abbreviation="")


class TestPlayer:
    """Test the Player model."""
    
    def setup_method(self):
        """Set up test data."""
        self.team = Team(name="Liverpool", abbreviation="LIV")
    
    def test_create_valid_player(self):
        """Test creating a valid player."""
        player = Player(
            id="test1",
            name="Mohamed Salah",
            team=self.team,
            position=Position.FORWARD,
            status=PlayerStatus.ACTIVE,
            fantasy_points=100.5,
            average_points=10.5
        )
        
        assert player.id == "test1"
        assert player.name == "Mohamed Salah"
        assert player.team == self.team
        assert player.position == Position.FORWARD
        assert player.status == PlayerStatus.ACTIVE
        assert player.fantasy_points == 100.5
        assert player.average_points == 10.5
        assert player.is_active is True
        assert player.team_name == "Liverpool"
    
    def test_player_validation(self):
        """Test player validation rules."""
        # Test missing ID
        with pytest.raises(InvalidDataError):
            Player(
                id="",
                name="Test Player",
                team=self.team,
                position=Position.FORWARD,
                status=PlayerStatus.ACTIVE,
                fantasy_points=0.0,
                average_points=0.0
            )
        
        # Test negative fantasy points
        with pytest.raises(InvalidDataError):
            Player(
                id="test1",
                name="Test Player", 
                team=self.team,
                position=Position.FORWARD,
                status=PlayerStatus.ACTIVE,
                fantasy_points=-10.0,
                average_points=0.0
            )
    
    def test_player_properties(self):
        """Test player properties."""
        active_player = Player(
            id="test1", name="Test", team=self.team,
            position=Position.FORWARD, status=PlayerStatus.ACTIVE,
            fantasy_points=0.0, average_points=0.0
        )
        
        reserve_player = Player(
            id="test2", name="Test", team=self.team,
            position=Position.FORWARD, status=PlayerStatus.RESERVE,
            fantasy_points=0.0, average_points=0.0
        )
        
        assert active_player.is_active is True
        assert reserve_player.is_active is False


class TestMatch:
    """Test the Match model."""
    
    def setup_method(self):
        """Set up test data."""
        self.home_team = Team(name="Liverpool", abbreviation="LIV")
        self.away_team = Team(name="Arsenal", abbreviation="ARS")
    
    def test_create_valid_match(self):
        """Test creating a valid match."""
        kickoff = datetime.now()
        match = Match(
            id="match1",
            home_team=self.home_team,
            away_team=self.away_team,
            kickoff=kickoff,
            status=MatchStatus.NOT_STARTED
        )
        
        assert match.id == "match1"
        assert match.home_team == self.home_team
        assert match.away_team == self.away_team
        assert match.kickoff == kickoff
        assert match.status == MatchStatus.NOT_STARTED
        assert match.is_started is False
    
    def test_match_validation(self):
        """Test match validation rules."""
        # Test same team for home and away
        with pytest.raises(InvalidDataError):
            Match(
                id="match1",
                home_team=self.home_team,
                away_team=self.home_team,  # Same team
                kickoff=datetime.now(),
                status=MatchStatus.NOT_STARTED
            )
    
    def test_match_involves_team(self):
        """Test the involves_team method."""
        match = Match(
            id="match1",
            home_team=self.home_team,
            away_team=self.away_team,
            kickoff=datetime.now(),
            status=MatchStatus.NOT_STARTED
        )
        
        assert match.involves_team("Liverpool") is True
        assert match.involves_team("Arsenal") is True
        assert match.involves_team("Chelsea") is False


class TestSquad:
    """Test the Squad model."""
    
    def setup_method(self):
        """Set up test data."""
        team = Team(name="Liverpool", abbreviation="LIV")
        self.active_player = Player(
            id="1", name="Active Player", team=team,
            position=Position.FORWARD, status=PlayerStatus.ACTIVE,
            fantasy_points=100.0, average_points=10.0
        )
        self.reserve_player = Player(
            id="2", name="Reserve Player", team=team,
            position=Position.DEFENDER, status=PlayerStatus.RESERVE,
            fantasy_points=50.0, average_points=5.0
        )
    
    def test_create_valid_squad(self):
        """Test creating a valid squad."""
        squad = Squad(players=[self.active_player, self.reserve_player])
        
        assert len(squad.players) == 2
        assert squad.total_count == 2
        assert squad.active_count == 1
        assert squad.reserve_count == 1
        assert len(squad.active_players) == 1
        assert len(squad.reserve_players) == 1
        assert squad.active_players[0] == self.active_player
        assert squad.reserve_players[0] == self.reserve_player
    
    def test_empty_squad_validation(self):
        """Test that empty squad raises error."""
        with pytest.raises(InvalidDataError):
            Squad(players=[])
    
    def test_squad_team_methods(self):
        """Test squad team-based methods."""
        squad = Squad(players=[self.active_player, self.reserve_player])
        
        liverpool_players = squad.get_players_by_team("Liverpool")
        assert len(liverpool_players) == 2
        
        active_liverpool = squad.get_active_players_by_team("Liverpool")
        assert len(active_liverpool) == 1
        assert active_liverpool[0] == self.active_player
        
        teams = squad.get_teams()
        assert "Liverpool" in teams


class TestLineup:
    """Test the Lineup model."""
    
    def setup_method(self):
        """Set up test data."""
        self.team = Team(name="Liverpool", abbreviation="LIV")
        self.starting_eleven = [f"Player {i}" for i in range(1, 12)]
    
    def test_create_valid_lineup(self):
        """Test creating a valid lineup."""
        lineup = Lineup(
            team=self.team,
            starting_eleven=self.starting_eleven
        )
        
        assert lineup.team == self.team
        assert len(lineup.starting_eleven) == 11
        assert lineup.has_player_starting("Player 1") is True
        assert lineup.has_player_starting("Unknown Player") is False
    
    def test_lineup_validation(self):
        """Test lineup validation rules."""
        # Test wrong number of starting players
        with pytest.raises(InvalidDataError):
            Lineup(
                team=self.team,
                starting_eleven=["Player 1", "Player 2"]  # Only 2 players
            )


if __name__ == "__main__":
    pytest.main([__file__])
