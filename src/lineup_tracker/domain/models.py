"""
Core domain models with proper type safety.

Defines the fundamental data structures used throughout the LineupTracker system,
replacing the dictionary-based approach with strongly typed dataclasses.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict, Any
from .enums import Position, PlayerStatus, MatchStatus, AlertType, AlertUrgency
from .exceptions import InvalidDataError


@dataclass(frozen=True)
class Team:
    """Football team entity."""
    name: str
    abbreviation: str
    
    def __post_init__(self):
        if not self.name or not self.abbreviation:
            raise InvalidDataError("Team name and abbreviation are required")


@dataclass
class Player:
    """Fantasy football player entity with Fantrax data."""
    id: str
    name: str
    team: Team
    position: Position
    status: PlayerStatus
    fantasy_points: float
    average_points: float
    
    # Optional Fantrax metadata
    age: Optional[int] = None
    opponent: Optional[str] = None
    games_played: Optional[int] = None
    draft_percentage: Optional[str] = None
    average_draft_position: Optional[str] = None
    
    def __post_init__(self):
        if not self.id or not self.name:
            raise InvalidDataError("Player ID and name are required")
        if self.fantasy_points < 0 or self.average_points < 0:
            raise InvalidDataError("Fantasy points cannot be negative")
    
    @property
    def is_active(self) -> bool:
        """Check if player is expected to start."""
        return self.status == PlayerStatus.ACTIVE
    
    @property
    def team_name(self) -> str:
        """Get team name for backward compatibility."""
        return self.team.name


@dataclass
class Match:
    """Football match entity."""
    id: str
    home_team: Team
    away_team: Team
    kickoff: datetime
    status: MatchStatus
    elapsed_time: Optional[int] = None
    
    def __post_init__(self):
        if not self.id:
            raise InvalidDataError("Match ID is required")
        if self.home_team == self.away_team:
            raise InvalidDataError("Home and away teams must be different")
    
    @property
    def teams(self) -> List[Team]:
        """Get both teams in the match."""
        return [self.home_team, self.away_team]
    
    @property
    def is_started(self) -> bool:
        """Check if match has started."""
        return self.status not in [MatchStatus.NOT_STARTED, MatchStatus.TO_BE_DETERMINED]
    
    def involves_team(self, team_name: str) -> bool:
        """Check if match involves a specific team."""
        return team_name in [self.home_team.name, self.away_team.name]


@dataclass
class Lineup:
    """Team lineup for a specific match."""
    team: Team
    starting_eleven: List[str]  # Player names
    substitutes: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if len(self.starting_eleven) != 11:
            raise InvalidDataError(f"Starting eleven must have 11 players, got {len(self.starting_eleven)}")
    
    def has_player_starting(self, player_name: str) -> bool:
        """Check if a player is in the starting eleven."""
        return player_name in self.starting_eleven
    
    def has_player_on_bench(self, player_name: str) -> bool:
        """Check if a player is on the bench."""
        return player_name in self.substitutes


@dataclass
class Squad:
    """Fantasy football squad containing all players."""
    players: List[Player]
    last_updated: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.players:
            raise InvalidDataError("Squad cannot be empty")
    
    @property
    def active_players(self) -> List[Player]:
        """Get players expected to start."""
        return [p for p in self.players if p.status == PlayerStatus.ACTIVE]
    
    @property
    def reserve_players(self) -> List[Player]:
        """Get bench/reserve players."""
        return [p for p in self.players if p.status == PlayerStatus.RESERVE]
    
    @property
    def total_count(self) -> int:
        """Total number of players in squad."""
        return len(self.players)
    
    @property
    def active_count(self) -> int:
        """Number of active players."""
        return len(self.active_players)
    
    @property
    def reserve_count(self) -> int:
        """Number of reserve players."""
        return len(self.reserve_players)
    
    def get_players_by_team(self, team_name: str) -> List[Player]:
        """Get all players from a specific team."""
        return [p for p in self.players if p.team.name == team_name]
    
    def get_active_players_by_team(self, team_name: str) -> List[Player]:
        """Get active players from a specific team."""
        return [p for p in self.active_players if p.team.name == team_name]
    
    def get_teams(self) -> List[str]:
        """Get unique team names in squad."""
        return list(set(player.team.name for player in self.players))


@dataclass
class Alert:
    """Lineup discrepancy alert."""
    player: Player
    match: Match
    alert_type: AlertType
    urgency: AlertUrgency
    message: str
    timestamp: datetime = field(default_factory=datetime.now)
    
    # Additional context for notifications
    extra_context: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.message:
            raise InvalidDataError("Alert message is required")
    
    @property
    def should_send_email(self) -> bool:
        """Check if alert should trigger email notification."""
        return self.urgency in [AlertUrgency.URGENT, AlertUrgency.IMPORTANT]
    
    @property
    def should_send_discord(self) -> bool:
        """Check if alert should trigger Discord notification."""
        return True  # All alerts go to Discord
    
    @property
    def emoji(self) -> str:
        """Get emoji for alert type."""
        emoji_map = {
            AlertType.UNEXPECTED_BENCHING: "🚨",
            AlertType.UNEXPECTED_STARTING: "⚡",
            AlertType.LINEUP_CONFIRMED: "✅"
        }
        return emoji_map.get(self.alert_type, "📋")


@dataclass
class LineupDiscrepancy:
    """Represents a discrepancy between expected and actual lineup."""
    player: Player
    match: Match
    expected_starting: bool
    actually_starting: bool
    
    @property
    def discrepancy_type(self) -> AlertType:
        """Determine the type of discrepancy."""
        if self.expected_starting and not self.actually_starting:
            return AlertType.UNEXPECTED_BENCHING
        elif not self.expected_starting and self.actually_starting:
            return AlertType.UNEXPECTED_STARTING
        else:
            return AlertType.LINEUP_CONFIRMED
    
    @property
    def urgency(self) -> AlertUrgency:
        """Determine alert urgency based on discrepancy type."""
        urgency_map = {
            AlertType.UNEXPECTED_BENCHING: AlertUrgency.URGENT,
            AlertType.UNEXPECTED_STARTING: AlertUrgency.IMPORTANT,
            AlertType.LINEUP_CONFIRMED: AlertUrgency.INFO
        }
        return urgency_map[self.discrepancy_type]
