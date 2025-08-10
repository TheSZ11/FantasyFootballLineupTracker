"""
Domain interfaces and protocols for dependency injection.

Defines the contracts that must be implemented by providers and services,
enabling loose coupling and easy testing with mocks.
"""

from abc import ABC, abstractmethod
from typing import Protocol, List, Optional, Dict, Any
from datetime import datetime

from .models import Match, Lineup, Squad, Alert, Player
from .enums import AlertUrgency


class FootballDataProvider(Protocol):
    """Protocol for football data providers (API clients)."""
    
    async def get_fixtures(self, date: Optional[datetime] = None) -> List[Match]:
        """
        Get football fixtures for a specific date.
        
        Args:
            date: Optional date to filter fixtures. If None, gets today's fixtures.
            
        Returns:
            List of Match objects
            
        Raises:
            APIConnectionError: When API connection fails
            APIResponseError: When API returns invalid data
        """
        ...
    
    async def get_lineup(self, match_id: str) -> Optional[Lineup]:
        """
        Get lineup for a specific match.
        
        Args:
            match_id: Unique identifier for the match
            
        Returns:
            Lineup object if available, None if not yet published
            
        Raises:
            APIConnectionError: When API connection fails
            APIResponseError: When API returns invalid data
        """
        ...
    
    async def test_connection(self) -> bool:
        """
        Test the API connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        ...
    
    async def close(self) -> None:
        """Clean up resources and close connections."""
        ...


class NotificationProvider(Protocol):
    """Protocol for notification providers (email, Discord, etc.)."""
    
    async def send_alert(self, alert: Alert) -> bool:
        """
        Send an alert notification.
        
        Args:
            alert: Alert object containing message and metadata
            
        Returns:
            True if notification was sent successfully
            
        Raises:
            NotificationError: When notification sending fails
        """
        ...
    
    async def send_message(self, message: str, urgency: AlertUrgency = AlertUrgency.INFO) -> bool:
        """
        Send a simple text message.
        
        Args:
            message: Text message to send
            urgency: Urgency level for formatting
            
        Returns:
            True if message was sent successfully
        """
        ...
    
    async def test_connection(self) -> bool:
        """
        Test the notification provider connection.
        
        Returns:
            True if provider is available and configured
        """
        ...
    
    @property
    def provider_name(self) -> str:
        """Get the name of this notification provider."""
        ...


class SquadRepository(Protocol):
    """Protocol for squad data persistence."""
    
    def load_squad(self, file_path: str) -> Squad:
        """
        Load squad from data source.
        
        Args:
            file_path: Path to the squad data file
            
        Returns:
            Squad object with all players
            
        Raises:
            SquadLoadError: When squad loading fails
            SquadValidationError: When squad data is invalid
        """
        ...
    
    def save_squad(self, squad: Squad, file_path: str) -> bool:
        """
        Save squad to data source.
        
        Args:
            squad: Squad object to save
            file_path: Path where to save the squad data
            
        Returns:
            True if save was successful
            
        Raises:
            SquadError: When squad saving fails
        """
        ...
    
    def squad_exists(self, file_path: str) -> bool:
        """
        Check if squad file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if squad file exists and is readable
        """
        ...


class CacheProvider(Protocol):
    """Protocol for caching providers."""
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        ...
    
    async def set(self, key: str, value: Any, ttl: int) -> bool:
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            
        Returns:
            True if value was cached successfully
        """
        ...
    
    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if value was deleted
        """
        ...
    
    async def clear(self) -> bool:
        """
        Clear all cache entries.
        
        Returns:
            True if cache was cleared successfully
        """
        ...


class HealthChecker(Protocol):
    """Protocol for health checking services."""
    
    async def check_health(self) -> Dict[str, Any]:
        """
        Perform health check.
        
        Returns:
            Dictionary with health check results
        """
        ...
    
    @property
    def service_name(self) -> str:
        """Get the name of the service being checked."""
        ...


class MetricsCollector(Protocol):
    """Protocol for metrics collection."""
    
    def record_duration(self, name: str, duration: float, **tags) -> None:
        """Record a duration metric."""
        ...
    
    def increment_counter(self, name: str, value: int = 1, **tags) -> None:
        """Increment a counter metric."""
        ...
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        ...


# Abstract base classes for common implementations

class BaseNotificationProvider(ABC):
    """Base class for notification providers with common functionality."""
    
    def __init__(self, provider_name: str):
        self._provider_name = provider_name
    
    @property
    def provider_name(self) -> str:
        return self._provider_name
    
    @abstractmethod
    async def send_alert(self, alert: Alert) -> bool:
        """Send an alert notification."""
        pass
    
    @abstractmethod
    async def send_message(self, message: str, urgency: AlertUrgency = AlertUrgency.INFO) -> bool:
        """Send a simple text message."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test the notification provider connection."""
        pass
    
    def format_alert_message(self, alert: Alert) -> str:
        """Format alert into a message string."""
        return f"{alert.emoji} {alert.message}"


class BaseSquadRepository(ABC):
    """Base class for squad repositories with common functionality."""
    
    @abstractmethod
    def load_squad(self, file_path: str) -> Squad:
        """Load squad from data source."""
        pass
    
    @abstractmethod
    def save_squad(self, squad: Squad, file_path: str) -> bool:
        """Save squad to data source."""
        pass
    
    def squad_exists(self, file_path: str) -> bool:
        """Default implementation for checking squad existence."""
        import os
        return os.path.exists(file_path) and os.path.isfile(file_path)


class BaseFootballDataProvider(ABC):
    """Base class for football data providers with common functionality."""
    
    @abstractmethod
    async def get_fixtures(self, date: Optional[datetime] = None) -> List[Match]:
        """Get football fixtures."""
        pass
    
    @abstractmethod
    async def get_lineup(self, match_id: str) -> Optional[Lineup]:
        """Get lineup for a match."""
        pass
    
    @abstractmethod
    async def test_connection(self) -> bool:
        """Test API connection."""
        pass
    
    async def close(self) -> None:
        """Default close implementation - override if needed."""
        pass
    
    def filter_fixtures_by_teams(self, fixtures: List[Match], team_names: List[str]) -> List[Match]:
        """Filter fixtures to only include matches with specified teams."""
        return [
            match for match in fixtures
            if any(match.involves_team(team_name) for team_name in team_names)
        ]


class LineupAnalyzer(Protocol):
    """Protocol for analyzing lineups and detecting discrepancies."""
    
    def analyze_match_lineups(self, match: Match, lineups: List[Lineup], squad: Squad) -> List[str]:
        """
        Analyze match lineups against the squad to detect discrepancies.
        
        Args:
            match: The match being analyzed
            lineups: List of lineups to analyze
            squad: The user's squad
            
        Returns:
            List of discrepancy descriptions
        """
        ...


class AlertGenerator(Protocol):
    """Protocol for generating alerts from discrepancies."""
    
    def generate_alerts(self, discrepancies: List[str], match: Match) -> List[Alert]:
        """
        Generate alerts from lineup discrepancies.
        
        Args:
            discrepancies: List of discrepancy descriptions
            match: The match context
            
        Returns:
            List of Alert objects
        """
        ...
