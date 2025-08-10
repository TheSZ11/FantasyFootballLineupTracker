"""
Application configuration management with validation and type safety.

Provides centralized configuration handling with environment variable loading,
validation, and structured access to all application settings.
"""

import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from pathlib import Path
from dotenv import load_dotenv

from ..domain.exceptions import ConfigurationError, MissingConfigurationError, InvalidConfigurationError


logger = logging.getLogger(__name__)


@dataclass
class APIConfig:
    """API configuration settings with validation."""
    
    base_url: str = "https://api.sofascore.com"
    timeout_seconds: int = 30
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    connection_pool_size: int = 10
    max_concurrent_requests: int = 5
    
    def __post_init__(self):
        """Validate API configuration."""
        if self.timeout_seconds <= 0:
            raise InvalidConfigurationError("API timeout must be positive")
        if self.max_retries < 0:
            raise InvalidConfigurationError("Max retries cannot be negative")
        if self.rate_limit_per_minute <= 0:
            raise InvalidConfigurationError("Rate limit must be positive")
        if not self.base_url.startswith(('http://', 'https://')):
            raise InvalidConfigurationError("API base URL must start with http:// or https://")


@dataclass
class EmailConfig:
    """Email notification configuration with validation."""
    
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    recipient: str
    use_tls: bool = True
    timeout_seconds: int = 30
    
    def __post_init__(self):
        """Validate email configuration."""
        if not all([self.smtp_server, self.username, self.password, self.recipient]):
            raise InvalidConfigurationError("All email fields (server, username, password, recipient) must be provided")
        
        if not (1 <= self.smtp_port <= 65535):
            raise InvalidConfigurationError("SMTP port must be between 1 and 65535")
        
        if '@' not in self.recipient:
            raise InvalidConfigurationError("Recipient must be a valid email address")
        
        if self.timeout_seconds <= 0:
            raise InvalidConfigurationError("Email timeout must be positive")


@dataclass
class DiscordConfig:
    """Discord notification configuration with validation."""
    
    webhook_url: str
    timeout_seconds: int = 30
    retry_attempts: int = 3
    
    def __post_init__(self):
        """Validate Discord configuration."""
        if not self.webhook_url:
            raise InvalidConfigurationError("Discord webhook URL is required")
        
        if not self.webhook_url.startswith('https://discord.com/api/webhooks/'):
            raise InvalidConfigurationError("Discord webhook URL must be a valid Discord webhook")
        
        if self.timeout_seconds <= 0:
            raise InvalidConfigurationError("Discord timeout must be positive")
        
        if self.retry_attempts < 0:
            raise InvalidConfigurationError("Discord retry attempts cannot be negative")


@dataclass
class NotificationConfig:
    """Notification system configuration with provider settings."""
    
    email_enabled: bool = False
    discord_enabled: bool = False
    email: Optional[EmailConfig] = None
    discord: Optional[DiscordConfig] = None
    
    # Notification behavior settings
    send_startup_notifications: bool = True
    send_shutdown_notifications: bool = True
    send_error_notifications: bool = True
    send_confirmation_alerts: bool = True
    
    def __post_init__(self):
        """Validate notification configuration."""
        if self.email_enabled and not self.email:
            raise InvalidConfigurationError("Email config required when email notifications enabled")
        
        if self.discord_enabled and not self.discord:
            raise InvalidConfigurationError("Discord config required when Discord notifications enabled")
        
        if not self.email_enabled and not self.discord_enabled:
            logger.warning("No notification providers enabled - alerts will not be sent")


