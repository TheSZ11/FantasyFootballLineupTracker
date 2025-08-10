"""
Unit tests for the dependency injection container.

Tests the container's ability to create and manage dependencies correctly.
"""

import pytest

from src.lineup_tracker.container import Container, setup_container, reset_container
from src.lineup_tracker.domain.interfaces import FootballDataProvider, SquadRepository


class TestContainer:
    """Test the dependency injection container."""
    
    def setup_method(self):
        """Set up for each test."""
        reset_container()
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_container()
    
    def test_create_container(self):
        """Test creating a container."""
        container = Container()
        assert container is not None
        assert container.config is not None
    
    def test_container_with_config(self):
        """Test creating container with custom config."""
        config = {'test': 'value'}
        container = Container(config=config)
        assert container.config == config
    
    def test_lazy_dependency_creation(self):
        """Test that dependencies are created lazily."""
        container = Container()
        
        # Dependencies should not be created initially
        assert len(container._instances) == 0
        
        # Accessing a dependency should create it
        football_api = container.football_api
        assert football_api is not None
        assert 'football_api' in container._instances
        
        # Second access should return same instance
        football_api2 = container.football_api
        assert football_api is football_api2
    
    def test_all_dependencies_accessible(self):
        """Test that all dependencies can be accessed."""
        container = Container()
        
        # Test all dependencies can be created
        assert container.football_api is not None
        assert container.squad_repository is not None
        assert container.notification_service is not None
        assert container.cache_provider is not None
        assert container.health_checker is not None
        assert container.metrics_collector is not None
    
    def test_dependency_override(self):
        """Test overriding dependencies for testing."""
        container = Container()
        
        # Create mock dependency
        class MockFootballAPI:
            pass
        
        mock_api = MockFootballAPI()
        
        # Override dependency
        container.override_dependency('football_api', mock_api)
        
        # Should return mock instance
        assert container.football_api is mock_api
    
    def test_dependency_status(self):
        """Test getting dependency initialization status."""
        container = Container()
        
        # Initially no dependencies created
        status = container.get_dependency_status()
        assert all(not initialized for initialized in status.values())
        
        # Access one dependency
        _ = container.football_api
        
        # Check status updated
        status = container.get_dependency_status()
        assert status['football_api'] is True
        assert status['squad_repository'] is False
    
    def test_reset_dependencies(self):
        """Test resetting dependencies."""
        container = Container()
        
        # Create some dependencies
        _ = container.football_api
        _ = container.squad_repository
        
        assert len(container._instances) == 2
        
        # Reset
        container.reset_dependencies()
        
        assert len(container._instances) == 0
    
    def test_global_container_functions(self):
        """Test global container management functions."""
        # Initially no container
        with pytest.raises(RuntimeError):
            from src.lineup_tracker.container import get_container
            get_container()
        
        # Set up container
        container = setup_container()
        assert container is not None
        
        # Should be able to get it
        from src.lineup_tracker.container import get_container
        retrieved = get_container()
        assert retrieved is container
        
        # Reset
        reset_container()
        
        # Should raise error again
        with pytest.raises(RuntimeError):
            get_container()


@pytest.mark.asyncio
class TestContainerAsync:
    """Test async functionality of container."""
    
    def setup_method(self):
        """Set up for each test."""
        reset_container()
    
    def teardown_method(self):
        """Clean up after each test."""
        reset_container()
    
    async def test_container_lifecycle(self):
        """Test container initialization and shutdown."""
        container = Container()
        
        # Initialize
        await container.initialize()
        
        # Should still work
        api = container.football_api
        assert api is not None
        
        # Shutdown
        await container.shutdown()
        
        # Instances should be cleared
        assert len(container._instances) == 0
    
    async def test_container_context_manager(self):
        """Test container context manager."""
        from src.lineup_tracker.container import ContainerContext
        
        async with ContainerContext() as container:
            assert container is not None
            api = container.football_api
            assert api is not None
        
        # Container should be reset after context
        with pytest.raises(RuntimeError):
            from src.lineup_tracker.container import get_container
            get_container()
