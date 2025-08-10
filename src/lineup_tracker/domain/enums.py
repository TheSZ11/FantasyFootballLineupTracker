"""
Domain enums for type safety and consistency.

Defines all enumerated types used throughout the LineupTracker system
for positions, statuses, and other categorical data.
"""

from enum import Enum


class Position(Enum):
    """Player positions in football."""
    GOALKEEPER = "Goalkeeper"
    DEFENDER = "Defender"
    MIDFIELDER = "Midfielder"
    FORWARD = "Forward"


class PlayerStatus(Enum):
    """Player status in fantasy team."""
    ACTIVE = "Act"      # Expected to start (Active in Fantrax)
    RESERVE = "Res"     # Bench player (Reserve in Fantrax)


class MatchStatus(Enum):
    """Match status from API."""
    NOT_STARTED = "NS"
    LIVE = "LIVE"
    FINISHED = "FT"
    POSTPONED = "PST"
    CANCELLED = "CANC"
    TO_BE_DETERMINED = "TBD"


class AlertType(Enum):
    """Types of lineup alerts."""
    UNEXPECTED_BENCHING = "unexpected_benching"
    UNEXPECTED_STARTING = "unexpected_starting"
    LINEUP_CONFIRMED = "lineup_confirmed"


class AlertUrgency(Enum):
    """Alert urgency levels for notifications."""
    URGENT = "urgent"       # Email + Discord (unexpected benching)
    IMPORTANT = "important" # Email + Discord (unexpected starting)  
    INFO = "info"          # Discord only (confirmations)
    WARNING = "warning"    # Discord only (warnings)


class NotificationType(Enum):
    """Types of notifications."""
    EMAIL = "email"
    DISCORD = "discord"