@dataclass
class MonitoringConfig:
    """Monitoring behavior configuration with validation."""
    
    # Core monitoring settings
    check_interval_minutes: int = 15
    pre_match_window_minutes: int = 60
    final_sprint_minutes: int = 5
    final_sprint_interval_minutes: int = 1
    
    # File and data settings
    squad_file_path: str = "my_roster.csv"
    backup_squad_file_path: Optional[str] = None
    
    # Analysis settings
    min_analysis_interval_minutes: int = 5
    cache_lineup_data_minutes: int = 10
    
    # Safety and limits
    max_concurrent_requests: int = 5
    max_monitoring_cycles_per_day: int = 200
    
    def __post_init__(self):
        """Validate monitoring configuration."""
        if self.check_interval_minutes <= 0:
            raise InvalidConfigurationError("Check interval must be positive")
        
        if self.pre_match_window_minutes <= 0:
            raise InvalidConfigurationError("Pre-match window must be positive")
        
        if self.final_sprint_minutes <= 0:
            raise InvalidConfigurationError("Final sprint minutes must be positive")
        
        if self.final_sprint_interval_minutes <= 0:
            raise InvalidConfigurationError("Final sprint interval must be positive")
        
        if self.final_sprint_interval_minutes >= self.final_sprint_minutes:
            raise InvalidConfigurationError("Final sprint interval must be less than final sprint duration")
        
        if self.min_analysis_interval_minutes <= 0:
            raise InvalidConfigurationError("Minimum analysis interval must be positive")
        
        if not self.squad_file_path:
            raise InvalidConfigurationError("Squad file path is required")
        
        if self.max_concurrent_requests <= 0:
            raise InvalidConfigurationError("Max concurrent requests must be positive")


