"""
Unit tests for configuration management system.

Tests configuration loading, validation, environment handling,
and integration with the dependency injection system.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch, Mock

from src.lineup_tracker.config import (
    AppConfig, APIConfig, EmailConfig, DiscordConfig,
    NotificationConfig, MonitoringConfig, LoggingConfig, SecurityConfig,
    ConfigurationLoader, load_config
)
from src.lineup_tracker.domain.exceptions import (
    ConfigurationError, InvalidConfigurationError, MissingConfigurationError
)


@pytest.mark.unit
class TestAPIConfig:
    """Test API configuration validation."""
    
    def test_valid_api_config(self):
        """Test creating valid API configuration."""
        config = APIConfig(
            base_url="https://api.example.com",
            timeout_seconds=30,
            max_retries=3,
            rate_limit_per_minute=60
        )
        
        assert config.base_url == "https://api.example.com"
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.rate_limit_per_minute == 60
    
    def test_invalid_timeout(self):
        """Test that invalid timeout raises error."""
        with pytest.raises(InvalidConfigurationError):
            APIConfig(timeout_seconds=0)
        
        with pytest.raises(InvalidConfigurationError):
            APIConfig(timeout_seconds=-1)
    
    def test_invalid_retries(self):
        """Test that invalid retries raises error."""
        with pytest.raises(InvalidConfigurationError):
            APIConfig(max_retries=-1)
    
    def test_invalid_rate_limit(self):
        """Test that invalid rate limit raises error."""
        with pytest.raises(InvalidConfigurationError):
            APIConfig(rate_limit_per_minute=0)
        
        with pytest.raises(InvalidConfigurationError):
            APIConfig(rate_limit_per_minute=-1)
    
    def test_invalid_url(self):
        """Test that invalid URL raises error."""
        with pytest.raises(InvalidConfigurationError):
            APIConfig(base_url="not-a-url")
        
        with pytest.raises(InvalidConfigurationError):
            APIConfig(base_url="ftp://invalid.com")


@pytest.mark.unit
class TestEmailConfig:
    """Test email configuration validation."""
    
    def test_valid_email_config(self):
        """Test creating valid email configuration."""
        config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user@gmail.com",
            password="password",
            recipient="recipient@example.com"
        )
        
        assert config.smtp_server == "smtp.gmail.com"
        assert config.smtp_port == 587
        assert config.username == "user@gmail.com"
        assert config.recipient == "recipient@example.com"
        assert config.use_tls is True
    
    def test_missing_required_fields(self):
        """Test that missing required fields raise error."""
        with pytest.raises(InvalidConfigurationError):
            EmailConfig(
                smtp_server="",
                smtp_port=587,
                username="user",
                password="pass",
                recipient="recipient@example.com"
            )
    
    def test_invalid_port(self):
        """Test that invalid port raises error."""
        with pytest.raises(InvalidConfigurationError):
            EmailConfig(
                smtp_server="smtp.gmail.com",
                smtp_port=0,
                username="user",
                password="pass",
                recipient="recipient@example.com"
            )
        
        with pytest.raises(InvalidConfigurationError):
            EmailConfig(
                smtp_server="smtp.gmail.com",
                smtp_port=99999,
                username="user",
                password="pass",
                recipient="recipient@example.com"
            )
    
    def test_invalid_recipient(self):
        """Test that invalid recipient raises error."""
        with pytest.raises(InvalidConfigurationError):
            EmailConfig(
                smtp_server="smtp.gmail.com",
                smtp_port=587,
                username="user",
                password="pass",
                recipient="not-an-email"
            )


@pytest.mark.unit
class TestDiscordConfig:
    """Test Discord configuration validation."""
    
    def test_valid_discord_config(self):
        """Test creating valid Discord configuration."""
        config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        
        assert config.webhook_url == "https://discord.com/api/webhooks/123/abc"
        assert config.timeout_seconds == 30
        assert config.retry_attempts == 3
    
    def test_invalid_webhook_url(self):
        """Test that invalid webhook URL raises error."""
        with pytest.raises(InvalidConfigurationError):
            DiscordConfig(webhook_url="")
        
        with pytest.raises(InvalidConfigurationError):
            DiscordConfig(webhook_url="https://example.com/webhook")
        
        with pytest.raises(InvalidConfigurationError):
            DiscordConfig(webhook_url="not-a-url")


@pytest.mark.unit
class TestNotificationConfig:
    """Test notification configuration validation."""
    
    def test_valid_notification_config(self):
        """Test creating valid notification configuration."""
        email_config = EmailConfig(
            smtp_server="smtp.gmail.com",
            smtp_port=587,
            username="user",
            password="pass",
            recipient="recipient@example.com"
        )
        
        discord_config = DiscordConfig(
            webhook_url="https://discord.com/api/webhooks/123/abc"
        )
        
        config = NotificationConfig(
            email_enabled=True,
            discord_enabled=True,
            email=email_config,
            discord=discord_config
        )
        
        assert config.email_enabled is True
        assert config.discord_enabled is True
        assert config.email == email_config
        assert config.discord == discord_config
    
    def test_enabled_without_config(self):
        """Test that enabled provider without config raises error."""
        with pytest.raises(InvalidConfigurationError):
            NotificationConfig(email_enabled=True, email=None)
        
        with pytest.raises(InvalidConfigurationError):
            NotificationConfig(discord_enabled=True, discord=None)
    
    def test_no_providers_warning(self, caplog):
        """Test warning when no providers are enabled."""
        import logging
        caplog.set_level(logging.WARNING)
        
        config = NotificationConfig(
            email_enabled=False,
            discord_enabled=False
        )
        
        assert "No notification providers enabled" in caplog.text


@pytest.mark.unit
class TestMonitoringConfig:
    """Test monitoring configuration validation."""
    
    def test_valid_monitoring_config(self):
        """Test creating valid monitoring configuration."""
        config = MonitoringConfig(
            check_interval_minutes=15,
            pre_match_window_minutes=60,
            final_sprint_minutes=5,
            final_sprint_interval_minutes=1,
            squad_file_path="my_roster.csv"
        )
        
        assert config.check_interval_minutes == 15
        assert config.pre_match_window_minutes == 60
        assert config.squad_file_path == "my_roster.csv"
    
    def test_invalid_intervals(self):
        """Test that invalid intervals raise error."""
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(check_interval_minutes=0)
        
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(pre_match_window_minutes=-1)
        
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(final_sprint_minutes=0)
        
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(final_sprint_interval_minutes=0)
    
    def test_sprint_interval_validation(self):
        """Test that sprint interval must be less than sprint duration."""
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(
                final_sprint_minutes=5,
                final_sprint_interval_minutes=10
            )
        
        with pytest.raises(InvalidConfigurationError):
            MonitoringConfig(
                final_sprint_minutes=5,
                final_sprint_interval_minutes=5
            )


@pytest.mark.unit
class TestAppConfig:
    """Test main application configuration."""
    
    def test_valid_app_config(self):
        """Test creating valid application configuration."""
        config = AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(),
            security_settings=SecurityConfig(),
            environment="production"
        )
        
        assert config.environment == "production"
        assert config.debug_mode is False
        assert isinstance(config.api_settings, APIConfig)
        assert isinstance(config.notification_settings, NotificationConfig)
    
    def test_invalid_environment(self):
        """Test that invalid environment raises error."""
        with pytest.raises(InvalidConfigurationError):
            AppConfig(
                api_settings=APIConfig(),
                notification_settings=NotificationConfig(),
                monitoring_settings=MonitoringConfig(),
                logging_settings=LoggingConfig(),
                security_settings=SecurityConfig(),
                environment="invalid"
            )
    
    def test_development_environment_defaults(self):
        """Test that development environment sets debug mode."""
        config = AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(),
            security_settings=SecurityConfig(),
            environment="development"
        )
        
        assert config.debug_mode is True
    
    def test_config_to_dict(self):
        """Test converting configuration to dictionary."""
        config = AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(),
            security_settings=SecurityConfig()
        )
        
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert 'api_settings' in config_dict
        assert 'notification_settings' in config_dict
        assert 'monitoring_settings' in config_dict
        assert 'logging_settings' in config_dict
        assert 'security_settings' in config_dict
    
    def test_config_from_dict(self):
        """Test creating configuration from dictionary."""
        config_dict = {
            'api_settings': {
                'base_url': 'https://api.example.com',
                'timeout_seconds': 30
            },
            'notification_settings': {
                'email_enabled': False,
                'discord_enabled': False
            },
            'monitoring_settings': {
                'squad_file_path': 'test.csv'
            },
            'logging_settings': {},
            'security_settings': {},
            'environment': 'staging'
        }
        
        config = AppConfig.from_dict(config_dict)
        
        assert config.environment == 'staging'
        assert config.api_settings.base_url == 'https://api.example.com'
        assert config.monitoring_settings.squad_file_path == 'test.csv'


@pytest.mark.unit
class TestConfigurationLoader:
    """Test configuration loader functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.loader = ConfigurationLoader()
    
    def test_environment_detection_from_var(self):
        """Test environment detection from environment variable."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}):
            env = self.loader._detect_environment()
            assert env == 'staging'
    
    def test_environment_detection_from_debug(self):
        """Test environment detection from debug flag."""
        with patch.dict(os.environ, {'DEBUG': 'true'}, clear=True):
            env = self.loader._detect_environment()
            assert env == 'development'
    
    def test_environment_detection_default(self):
        """Test default environment detection."""
        with patch.dict(os.environ, {}, clear=True):
            env = self.loader._detect_environment()
            assert env == 'production'
    
    def test_load_config_file_json(self):
        """Test loading JSON configuration file."""
        config_data = {
            'api_settings': {'base_url': 'https://api.test.com'},
            'notification_settings': {'email_enabled': False},
            'monitoring_settings': {},
            'logging_settings': {},
            'security_settings': {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                loaded_data = self.loader._load_config_file(f.name)
                assert loaded_data == config_data
            finally:
                os.unlink(f.name)
    
    def test_load_config_file_not_found(self):
        """Test error when configuration file not found."""
        with pytest.raises(ConfigurationError):
            self.loader._load_config_file("nonexistent.json")
    
    def test_validate_config_file(self):
        """Test configuration file validation."""
        config_data = {
            'api_settings': {'base_url': 'https://api.test.com'},
            'notification_settings': {'email_enabled': False, 'discord_enabled': False},
            'monitoring_settings': {},
            'logging_settings': {},
            'security_settings': {}
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            f.flush()
            
            try:
                errors = self.loader.validate_config_file(f.name)
                assert len(errors) == 0
            finally:
                os.unlink(f.name)
    
    def test_get_config_template(self):
        """Test configuration template generation."""
        template = self.loader.get_config_template('development')
        
        assert isinstance(template, dict)
        assert 'api_settings' in template
        assert 'notification_settings' in template
        assert 'monitoring_settings' in template
    
    def test_export_env_template(self):
        """Test environment template export."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            try:
                self.loader.export_env_template(f.name, 'production')
                
                # Check file was created and has content
                with open(f.name, 'r') as read_file:
                    content = read_file.read()
                    assert 'ENVIRONMENT=production' in content
                    assert 'API_BASE_URL' in content
                    assert 'DISCORD_WEBHOOK_URL' in content
                    
            finally:
                os.unlink(f.name)
    
    @patch.dict(os.environ, {
        'ENVIRONMENT': 'development',
        'API_TIMEOUT_SECONDS': '15',
        'DISCORD_WEBHOOK_URL': 'https://discord.com/api/webhooks/123/abc',
        'DISCORD_ENABLED': 'true'
    })
    def test_load_from_environment(self):
        """Test loading configuration from environment variables."""
        config = self.loader.load_config(validate_runtime=False)
        
        assert config.environment == 'development'
        assert config.debug_mode is True
        assert config.api_settings.timeout_seconds == 15
        assert config.notification_settings.discord_enabled is True
    
    def test_config_caching(self):
        """Test that configuration is cached."""
        with patch('src.lineup_tracker.config.config_loader.AppConfig.from_env') as mock_from_env:
            mock_config = Mock()
            mock_from_env.return_value = mock_config
            
            # First call
            config1 = self.loader.load_config(validate_runtime=False)
            # Second call
            config2 = self.loader.load_config(validate_runtime=False)
            
            assert config1 is config2
            assert mock_from_env.call_count == 1
    
    def test_config_reload_clears_cache(self):
        """Test that reload clears the cache."""
        with patch('src.lineup_tracker.config.config_loader.AppConfig.from_env') as mock_from_env:
            mock_config1 = Mock()
            mock_config2 = Mock()
            mock_from_env.side_effect = [mock_config1, mock_config2]
            
            # Load, reload, and load again
            config1 = self.loader.load_config(validate_runtime=False)
            config2 = self.loader.reload_config(validate_runtime=False)
            
            assert config1 is not config2
            assert mock_from_env.call_count == 2


