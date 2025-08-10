"""
Pytest configuration and shared fixtures.

Provides common test fixtures, configuration, and utilities
for the entire test suite.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, AsyncMock

from src.lineup_tracker.domain.models import Team, Player, Match, Squad, Lineup, Alert
from src.lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus, AlertType, AlertUrgency
from src.lineup_tracker.container import Container, reset_container


# Configure asyncio for pytest
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Domain model fixtures
@pytest.fixture
def sample_team() -> Team:
    """Create a sample team for testing."""
    return Team(name="Liverpool", abbreviation="LIV")


@pytest.fixture
def sample_away_team() -> Team:
    """Create a sample away team for testing."""
    return Team(name="Arsenal", abbreviation="ARS")


@pytest.fixture
def sample_player(sample_team: Team) -> Player:
    """Create a sample player for testing."""
    return Player(
        id="test_player_1",
        name="Mohamed Salah",
        team=sample_team,
        position=Position.FORWARD,
        status=PlayerStatus.ACTIVE,
        fantasy_points=150.0,
        average_points=12.5,
        age=31,
        opponent="ARS H",
        games_played=20,
        draft_percentage="100",
        average_draft_position="1.5"
    )


@pytest.fixture
def sample_reserve_player(sample_team: Team) -> Player:
    """Create a sample reserve player for testing."""
    return Player(
        id="test_player_2",
        name="Backup Player",
        team=sample_team,
        position=Position.MIDFIELDER,
        status=PlayerStatus.RESERVE,
        fantasy_points=75.0,
        average_points=6.0,
        age=25,
        games_played=15
    )


@pytest.fixture
def sample_squad(sample_player: Player, sample_reserve_player: Player) -> Squad:
    """Create a sample squad for testing."""
    return Squad(players=[sample_player, sample_reserve_player])


@pytest.fixture
def sample_match(sample_team: Team, sample_away_team: Team) -> Match:
    """Create a sample match for testing."""
    return Match(
        id="test_match_1",
        home_team=sample_team,
        away_team=sample_away_team,
        kickoff=datetime.now() + timedelta(hours=2),
        status=MatchStatus.NOT_STARTED
    )


@pytest.fixture
def sample_lineup(sample_team: Team) -> Lineup:
    """Create a sample lineup for testing."""
    starting_eleven = [
        "Mohamed Salah", "Sadio Mane", "Roberto Firmino", "Jordan Henderson",
        "Fabinho", "Thiago Alcantara", "Andrew Robertson", "Trent Alexander-Arnold",
        "Virgil van Dijk", "Joel Matip", "Alisson Becker"
    ]
    return Lineup(team=sample_team, starting_eleven=starting_eleven)


@pytest.fixture
def sample_alert(sample_player: Player, sample_match: Match) -> Alert:
    """Create a sample alert for testing."""
    return Alert(
        player=sample_player,
        match=sample_match,
        alert_type=AlertType.UNEXPECTED_BENCHING,
        urgency=AlertUrgency.URGENT,
        message="Test alert message",
        extra_context={"test": "data"}
    )


# Mock fixtures
@pytest.fixture
def mock_football_api() -> AsyncMock:
    """Create a mock football API for testing."""
    mock_api = AsyncMock()
    mock_api.get_fixtures.return_value = []
    mock_api.get_lineup.return_value = None
    mock_api.test_connection.return_value = True
    return mock_api


@pytest.fixture
def mock_squad_repository() -> Mock:
    """Create a mock squad repository for testing."""
    mock_repo = Mock()
    mock_repo.load_squad.return_value = None
    mock_repo.save_squad.return_value = True
    mock_repo.squad_exists.return_value = True
    return mock_repo


@pytest.fixture
def mock_notification_provider() -> AsyncMock:
    """Create a mock notification provider for testing."""
    mock_provider = AsyncMock()
    mock_provider.provider_name = "test_provider"
    mock_provider.send_alert.return_value = True
    mock_provider.send_message.return_value = True
    mock_provider.test_connection.return_value = True
    return mock_provider


@pytest.fixture
def mock_notification_service(mock_notification_provider: AsyncMock) -> AsyncMock:
    """Create a mock notification service for testing."""
    mock_service = AsyncMock()
    mock_service.send_alert.return_value = True
    mock_service.send_message.return_value = True
    mock_service.send_startup_notification.return_value = True
    mock_service.send_shutdown_notification.return_value = True
    mock_service.send_error_notification.return_value = True
    mock_service.test_all_providers.return_value = {"test_provider": True}
    return mock_service


# Container fixtures
@pytest.fixture
def test_container() -> Container:
    """Create a test container with default configuration."""
    reset_container()
    container = Container()
    yield container
    reset_container()


@pytest.fixture
def container_with_mocks(
    mock_football_api: AsyncMock,
    mock_squad_repository: Mock,
    mock_notification_service: AsyncMock
) -> Container:
    """Create a container with mocked dependencies."""
    reset_container()
    container = Container()
    
    # Override dependencies with mocks
    container.override_dependency('football_api', mock_football_api)
    container.override_dependency('squad_repository', mock_squad_repository)
    container.override_dependency('notification_service', mock_notification_service)
    
    yield container
    reset_container()


# Test data fixtures
@pytest.fixture
def sample_csv_data() -> str:
    """Sample CSV data for testing repository."""
    return '''
"","Goalkeeper"
"ID","Pos","Player","Team","Eligible","Status","Age","Opponent","Fantasy Points","Average Fantasy Points per Game","% of leagues in which player was drafted","Average draft position among all leagues on Fantrax","GP","CS","GA","Sv","YC","RC","FC","FS","Pen","PKS","PKD","PKM","TkW","DIS","G","A2","KP","AT","Int","CLR","CoS","AER","ACNC","HCS","OG","SOT"
"*test1*","G","Test Goalkeeper","LIV","G","Act","25","ARS H","100.0","8.0","95","50.0","12","5","15","45","2","0","0","2","0","1","0","0","0","0","0","0","1","1","1","0","0","3","0","0","0","0"

"","Outfielder"
"ID","Pos","Player","Team","Eligible","Status","Age","Opponent","Fantasy Points","Average Fantasy Points per Game","% of leagues in which player was drafted","Average draft position among all leagues on Fantrax","GP","G","A2","KP","AT","SOT","TkW","DIS","FC","FS","YC","SYC","RC","HB","Pen","Off","ACNC","Int","CLR","CoS","BS","AER","BR","PKM","PKD","OG","GAO","CS"
"*test2*","F","Test Forward","LIV","F","Act","28","ARS H","150.0","12.5","100","1.0","20","15","8","25","10","35","5","20","15","25","3","0","0","0","0","0","5","3","0","15","1","5","45","0","0","0","20","5"
"*test3*","M","Test Midfielder","ARS","M","Res","26","LIV A","75.0","6.0","80","75.0","15","3","5","20","8","15","25","10","20","15","4","0","0","0","0","0","8","15","0","25","3","10","65","0","0","0","15","3"
'''.strip()


@pytest.fixture
def sample_fixture_data() -> List[Dict[str, Any]]:
    """Sample fixture data for testing API responses."""
    return [
        {
            "fixture": {
                "id": "test_fixture_1",
                "date": "2024-01-15T15:00:00Z",
                "status": {"short": "NS", "elapsed": None}
            },
            "teams": {
                "home": {"name": "Liverpool"},
                "away": {"name": "Arsenal"}
            }
        },
        {
            "fixture": {
                "id": "test_fixture_2", 
                "date": "2024-01-15T17:30:00Z",
                "status": {"short": "NS", "elapsed": None}
            },
            "teams": {
                "home": {"name": "Manchester City"},
                "away": {"name": "Chelsea"}
            }
        }
    ]


@pytest.fixture
def sample_lineup_data() -> List[Dict[str, Any]]:
    """Sample lineup data for testing API responses."""
    return [
        {
            "team": {"name": "Liverpool"},
            "startXI": [
                {"player": {"name": "Alisson Becker"}},
                {"player": {"name": "Trent Alexander-Arnold"}},
                {"player": {"name": "Virgil van Dijk"}},
                {"player": {"name": "Joel Matip"}},
                {"player": {"name": "Andrew Robertson"}},
                {"player": {"name": "Fabinho"}},
                {"player": {"name": "Jordan Henderson"}},
                {"player": {"name": "Mohamed Salah"}},
                {"player": {"name": "Sadio Mane"}},
                {"player": {"name": "Roberto Firmino"}},
                {"player": {"name": "Diogo Jota"}}
            ]
        },
        {
            "team": {"name": "Arsenal"},
            "startXI": [
                {"player": {"name": "Aaron Ramsdale"}},
                {"player": {"name": "Ben White"}},
                {"player": {"name": "William Saliba"}},
                {"player": {"name": "Gabriel Magalhaes"}},
                {"player": {"name": "Kieran Tierney"}},
                {"player": {"name": "Thomas Partey"}},
                {"player": {"name": "Granit Xhaka"}},
                {"player": {"name": "Bukayo Saka"}},
                {"player": {"name": "Martin Odegaard"}},
                {"player": {"name": "Gabriel Martinelli"}},
                {"player": {"name": "Eddie Nketiah"}}
            ]
        }
    ]


# Utility functions for tests
def create_test_player(
    player_id: str = "test_player",
    name: str = "Test Player", 
    team: Team = None,
    position: Position = Position.MIDFIELDER,
    status: PlayerStatus = PlayerStatus.ACTIVE,
    fantasy_points: float = 100.0,
    average_points: float = 8.0
) -> Player:
    """Create a test player with customizable attributes."""
    if team is None:
        team = Team(name="Test Team", abbreviation="TEST")
    
    return Player(
        id=player_id,
        name=name,
        team=team,
        position=position,
        status=status,
        fantasy_points=fantasy_points,
        average_points=average_points
    )


def create_test_match(
    match_id: str = "test_match",
    home_team: Team = None,
    away_team: Team = None,
    status: MatchStatus = MatchStatus.NOT_STARTED,
    kickoff_hours_from_now: int = 2
) -> Match:
    """Create a test match with customizable attributes."""
    if home_team is None:
        home_team = Team(name="Home Team", abbreviation="HOME")
    if away_team is None:
        away_team = Team(name="Away Team", abbreviation="AWAY")
    
    return Match(
        id=match_id,
        home_team=home_team,
        away_team=away_team,
        kickoff=datetime.now() + timedelta(hours=kickoff_hours_from_now),
        status=status
    )


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test" 
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "external: mark test as requiring external resources"
    )


# Custom assertions
def assert_player_matches(actual: Player, expected: Player, ignore_fields: List[str] = None):
    """Assert that two players match, optionally ignoring certain fields."""
    if ignore_fields is None:
        ignore_fields = []
    
    if 'id' not in ignore_fields:
        assert actual.id == expected.id
    if 'name' not in ignore_fields:
        assert actual.name == expected.name
    if 'team' not in ignore_fields:
        assert actual.team.name == expected.team.name
        assert actual.team.abbreviation == expected.team.abbreviation
    if 'position' not in ignore_fields:
        assert actual.position == expected.position
    if 'status' not in ignore_fields:
        assert actual.status == expected.status
    if 'fantasy_points' not in ignore_fields:
        assert abs(actual.fantasy_points - expected.fantasy_points) < 0.01
    if 'average_points' not in ignore_fields:
        assert abs(actual.average_points - expected.average_points) < 0.01


def assert_alert_valid(alert: Alert):
    """Assert that an alert is valid and complete."""
    assert alert.player is not None
    assert alert.match is not None
    assert alert.alert_type in AlertType
    assert alert.urgency in AlertUrgency
    assert alert.message is not None
    assert len(alert.message) > 0
    assert alert.timestamp is not None