@dataclass
class LoggingConfig:
    """Logging configuration with structured logging support."""
    
    level: str = "INFO"
    format_type: str = "structured"  # "structured" or "simple"
    log_file: Optional[str] = None
    max_file_size_mb: int = 10
    backup_count: int = 5
    enable_console: bool = True
    correlation_tracking: bool = True
    
    def __post_init__(self):
        """Validate logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.level.upper() not in valid_levels:
            raise InvalidConfigurationError(f"Log level must be one of: {valid_levels}")
        
        valid_formats = ["structured", "simple"]
        if self.format_type not in valid_formats:
            raise InvalidConfigurationError(f"Log format must be one of: {valid_formats}")
        
        if self.max_file_size_mb <= 0:
            raise InvalidConfigurationError("Max file size must be positive")
        
        if self.backup_count < 0:
            raise InvalidConfigurationError("Backup count cannot be negative")


@dataclass
class SecurityConfig:
    """Security-related configuration settings."""
    
    max_request_timeout_seconds: int = 60
    allowed_file_extensions: List[str] = field(default_factory=lambda: ['.csv', '.txt'])
    max_file_size_mb: int = 10
    enable_file_validation: bool = True
    
    def __post_init__(self):
        """Validate security configuration."""
        if self.max_request_timeout_seconds <= 0:
            raise InvalidConfigurationError("Max request timeout must be positive")
        
        if self.max_file_size_mb <= 0:
            raise InvalidConfigurationError("Max file size must be positive")
        
        if not self.allowed_file_extensions:
            raise InvalidConfigurationError("At least one file extension must be allowed")


@dataclass
class AppConfig:
    """Main application configuration container."""
    
    # Core configuration sections
    api_settings: APIConfig
    notification_settings: NotificationConfig
    monitoring_settings: MonitoringConfig
    logging_settings: LoggingConfig
    security_settings: SecurityConfig
    
    # Global application settings
    user_timezone: str = "UTC"
    environment: str = "production"  # development, staging, production
    debug_mode: bool = False
    
    def __post_init__(self):
        """Validate overall configuration."""
        valid_environments = ["development", "staging", "production"]
        if self.environment not in valid_environments:
            raise InvalidConfigurationError(f"Environment must be one of: {valid_environments}")
        
        # Adjust debug mode based on environment
        if self.environment == "development" and not hasattr(self, '_debug_mode_set'):
            self.debug_mode = True
    
    @classmethod
    def from_env(cls, env_file: Optional[str] = None) -> 'AppConfig':
        """
        Create configuration from environment variables.
        
        Args:
            env_file: Optional path to .env file
            
        Returns:
            Fully configured AppConfig instance
            
        Raises:
            MissingConfigurationError: When required settings are missing
            InvalidConfigurationError: When settings are invalid
        """
        # Load environment variables
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()
        
        logger.info("Loading application configuration from environment")
        
        try:
            # API settings
            api_settings = APIConfig(
                base_url=os.getenv('API_BASE_URL', 'https://api.sofascore.com'),
                timeout_seconds=int(os.getenv('API_TIMEOUT_SECONDS', '30')),
                max_retries=int(os.getenv('API_MAX_RETRIES', '3')),
                rate_limit_per_minute=int(os.getenv('API_RATE_LIMIT_PER_MINUTE', '60')),
                connection_pool_size=int(os.getenv('API_CONNECTION_POOL_SIZE', '10'))
            )
            
            # Email settings (optional)
            email_config = None
            if all(os.getenv(key) for key in ['EMAIL_SMTP_SERVER', 'EMAIL_USERNAME', 'EMAIL_PASSWORD', 'EMAIL_RECIPIENT']):
                email_config = EmailConfig(
                    smtp_server=os.getenv('EMAIL_SMTP_SERVER'),
                    smtp_port=int(os.getenv('EMAIL_SMTP_PORT', '587')),
                    username=os.getenv('EMAIL_USERNAME'),
                    password=os.getenv('EMAIL_PASSWORD'),
                    recipient=os.getenv('EMAIL_RECIPIENT'),
                    use_tls=os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true',
                    timeout_seconds=int(os.getenv('EMAIL_TIMEOUT_SECONDS', '30'))
                )
            
            # Discord settings (optional)
            discord_config = None
            if os.getenv('DISCORD_WEBHOOK_URL'):
                discord_config = DiscordConfig(
                    webhook_url=os.getenv('DISCORD_WEBHOOK_URL'),
                    timeout_seconds=int(os.getenv('DISCORD_TIMEOUT_SECONDS', '30')),
                    retry_attempts=int(os.getenv('DISCORD_RETRY_ATTEMPTS', '3'))
                )
            
            # Notification settings
            notification_settings = NotificationConfig(
                email_enabled=email_config is not None and os.getenv('EMAIL_ENABLED', 'true').lower() == 'true',
                discord_enabled=discord_config is not None and os.getenv('DISCORD_ENABLED', 'true').lower() == 'true',
                email=email_config,
                discord=discord_config,
                send_startup_notifications=os.getenv('SEND_STARTUP_NOTIFICATIONS', 'true').lower() == 'true',
                send_shutdown_notifications=os.getenv('SEND_SHUTDOWN_NOTIFICATIONS', 'true').lower() == 'true',
                send_error_notifications=os.getenv('SEND_ERROR_NOTIFICATIONS', 'true').lower() == 'true',
                send_confirmation_alerts=os.getenv('SEND_CONFIRMATION_ALERTS', 'true').lower() == 'true'
            )
            
            # Monitoring settings
            monitoring_settings = MonitoringConfig(
                check_interval_minutes=int(os.getenv('CHECK_INTERVAL_MINUTES', '15')),
                pre_match_window_minutes=int(os.getenv('PRE_MATCH_WINDOW_MINUTES', '60')),
                final_sprint_minutes=int(os.getenv('FINAL_SPRINT_MINUTES', '5')),
                final_sprint_interval_minutes=int(os.getenv('FINAL_SPRINT_INTERVAL_MINUTES', '1')),
                squad_file_path=os.getenv('SQUAD_FILE_PATH', 'my_roster.csv'),
                backup_squad_file_path=os.getenv('BACKUP_SQUAD_FILE_PATH'),
                min_analysis_interval_minutes=int(os.getenv('MIN_ANALYSIS_INTERVAL_MINUTES', '5')),
                cache_lineup_data_minutes=int(os.getenv('CACHE_LINEUP_DATA_MINUTES', '10')),
                max_concurrent_requests=int(os.getenv('MAX_CONCURRENT_REQUESTS', '5')),
                max_monitoring_cycles_per_day=int(os.getenv('MAX_MONITORING_CYCLES_PER_DAY', '200'))
            )
            
            # Logging settings
            logging_settings = LoggingConfig(
                level=os.getenv('LOG_LEVEL', 'INFO').upper(),
                format_type=os.getenv('LOG_FORMAT', 'structured'),
                log_file=os.getenv('LOG_FILE'),
                max_file_size_mb=int(os.getenv('LOG_MAX_FILE_SIZE_MB', '10')),
                backup_count=int(os.getenv('LOG_BACKUP_COUNT', '5')),
                enable_console=os.getenv('LOG_ENABLE_CONSOLE', 'true').lower() == 'true',
                correlation_tracking=os.getenv('LOG_CORRELATION_TRACKING', 'true').lower() == 'true'
            )
            
            # Security settings
            security_settings = SecurityConfig(
                max_request_timeout_seconds=int(os.getenv('SECURITY_MAX_REQUEST_TIMEOUT', '60')),
                allowed_file_extensions=os.getenv('SECURITY_ALLOWED_FILE_EXTENSIONS', '.csv,.txt').split(','),
                max_file_size_mb=int(os.getenv('SECURITY_MAX_FILE_SIZE_MB', '10')),
                enable_file_validation=os.getenv('SECURITY_ENABLE_FILE_VALIDATION', 'true').lower() == 'true'
            )
            
            # Create main config
            config = cls(
                api_settings=api_settings,
                notification_settings=notification_settings,
                monitoring_settings=monitoring_settings,
                logging_settings=logging_settings,
                security_settings=security_settings,
                user_timezone=os.getenv('USER_TIMEZONE', 'UTC'),
                environment=os.getenv('ENVIRONMENT', 'production'),
                debug_mode=os.getenv('DEBUG_MODE', 'false').lower() == 'true'
            )
            
            logger.info(f"Configuration loaded successfully for environment: {config.environment}")
            return config
            
        except ValueError as e:
            raise InvalidConfigurationError(f"Invalid configuration value: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AppConfig':
        """
        Create configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            AppConfig instance
        """
        try:
            api_settings = APIConfig(**config_dict.get('api_settings', {}))
            
            # Handle notification settings
            notification_data = config_dict.get('notification_settings', {})
            email_config = None
            if notification_data.get('email'):
                email_config = EmailConfig(**notification_data['email'])
            
            discord_config = None
            if notification_data.get('discord'):
                discord_config = DiscordConfig(**notification_data['discord'])
            
            notification_settings = NotificationConfig(
                email_enabled=notification_data.get('email_enabled', False),
                discord_enabled=notification_data.get('discord_enabled', False),
                email=email_config,
                discord=discord_config,
                **{k: v for k, v in notification_data.items() 
                   if k not in ['email', 'discord', 'email_enabled', 'discord_enabled']}
            )
            
            monitoring_settings = MonitoringConfig(**config_dict.get('monitoring_settings', {}))
            logging_settings = LoggingConfig(**config_dict.get('logging_settings', {}))
            security_settings = SecurityConfig(**config_dict.get('security_settings', {}))
            
            return cls(
                api_settings=api_settings,
                notification_settings=notification_settings,
                monitoring_settings=monitoring_settings,
                logging_settings=logging_settings,
                security_settings=security_settings,
                **{k: v for k, v in config_dict.items() 
                   if k not in ['api_settings', 'notification_settings', 'monitoring_settings', 
                               'logging_settings', 'security_settings']}
            )
            
        except Exception as e:
            raise ConfigurationError(f"Failed to create configuration from dictionary: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'api_settings': {
                'base_url': self.api_settings.base_url,
                'timeout_seconds': self.api_settings.timeout_seconds,
                'max_retries': self.api_settings.max_retries,
                'rate_limit_per_minute': self.api_settings.rate_limit_per_minute,
                'connection_pool_size': self.api_settings.connection_pool_size
            },
            'notification_settings': {
                'email_enabled': self.notification_settings.email_enabled,
                'discord_enabled': self.notification_settings.discord_enabled,
                'send_startup_notifications': self.notification_settings.send_startup_notifications,
                'send_shutdown_notifications': self.notification_settings.send_shutdown_notifications,
                'send_error_notifications': self.notification_settings.send_error_notifications,
                'send_confirmation_alerts': self.notification_settings.send_confirmation_alerts,
                'email': {
                    'smtp_server': self.notification_settings.email.smtp_server,
                    'smtp_port': self.notification_settings.email.smtp_port,
                    'username': self.notification_settings.email.username,
                    'recipient': self.notification_settings.email.recipient,
                    'use_tls': self.notification_settings.email.use_tls,
                    'timeout_seconds': self.notification_settings.email.timeout_seconds
                } if self.notification_settings.email else None,
                'discord': {
                    'webhook_url': self.notification_settings.discord.webhook_url,
                    'timeout_seconds': self.notification_settings.discord.timeout_seconds,
                    'retry_attempts': self.notification_settings.discord.retry_attempts
                } if self.notification_settings.discord else None
            },
            'monitoring_settings': {
                'check_interval_minutes': self.monitoring_settings.check_interval_minutes,
                'pre_match_window_minutes': self.monitoring_settings.pre_match_window_minutes,
                'final_sprint_minutes': self.monitoring_settings.final_sprint_minutes,
                'final_sprint_interval_minutes': self.monitoring_settings.final_sprint_interval_minutes,
                'squad_file_path': self.monitoring_settings.squad_file_path,
                'backup_squad_file_path': self.monitoring_settings.backup_squad_file_path,
                'min_analysis_interval_minutes': self.monitoring_settings.min_analysis_interval_minutes,
                'cache_lineup_data_minutes': self.monitoring_settings.cache_lineup_data_minutes,
                'max_concurrent_requests': self.monitoring_settings.max_concurrent_requests,
                'max_monitoring_cycles_per_day': self.monitoring_settings.max_monitoring_cycles_per_day
            },
            'logging_settings': {
                'level': self.logging_settings.level,
                'format_type': self.logging_settings.format_type,
                'log_file': self.logging_settings.log_file,
                'max_file_size_mb': self.logging_settings.max_file_size_mb,
                'backup_count': self.logging_settings.backup_count,
                'enable_console': self.logging_settings.enable_console,
                'correlation_tracking': self.logging_settings.correlation_tracking
            },
            'security_settings': {
                'max_request_timeout_seconds': self.security_settings.max_request_timeout_seconds,
                'allowed_file_extensions': self.security_settings.allowed_file_extensions,
                'max_file_size_mb': self.security_settings.max_file_size_mb,
                'enable_file_validation': self.security_settings.enable_file_validation
            },
            'user_timezone': self.user_timezone,
            'environment': self.environment,
            'debug_mode': self.debug_mode
        }
    
    def validate_runtime_requirements(self) -> List[str]:
        """
        Validate runtime requirements and return any issues.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        issues = []
        
        # Check squad file exists
        squad_path = Path(self.monitoring_settings.squad_file_path)
        if not squad_path.exists():
            issues.append(f"Squad file not found: {squad_path}")
        elif not squad_path.is_file():
            issues.append(f"Squad path is not a file: {squad_path}")
        
        # Check backup squad file if specified
        if self.monitoring_settings.backup_squad_file_path:
            backup_path = Path(self.monitoring_settings.backup_squad_file_path)
            if not backup_path.exists():
                issues.append(f"Backup squad file not found: {backup_path}")
        
        # Check log file directory if specified
        if self.logging_settings.log_file:
            log_path = Path(self.logging_settings.log_file)
            log_dir = log_path.parent
            if not log_dir.exists():
                try:
                    log_dir.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    issues.append(f"Cannot create log directory {log_dir}: {e}")
        
        # Validate timezone
        try:
            import zoneinfo
            zoneinfo.ZoneInfo(self.user_timezone)
        except Exception:
            try:
                import pytz
                pytz.timezone(self.user_timezone)
            except Exception:
                issues.append(f"Invalid timezone: {self.user_timezone}")
        
        return issues
    
    def get_summary(self) -> str:
        """Get a human-readable configuration summary."""
        summary_lines = [
            f"🔧 LineupTracker Configuration Summary",
            f"   Environment: {self.environment}",
            f"   Debug Mode: {self.debug_mode}",
            f"   User Timezone: {self.user_timezone}",
            "",
            f"📡 API Settings:",
            f"   Base URL: {self.api_settings.base_url}",
            f"   Timeout: {self.api_settings.timeout_seconds}s",
            f"   Max Retries: {self.api_settings.max_retries}",
            f"   Rate Limit: {self.api_settings.rate_limit_per_minute}/min",
            "",
            f"📬 Notifications:",
            f"   Email: {'✅ Enabled' if self.notification_settings.email_enabled else '❌ Disabled'}",
            f"   Discord: {'✅ Enabled' if self.notification_settings.discord_enabled else '❌ Disabled'}",
            "",
            f"⏰ Monitoring:",
            f"   Check Interval: {self.monitoring_settings.check_interval_minutes} minutes",
            f"   Squad File: {self.monitoring_settings.squad_file_path}",
            f"   Pre-match Window: {self.monitoring_settings.pre_match_window_minutes} minutes",
            "",
            f"📝 Logging:",
            f"   Level: {self.logging_settings.level}",
            f"   Format: {self.logging_settings.format_type}",
            f"   File: {self.logging_settings.log_file or 'Console only'}",
        ]
        
        return "\n".join(summary_lines)