@pytest.mark.unit
class TestConfigurationIntegration:
    """Test configuration integration with other systems."""
    
    def test_container_configuration_loading(self):
        """Test that container loads configuration properly."""
        from src.lineup_tracker.container import Container
        
        with patch('src.lineup_tracker.config.config_loader.load_config') as mock_load:
            mock_config = Mock()
            mock_config.notification_settings = Mock()
            mock_config.notification_settings.email_enabled = False
            mock_config.notification_settings.discord_enabled = False
            mock_config.monitoring_settings = Mock()
            mock_config.monitoring_settings.squad_file_path = 'test.csv'
            mock_load.return_value = mock_config
            
            container = Container()
            
            assert container.config is mock_config
            mock_load.assert_called_once()
    
    def test_container_fallback_configuration(self):
        """Test that container falls back to minimal config on error."""
        from src.lineup_tracker.container import Container
        
        with patch('src.lineup_tracker.config.config_loader.load_config') as mock_load:
            mock_load.side_effect = ConfigurationError("Test error")
            
            container = Container()
            
            assert container.config is not None
            assert container.config.environment == 'development'
            assert container.config.debug_mode is True
    
    def test_logging_configuration_integration(self):
        """Test that logging can be configured from config."""
        from src.lineup_tracker.utils.logging import configure_logging
        
        config = AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(
                level="DEBUG",
                format_type="structured",
                enable_console=True
            ),
            security_settings=SecurityConfig()
        )
        
        # Should not raise any errors
        configure_logging(
            log_level=config.logging_settings.level,
            enable_console=config.logging_settings.enable_console,
            structured_format=config.logging_settings.format_type == "structured"
        )
