"""
Configuration loader with environment detection and validation.

Provides intelligent configuration loading with environment-specific defaults,
validation, and integration with the dependency injection system.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path

from .app_config import AppConfig
from ..domain.exceptions import ConfigurationError, MissingConfigurationError
from ..utils.logging import get_logger

logger = get_logger(__name__)


class ConfigurationLoader:
    """
    Intelligent configuration loader with environment detection.
    
    Handles loading configuration from multiple sources with proper
    precedence and validation.
    """
    
    def __init__(self):
        self._config_cache: Optional[AppConfig] = None
        self._config_sources = []
    
    def load_config(
        self,
        env_file: Optional[str] = None,
        config_file: Optional[str] = None,
        environment: Optional[str] = None,
        validate_runtime: bool = True
    ) -> AppConfig:
        """
        Load configuration from multiple sources with precedence.
        
        Precedence (highest to lowest):
        1. Environment variables
        2. Config file (JSON/YAML)
        3. Environment-specific defaults
        4. Application defaults
        
        Args:
            env_file: Path to .env file
            config_file: Path to JSON/YAML config file
            environment: Override environment detection
            validate_runtime: Whether to validate runtime requirements
            
        Returns:
            Fully loaded and validated AppConfig
            
        Raises:
            ConfigurationError: When configuration is invalid or missing
        """
        if self._config_cache:
            logger.debug("Returning cached configuration")
            return self._config_cache
        
        try:
            logger.info("Loading application configuration")
            
            # Detect environment
            detected_env = environment or self._detect_environment()
            logger.info(f"Detected environment: {detected_env}")
            
            # Load base configuration
            config = self._load_base_config(env_file, config_file, detected_env)
            
            # Apply environment-specific overrides
            config = self._apply_environment_overrides(config, detected_env)
            
            # Validate configuration
            self._validate_configuration(config, validate_runtime)
            
            # Cache the configuration
            self._config_cache = config
            
            logger.info("Configuration loaded successfully")
            logger.debug(f"Configuration summary:\n{config.get_summary()}")
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration loading failed: {e}")
    
    def reload_config(self, **kwargs) -> AppConfig:
        """
        Force reload configuration clearing cache.
        
        Args:
            **kwargs: Arguments passed to load_config
            
        Returns:
            Freshly loaded AppConfig
        """
        logger.info("Reloading configuration (clearing cache)")
        self._config_cache = None
        return self.load_config(**kwargs)
    
    def _detect_environment(self) -> str:
        """
        Detect current environment from various sources.
        
        Returns:
            Environment name (development, staging, production)
        """
        # Check environment variable
        env = os.getenv('ENVIRONMENT', '').lower()
        if env in ['development', 'staging', 'production']:
            return env
        
        # Check for development indicators
        if os.getenv('DEBUG', '').lower() == 'true':
            return 'development'
        
        # Check if running in a development-like environment
        if any(indicator in os.getcwd().lower() for indicator in ['dev', 'test', 'local']):
            return 'development'
        
        # Check for common CI/CD environment variables
        ci_indicators = ['CI', 'CONTINUOUS_INTEGRATION', 'BUILD_NUMBER', 'JENKINS_URL']
        if any(os.getenv(indicator) for indicator in ci_indicators):
            return 'staging'
        
        # Default to production for safety
        return 'production'
    
    def _load_base_config(
        self,
        env_file: Optional[str],
        config_file: Optional[str],
        environment: str
    ) -> AppConfig:
        """
        Load base configuration from environment and files.
        
        Args:
            env_file: Path to .env file
            config_file: Path to config file
            environment: Current environment
            
        Returns:
            Base AppConfig instance
        """
        config_data = {}
        
        # Load from config file if provided
        if config_file:
            config_data = self._load_config_file(config_file)
        
        # Load from environment (takes precedence)
        if config_data:
            # Merge with environment variables
            base_config = AppConfig.from_dict(config_data)
            # Override with environment variables
            env_config = AppConfig.from_env(env_file)
            config = self._merge_configs(base_config, env_config)
        else:
            # Load directly from environment
            config = AppConfig.from_env(env_file)
        
        return config
    
    def _load_config_file(self, config_file: str) -> Dict[str, Any]:
        """
        Load configuration from JSON or YAML file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            Configuration dictionary
            
        Raises:
            ConfigurationError: When file cannot be loaded
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise ConfigurationError(f"Configuration file not found: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                if config_path.suffix.lower() == '.json':
                    return json.load(f)
                elif config_path.suffix.lower() in ['.yml', '.yaml']:
                    try:
                        import yaml
                        return yaml.safe_load(f)
                    except ImportError:
                        raise ConfigurationError("PyYAML is required to load YAML configuration files")
                else:
                    raise ConfigurationError(f"Unsupported configuration file format: {config_path.suffix}")
                    
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file {config_path}: {e}")
    
    def _merge_configs(self, base_config: AppConfig, override_config: AppConfig) -> AppConfig:
        """
        Merge two configurations with override taking precedence.
        
        Args:
            base_config: Base configuration
            override_config: Override configuration
            
        Returns:
            Merged configuration
        """
        # For now, simply return the override config
        # In a more sophisticated implementation, we could merge individual fields
        return override_config
    
    def _apply_environment_overrides(self, config: AppConfig, environment: str) -> AppConfig:
        """
        Apply environment-specific configuration overrides.
        
        Args:
            config: Base configuration
            environment: Current environment
            
        Returns:
            Configuration with environment overrides applied
        """
        if environment == 'development':
            # Development-specific overrides
            config.debug_mode = True
            config.logging_settings.level = 'DEBUG'
            config.logging_settings.enable_console = True
            config.api_settings.timeout_seconds = min(config.api_settings.timeout_seconds, 10)
            
        elif environment == 'staging':
            # Staging-specific overrides
            config.debug_mode = False
            config.logging_settings.level = 'INFO'
            config.monitoring_settings.check_interval_minutes = max(
                config.monitoring_settings.check_interval_minutes, 5
            )
            
        elif environment == 'production':
            # Production-specific overrides
            config.debug_mode = False
            config.logging_settings.level = config.logging_settings.level or 'INFO'
            config.security_settings.enable_file_validation = True
            
            # Ensure conservative defaults for production
            config.api_settings.max_retries = min(config.api_settings.max_retries, 5)
            config.monitoring_settings.max_concurrent_requests = min(
                config.monitoring_settings.max_concurrent_requests, 3
            )
        
        return config
    
    def _validate_configuration(self, config: AppConfig, validate_runtime: bool = True):
        """
        Validate configuration for consistency and completeness.
        
        Args:
            config: Configuration to validate
            validate_runtime: Whether to check runtime requirements
            
        Raises:
            ConfigurationError: When validation fails
        """
        logger.debug("Validating configuration")
        
        # Basic validation is handled by dataclass __post_init__ methods
        
        # Additional cross-field validation
        issues = []
        
        # Check notification configuration
        if not config.notification_settings.email_enabled and not config.notification_settings.discord_enabled:
            issues.append("At least one notification provider should be enabled")
        
        # Check monitoring intervals make sense
        if (config.monitoring_settings.final_sprint_interval_minutes >= 
            config.monitoring_settings.check_interval_minutes):
            issues.append("Final sprint interval should be less than regular check interval")
        
        # Validate API settings for the environment
        if config.environment == 'production':
            if config.api_settings.rate_limit_per_minute > 120:
                issues.append("Rate limit too high for production environment")
            
            if config.api_settings.timeout_seconds > 60:
                issues.append("API timeout too high for production environment")
        
        # Runtime validation
        if validate_runtime:
            runtime_issues = config.validate_runtime_requirements()
            issues.extend(runtime_issues)
        
        # Report issues
        if issues:
            if any("not found" in issue or "required" in issue.lower() for issue in issues):
                # Treat missing files/required settings as errors
                error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {issue}" for issue in issues)
                raise ConfigurationError(error_msg)
            else:
                # Treat other issues as warnings
                warning_msg = "Configuration validation warnings:\n" + "\n".join(f"  - {issue}" for issue in issues)
                logger.warning(warning_msg)
        
        logger.debug("Configuration validation completed")
    
    def validate_config_file(self, config_file: str) -> List[str]:
        """
        Validate a configuration file without loading it.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            List of validation errors
        """
        try:
            config_data = self._load_config_file(config_file)
            config = AppConfig.from_dict(config_data)
            self._validate_configuration(config, validate_runtime=False)
            return []
            
        except Exception as e:
            return [str(e)]
    
    def get_config_template(self, environment: str = 'production') -> Dict[str, Any]:
        """
        Generate a configuration template for the specified environment.
        
        Args:
            environment: Target environment
            
        Returns:
            Configuration template dictionary
        """
        # Create a default configuration
        from .app_config import (
            APIConfig, NotificationConfig, MonitoringConfig, 
            LoggingConfig, SecurityConfig
        )
        
        config = AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(),
            security_settings=SecurityConfig(),
            environment=environment
        )
        
        # Apply environment-specific defaults
        config = self._apply_environment_overrides(config, environment)
        
        return config.to_dict()
    
    def export_env_template(self, file_path: str, environment: str = 'production'):
        """
        Export an environment variable template file.
        
        Args:
            file_path: Path to write the template
            environment: Target environment
        """
        template_lines = [
            f"# LineupTracker Configuration Template - {environment.upper()} Environment",
            f"# Generated configuration template for {environment} deployment",
            "",
            "# Environment Settings",
            f"ENVIRONMENT={environment}",
            "DEBUG_MODE=false",
            "USER_TIMEZONE=UTC",
            "",
            "# API Configuration",
            "API_BASE_URL=https://api.sofascore.com",
            "API_TIMEOUT_SECONDS=30",
            "API_MAX_RETRIES=3",
            "API_RATE_LIMIT_PER_MINUTE=60",
            "API_CONNECTION_POOL_SIZE=10",
            "",
            "# Email Notifications (optional)",
            "EMAIL_ENABLED=false",
            "# EMAIL_SMTP_SERVER=smtp.gmail.com",
            "# EMAIL_SMTP_PORT=587",
            "# EMAIL_USERNAME=your-email@gmail.com",
            "# EMAIL_PASSWORD=your-app-password",
            "# EMAIL_RECIPIENT=recipient@example.com",
            "# EMAIL_USE_TLS=true",
            "# EMAIL_TIMEOUT_SECONDS=30",
            "",
            "# Discord Notifications (optional)",
            "DISCORD_ENABLED=false",
            "# DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...",
            "# DISCORD_TIMEOUT_SECONDS=30",
            "# DISCORD_RETRY_ATTEMPTS=3",
            "",
            "# Notification Behavior",
            "SEND_STARTUP_NOTIFICATIONS=true",
            "SEND_SHUTDOWN_NOTIFICATIONS=true",
            "SEND_ERROR_NOTIFICATIONS=true",
            "SEND_CONFIRMATION_ALERTS=true",
            "",
            "# Monitoring Settings",
            "CHECK_INTERVAL_MINUTES=15",
            "PRE_MATCH_WINDOW_MINUTES=60",
            "FINAL_SPRINT_MINUTES=5",
            "FINAL_SPRINT_INTERVAL_MINUTES=1",
            "SQUAD_FILE_PATH=my_roster.csv",
            "# BACKUP_SQUAD_FILE_PATH=backup_roster.csv",
            "MIN_ANALYSIS_INTERVAL_MINUTES=5",
            "CACHE_LINEUP_DATA_MINUTES=10",
            "MAX_CONCURRENT_REQUESTS=5",
            "MAX_MONITORING_CYCLES_PER_DAY=200",
            "",
            "# Logging Configuration",
            "LOG_LEVEL=INFO",
            "LOG_FORMAT=structured",
            "# LOG_FILE=logs/lineup_tracker.log",
            "LOG_MAX_FILE_SIZE_MB=10",
            "LOG_BACKUP_COUNT=5",
            "LOG_ENABLE_CONSOLE=true",
            "LOG_CORRELATION_TRACKING=true",
            "",
            "# Security Settings",
            "SECURITY_MAX_REQUEST_TIMEOUT=60",
            "SECURITY_ALLOWED_FILE_EXTENSIONS=.csv,.txt",
            "SECURITY_MAX_FILE_SIZE_MB=10",
            "SECURITY_ENABLE_FILE_VALIDATION=true",
        ]
        
        if environment == 'development':
            template_lines.extend([
                "",
                "# Development Overrides",
                "DEBUG_MODE=true",
                "LOG_LEVEL=DEBUG",
                "API_TIMEOUT_SECONDS=10",
                "CHECK_INTERVAL_MINUTES=5",
            ])
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(template_lines))
        
        logger.info(f"Environment template exported to: {file_path}")


# Global configuration loader instance
_config_loader = ConfigurationLoader()


def load_config(**kwargs) -> AppConfig:
    """
    Load application configuration using the global loader.
    
    Args:
        **kwargs: Arguments passed to ConfigurationLoader.load_config
        
    Returns:
        Loaded AppConfig instance
    """
    return _config_loader.load_config(**kwargs)


def reload_config(**kwargs) -> AppConfig:
    """
    Reload application configuration clearing cache.
    
    Args:
        **kwargs: Arguments passed to ConfigurationLoader.load_config
        
    Returns:
        Reloaded AppConfig instance
    """
    return _config_loader.reload_config(**kwargs)


def get_config_loader() -> ConfigurationLoader:
    """Get the global configuration loader instance."""
    return _config_loader
