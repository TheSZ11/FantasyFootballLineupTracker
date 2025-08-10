"""
Dependency injection container for the LineupTracker application.

Manages the creation and lifecycle of all application dependencies,
enabling loose coupling and easy testing with mocks.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from .config import AppConfig, load_config
from .domain.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

# Import interfaces (we'll implement these in the next phases)
from .domain.interfaces import (
    FootballDataProvider,
    NotificationProvider, 
    SquadRepository,
    CacheProvider,
    HealthChecker,
    MetricsCollector
)


@dataclass
class Container:
    """
    Dependency injection container that manages all application dependencies.
    
    This container follows the Composition Root pattern, creating and wiring
    all dependencies in one place. It supports lazy initialization and
    proper lifecycle management.
    """
    
    # Configuration will be injected during container creation
    config: Optional[AppConfig] = None
    
    # Internal cache for singleton instances
    _instances: Dict[str, Any] = field(default_factory=dict, init=False)
    _is_initialized: bool = field(default=False, init=False)
    
    def __post_init__(self):
        """Initialize the container after creation."""
        if self.config is None:
            # Load configuration from environment
            try:
                self.config = load_config()
                logger.info("Configuration loaded successfully in container")
            except ConfigurationError as e:
                logger.error(f"Failed to load configuration: {e}")
                # Fall back to minimal config for testing
                self.config = self._create_minimal_config()
        
        self._is_initialized = True
    
    def _create_minimal_config(self) -> AppConfig:
        """Create minimal configuration for testing/fallback."""
        from .config import (
            APIConfig, NotificationConfig, MonitoringConfig, 
            LoggingConfig, SecurityConfig
        )
        
        return AppConfig(
            api_settings=APIConfig(),
            notification_settings=NotificationConfig(),
            monitoring_settings=MonitoringConfig(),
            logging_settings=LoggingConfig(),
            security_settings=SecurityConfig(),
            environment='development',
            debug_mode=True
        )
    
    # Lazy property accessors for all dependencies
    
    @property
    def football_api(self) -> FootballDataProvider:
        """Get the football data provider (API client)."""
        if 'football_api' not in self._instances:
            # We'll implement this in Phase 2 - for now return a placeholder
            self._instances['football_api'] = self._create_football_api()
        return self._instances['football_api']
    
    @property
    def squad_repository(self) -> SquadRepository:
        """Get the squad repository for data access."""
        if 'squad_repository' not in self._instances:
            # We'll implement this in Phase 2 - for now return a placeholder
            self._instances['squad_repository'] = self._create_squad_repository()
        return self._instances['squad_repository']
    
    @property
    def notification_service(self) -> Any:  # Will be NotificationService in Phase 2
        """Get the notification service."""
        if 'notification_service' not in self._instances:
            # We'll implement this in Phase 2 - for now return a placeholder
            self._instances['notification_service'] = self._create_notification_service()
        return self._instances['notification_service']
    
    @property
    def cache_provider(self) -> CacheProvider:
        """Get the cache provider."""
        if 'cache_provider' not in self._instances:
            self._instances['cache_provider'] = self._create_cache_provider()
        return self._instances['cache_provider']
    
    @property
    def health_checker(self) -> HealthChecker:
        """Get the health checker."""
        if 'health_checker' not in self._instances:
            self._instances['health_checker'] = self._create_health_checker()
        return self._instances['health_checker']
    
    @property
    def metrics_collector(self) -> MetricsCollector:
        """Get the metrics collector."""
        if 'metrics_collector' not in self._instances:
            self._instances['metrics_collector'] = self._create_metrics_collector()
        return self._instances['metrics_collector']
    
    @property
    def lineup_analyzer(self) -> Any:  # Will be LineupAnalyzer
        """Get the lineup analyzer."""
        if 'lineup_analyzer' not in self._instances:
            self._instances['lineup_analyzer'] = self._create_lineup_analyzer()
        return self._instances['lineup_analyzer']
    
    @property
    def alert_generator(self) -> Any:  # Will be AlertGenerator
        """Get the alert generator."""
        if 'alert_generator' not in self._instances:
            self._instances['alert_generator'] = self._create_alert_generator()
        return self._instances['alert_generator']
    
    @property
    def lineup_monitoring_service(self) -> Any:  # Will be LineupMonitoringService
        """Get the main lineup monitoring service."""
        if 'lineup_monitoring_service' not in self._instances:
            self._instances['lineup_monitoring_service'] = self._create_lineup_monitoring_service()
        return self._instances['lineup_monitoring_service']
    
    # Factory methods for creating dependencies
    
    def _create_football_api(self) -> FootballDataProvider:
        """Create the football data provider with async support."""
        # Use high-performance async client for production/staging
        if self.config.environment in ['production', 'staging']:
            try:
                from .providers.async_sofascore_client import AsyncSofascoreClient
                return AsyncSofascoreClient(self.config.api_settings)
            except ImportError as e:
                logger.warning(f"Async client not available, falling back to placeholder: {e}")
        
        # For development/testing, create a minimal fallback
        logger.warning("Using minimal fallback football API for development")
        from .providers.async_sofascore_client import AsyncSofascoreClient
        return AsyncSofascoreClient(self.config.api_settings)
    
    def _create_squad_repository(self) -> SquadRepository:
        """Create the squad repository."""
        from .repositories.csv_squad_repository import CSVSquadRepository
        return CSVSquadRepository()
    
    def _create_notification_service(self) -> Any:
        """Create the notification service with all configured providers."""
        from .services.notification_service import NotificationService
        
        providers = []
        notification_config = self.config.notification_settings
        
        # Create Discord provider if configured
        if notification_config.discord_enabled and notification_config.discord:
            try:
                from .providers.discord_provider import DiscordProvider
                providers.append(DiscordProvider(notification_config.discord.webhook_url))
                logger.info("Discord notification provider initialized")
            except Exception as e:
                logger.warning(f"Failed to create Discord provider: {e}")
        
        # Create Email provider if configured
        if notification_config.email_enabled and notification_config.email:
            try:
                from .providers.email_provider import EmailProvider
                providers.append(EmailProvider(
                    smtp_server=notification_config.email.smtp_server,
                    smtp_port=notification_config.email.smtp_port,
                    username=notification_config.email.username,
                    password=notification_config.email.password,
                    recipient=notification_config.email.recipient,
                    use_tls=notification_config.email.use_tls,
                    timeout_seconds=notification_config.email.timeout_seconds
                ))
                logger.info("Email notification provider initialized")
            except Exception as e:
                logger.warning(f"Failed to create Email provider: {e}")
        
        # Fall back to console logging if no providers available
        if not providers:
            logger.warning("No notification providers configured, alerts will be logged only")
            # Create a minimal console-only notification service
            class ConsoleNotificationService:
                async def send_alert(self, alert):
                    print(f"ALERT: {alert.message}")
                    return True
                async def send_message(self, message, urgency=None):
                    print(f"MESSAGE: {message}")
                    return True
                async def test_connection(self):
                    return True
            return ConsoleNotificationService()
        
        return NotificationService(providers)
    
    def _create_cache_provider(self) -> CacheProvider:
        """Create the cache provider with enhanced features."""
        # Use advanced TTL cache with performance optimizations
        from .utils.cache import TTLCache
        
        # Configure cache based on environment
        if self.config.environment == 'production':
            max_size = 2000
            cleanup_interval = 300  # 5 minutes
        elif self.config.environment == 'staging':
            max_size = 1000
            cleanup_interval = 600  # 10 minutes
        else:
            max_size = 500
            cleanup_interval = 900  # 15 minutes
        
        return TTLCache(max_size=max_size, cleanup_interval=cleanup_interval)
    
    def _create_health_checker(self) -> HealthChecker:
        """Create the health checker."""
        # Minimal health checker implementation
        class SimpleHealthChecker:
            def __init__(self, container):
                self.container = container
            async def check_health(self):
                return {'status': 'healthy', 'timestamp': 'now', 'services': {}}
            @property
            def service_name(self):
                return "simple_health_checker"
        return SimpleHealthChecker(self)
    
    def _create_metrics_collector(self) -> MetricsCollector:
        """Create the metrics collector."""
        # Minimal metrics collector implementation
        class SimpleMetricsCollector:
            def __init__(self):
                self._metrics = {}
            def record_duration(self, name, duration, **tags):
                pass  # Simple no-op implementation
            def increment_counter(self, name, value=1, **tags):
                pass  # Simple no-op implementation
            def get_metrics(self):
                return self._metrics
        return SimpleMetricsCollector()
    
    def _create_lineup_analyzer(self) -> Any:
        """Create the lineup analyzer."""
        from .business.lineup_analyzer import LineupAnalyzer
        return LineupAnalyzer()
    
    def _create_alert_generator(self) -> Any:
        """Create the alert generator."""
        from .business.alert_generator import AlertGenerator
        return AlertGenerator()
    
    def _create_lineup_monitoring_service(self) -> Any:
        """Create the main lineup monitoring service."""
        # Use async monitoring service for production/staging
        if self.config.environment in ['production', 'staging']:
            try:
                from .services.async_lineup_monitoring_service import AsyncLineupMonitoringService
                return AsyncLineupMonitoringService(
                    football_api=self.football_api,
                    squad_repository=self.squad_repository,
                    notification_service=self.notification_service,
                    lineup_analyzer=self.lineup_analyzer,
                    alert_generator=self.alert_generator,
                    config=self.config.monitoring_settings
                )
            except ImportError as e:
                logger.warning(f"Async monitoring service not available, falling back to sync: {e}")
        
        # Fallback to sync monitoring service
        from .services.lineup_monitoring_service import LineupMonitoringService
        
        squad_file_path = self.config.monitoring_settings.squad_file_path
        
        return LineupMonitoringService(
            football_api=self.football_api,
            squad_repository=self.squad_repository,
            notification_service=self.notification_service,
            lineup_analyzer=self.lineup_analyzer,
            alert_generator=self.alert_generator,
            squad_file_path=squad_file_path
        )
    
    # Container lifecycle management
    
    async def initialize(self) -> None:
        """Initialize all async dependencies."""
        # Initialize any async components
        if hasattr(self.football_api, 'initialize'):
            await self.football_api.initialize()
    
    async def shutdown(self) -> None:
        """Clean shutdown of all dependencies."""
        logger.info("🛑 Shutting down container dependencies")
        
        # Close all connections and clean up resources
        for instance_name, instance in self._instances.items():
            try:
                if hasattr(instance, 'close'):
                    if asyncio.iscoroutinefunction(instance.close):
                        await instance.close()
                    else:
                        instance.close()
                    logger.debug(f"✅ Closed {instance_name}")
                elif hasattr(instance, 'shutdown'):
                    if asyncio.iscoroutinefunction(instance.shutdown):
                        await instance.shutdown()
                    else:
                        instance.shutdown()
                    logger.debug(f"✅ Shut down {instance_name}")
            except Exception as e:
                # Log error but continue shutdown
                logger.error(f"❌ Error closing {instance_name}: {e}")
        
        self._instances.clear()
        logger.info("✅ Container shutdown complete")
    
    async def close(self):
        """Alias for shutdown for compatibility."""
        await self.shutdown()
    
    # Testing support
    
    def override_dependency(self, key: str, instance: Any) -> None:
        """
        Override a dependency with a mock/test implementation.
        
        This is useful for testing where you want to inject mock objects.
        
        Args:
            key: The dependency key (e.g., 'football_api')
            instance: The mock/test instance to use
        """
        self._instances[key] = instance
    
    def reset_dependencies(self) -> None:
        """Reset all dependencies - useful for testing."""
        self._instances.clear()
    
    def get_dependency_status(self) -> Dict[str, bool]:
        """Get the initialization status of all dependencies."""
        return {
            key: key in self._instances 
            for key in [
                'football_api', 'squad_repository', 'notification_service',
                'cache_provider', 'health_checker', 'metrics_collector',
                'lineup_analyzer', 'alert_generator', 'lineup_monitoring_service'
            ]
        }


# Global container instance - will be initialized at startup
_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get the global container instance.
    
    Returns:
        The global Container instance
        
    Raises:
        RuntimeError: If container has not been initialized
    """
    global _container
    if _container is None:
        raise RuntimeError(
            "Container not initialized. Call setup_container() first."
        )
    return _container


def setup_container(config: Optional[Any] = None) -> Container:
    """
    Initialize the global container with configuration.
    
    Args:
        config: Optional configuration object
        
    Returns:
        The initialized Container instance
    """
    global _container
    _container = Container(config=config)
    return _container


def reset_container() -> None:
    """Reset the global container - useful for testing."""
    global _container
    if _container:
        _container.reset_dependencies()
    _container = None


# Context manager for container lifecycle
class ContainerContext:
    """Context manager for proper container lifecycle management."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.container: Optional[Container] = None
    
    async def __aenter__(self) -> Container:
        """Enter the context and initialize the container."""
        self.container = setup_container(self.config)
        await self.container.initialize()
        return self.container
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and clean up the container."""
        if self.container:
            await self.container.shutdown()
        reset_container()
