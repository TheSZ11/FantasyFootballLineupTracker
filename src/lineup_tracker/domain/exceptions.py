"""
Domain-specific exceptions for the LineupTracker system.

Defines a hierarchy of exceptions that represent different error conditions
that can occur within the business domain.
"""


class LineupMonitorError(Exception):
    """Base exception for all LineupTracker errors."""
    
    def __init__(self, message: str, details: str = None):
        self.message = message
        self.details = details
        super().__init__(self.message)


class DomainValidationError(LineupMonitorError):
    """Raised when domain model validation fails."""
    pass


class SquadError(LineupMonitorError):
    """Base exception for squad-related errors."""
    pass


class SquadLoadError(SquadError):
    """Raised when squad loading fails."""
    pass


class SquadValidationError(SquadError):
    """Raised when squad data is invalid."""
    pass


class SquadEmptyError(SquadError):
    """Raised when squad is empty or has no valid players."""
    pass


class APIError(LineupMonitorError):
    """Base exception for API-related errors."""
    pass


class APIConnectionError(APIError):
    """Raised when API connection fails."""
    pass


class APITimeoutError(APIError):
    """Raised when API request times out."""
    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class APIResponseError(APIError):
    """Raised when API returns invalid response."""
    pass


class NotificationError(LineupMonitorError):
    """Base exception for notification-related errors."""
    pass


class EmailNotificationError(NotificationError):
    """Raised when email notification fails."""
    pass


class DiscordNotificationError(NotificationError):
    """Raised when Discord notification fails."""
    pass


class NotificationProviderNotConfiguredError(NotificationError):
    """Raised when notification provider is not properly configured."""
    pass


class ConfigurationError(LineupMonitorError):
    """Base exception for configuration-related errors."""
    pass


class MissingConfigurationError(ConfigurationError):
    """Raised when required configuration is missing."""
    pass


class InvalidConfigurationError(ConfigurationError):
    """Raised when configuration values are invalid."""
    pass


class DataParsingError(LineupMonitorError):
    """Raised when data parsing fails."""
    pass


class CSVParsingError(DataParsingError):
    """Raised when CSV parsing fails."""
    pass


class TeamMappingError(LineupMonitorError):
    """Raised when team name mapping fails."""
    pass


class InvalidDataError(LineupMonitorError):
    """Raised when input data is invalid or malformed."""
    pass


class HealthCheckError(LineupMonitorError):
    """Raised when health check fails."""
    pass


class ServiceUnavailableError(LineupMonitorError):
    """Raised when a required service is unavailable."""
    pass


# Convenience functions for creating common exceptions

def squad_load_error(file_path: str, reason: str) -> SquadLoadError:
    """Create a SquadLoadError with standard formatting."""
    return SquadLoadError(
        f"Failed to load squad from {file_path}",
        details=reason
    )


def api_connection_error(service_name: str, reason: str) -> APIConnectionError:
    """Create an APIConnectionError with standard formatting."""
    return APIConnectionError(
        f"Failed to connect to {service_name}",
        details=reason
    )


def notification_error(provider: str, reason: str) -> NotificationError:
    """Create a NotificationError with standard formatting."""
    if provider.lower() == "email":
        return EmailNotificationError(
            f"Failed to send email notification",
            details=reason
        )
    elif provider.lower() == "discord":
        return DiscordNotificationError(
            f"Failed to send Discord notification",
            details=reason
        )
    else:
        return NotificationError(
            f"Failed to send {provider} notification",
            details=reason
        )


def configuration_error(setting_name: str, reason: str) -> ConfigurationError:
    """Create a ConfigurationError with standard formatting."""
    return InvalidConfigurationError(
        f"Invalid configuration for {setting_name}",
        details=reason
    )


# Football Data Provider Exceptions
class FootballDataProviderError(LineupMonitorError):
    """Base exception for football data provider errors."""
    pass


class RateLimitExceededError(FootballDataProviderError):
    """Raised when API rate limit is exceeded."""
    pass


class DataNotAvailableError(FootballDataProviderError):
    """Raised when requested data is not available."""
    pass


class LineupMonitoringError(LineupMonitorError):
    """Raised when lineup monitoring operations fail."""
    pass
