"""
Async main entry point for high-performance LineupTracker.

Provides async/await execution with proper resource management,
concurrent operations, and graceful shutdown handling.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Optional, Dict
from datetime import datetime

from .config import load_config
from .container import Container
from .services.async_lineup_monitoring_service import AsyncLineupMonitoringService
from .services.dashboard_export_service import DashboardExportService
from .providers.async_sofascore_client import AsyncSofascoreClient
from .domain.exceptions import LineupMonitoringError, ConfigurationError
from .utils.logging import configure_logging, get_logger, CorrelationContext

logger = get_logger(__name__)


class AsyncLineupTracker:
    """
    Main async application class for LineupTracker.
    
    Manages the complete application lifecycle with proper async patterns,
    resource management, and graceful shutdown handling.
    """
    
    def __init__(self):
        self.config = None
        self.container: Optional[Container] = None
        self.monitoring_service: Optional[AsyncLineupMonitoringService] = None
        self.football_api: Optional[AsyncSofascoreClient] = None
        self._shutdown_event = asyncio.Event()
        self._startup_time: Optional[datetime] = None
    
    async def initialize(self):
        """Initialize the application with async components."""
        logger.info("🚀 Initializing LineupTracker async application")
        
        try:
            # Load configuration
            self.config = load_config()
            
            # Configure logging from config
            configure_logging(
                log_level=self.config.logging_settings.level,
                enable_console=self.config.logging_settings.enable_console,
                structured_format=self.config.logging_settings.format_type == "structured",
                log_file=self.config.logging_settings.log_file
            )
            
            logger.info(f"📋 Configuration loaded for environment: {self.config.environment}")
            logger.info(f"🔧 Debug mode: {self.config.debug_mode}")
            
            # Create dependency injection container
            self.container = Container(config=self.config)
            
            # Create async football API client
            self.football_api = AsyncSofascoreClient(self.config.api_settings)
            
            # Create async monitoring service
            self.monitoring_service = AsyncLineupMonitoringService(
                football_api=self.football_api,
                squad_repository=self.container.squad_repository,
                notification_service=self.container.notification_service,
                lineup_analyzer=self.container.lineup_analyzer,
                alert_generator=self.container.alert_generator,
                config=self.config.monitoring_settings
            )
            
            self._startup_time = datetime.now()
            logger.info("✅ LineupTracker async application initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize application: {e}")
            raise LineupMonitoringError(f"Application initialization failed: {e}")
    
    async def run(self):
        """Run the main application with graceful shutdown handling."""
        if not self.monitoring_service:
            raise LineupMonitoringError("Application not initialized. Call initialize() first.")
        
        logger.info("🎯 Starting LineupTracker async execution")
        
        try:
            # Set up signal handlers for graceful shutdown
            self._setup_signal_handlers()
            
            # Start monitoring service
            await self.monitoring_service.start_monitoring()
            
            # Wait for shutdown signal
            logger.info("⏳ Application running. Press Ctrl+C to stop.")
            await self._shutdown_event.wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Keyboard interrupt received")
        except Exception as e:
            logger.error(f"❌ Application error: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Gracefully shutdown the application."""
        logger.info("🛑 Shutting down LineupTracker async application")
        
        try:
            # Stop monitoring service
            if self.monitoring_service:
                await self.monitoring_service.stop_monitoring()
            
            # Close async resources
            if self.football_api:
                await self.football_api.close()
            
            # Container cleanup
            if self.container:
                await self.container.close()
            
            # Calculate uptime
            if self._startup_time:
                uptime = datetime.now() - self._startup_time
                logger.info(f"⏱️ Application uptime: {uptime}")
            
            logger.info("✅ LineupTracker async application shutdown complete")
            
        except Exception as e:
            logger.error(f"❌ Error during shutdown: {e}")
    
    def _setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        if sys.platform != "win32":
            # Unix/Linux signal handling
            for sig in (signal.SIGTERM, signal.SIGINT):
                signal.signal(sig, self._signal_handler)
        else:
            # Windows signal handling
            signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"📶 Received signal {signum}, initiating graceful shutdown")
        
        # Set shutdown event in async context
        loop = asyncio.get_running_loop()
        loop.call_soon_threadsafe(self._shutdown_event.set)
    
    async def get_status(self) -> dict:
        """Get current application status."""
        status = {
            'startup_time': self._startup_time.isoformat() if self._startup_time else None,
            'uptime_seconds': (
                (datetime.now() - self._startup_time).total_seconds()
                if self._startup_time else 0
            ),
            'config_environment': self.config.environment if self.config else None,
            'monitoring_service': None,
            'football_api': None
        }
        
        # Get monitoring service status
        if self.monitoring_service:
            try:
                status['monitoring_service'] = await self.monitoring_service.get_monitoring_status()
            except Exception as e:
                logger.warning(f"Could not get monitoring status: {e}")
                status['monitoring_service'] = {'error': str(e)}
        
        # Get API status
        if self.football_api:
            try:
                status['football_api'] = await self.football_api.get_performance_stats()
            except Exception as e:
                logger.warning(f"Could not get API status: {e}")
                status['football_api'] = {'error': str(e)}
        
        return status
    
    async def export_dashboard_data(self, export_directory: str = "dashboard/public/data") -> Dict[str, str]:
        """Export current data for dashboard consumption."""
        if not self.container:
            raise LineupMonitoringError("Application not initialized. Call initialize() first.")
        
        logger.info(f"🗂️  Starting dashboard data export to {export_directory}")
        
        try:
            # Create dashboard export service
            export_service = DashboardExportService(
                export_directory=export_directory,
                football_api=self.football_api,
                squad_repository=self.container.squad_repository,
                lineup_analyzer=self.container.lineup_analyzer,
                alert_generator=self.container.alert_generator
            )
            
            # Get current monitoring status
            monitoring_status = None
            if self.monitoring_service:
                try:
                    monitoring_status = await self.monitoring_service.get_monitoring_status()
                except Exception as e:
                    logger.warning(f"Could not get monitoring status for export: {e}")
            
            # Export all data
            exported_files = await export_service.export_all_data(monitoring_status)
            
            logger.info(f"✅ Dashboard export completed successfully")
            logger.info(f"   📁 Export directory: {export_service.get_export_directory()}")
            logger.info(f"   📄 Files exported: {', '.join(exported_files.keys())}")
            
            return exported_files
            
        except Exception as e:
            logger.error(f"❌ Dashboard export failed: {e}")
            raise LineupMonitoringError(f"Dashboard export failed: {e}")


@asynccontextmanager
async def create_app():
    """Async context manager for creating and managing the application."""
    app = AsyncLineupTracker()
    
    try:
        await app.initialize()
        yield app
    finally:
        await app.shutdown()


async def run_async_monitoring():
    """Run the async monitoring service."""
    try:
        async with create_app() as app:
            await app.run()
            
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        return 1
    except LineupMonitoringError as e:
        logger.error(f"❌ Monitoring error: {e}")
        return 1
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return 1
    
    return 0


async def run_status_check():
    """Run a quick status check and exit."""
    try:
        async with create_app() as app:
            status = await app.get_status()
            
            print("📊 LineupTracker Status:")
            print(f"   Environment: {status.get('config_environment', 'Unknown')}")
            print(f"   Uptime: {status.get('uptime_seconds', 0):.1f}s")
            
            if status.get('monitoring_service'):
                ms = status['monitoring_service']
                print(f"   Monitoring: {'✅ Running' if ms.get('is_running') else '❌ Stopped'}")
                print(f"   Monitored matches: {ms.get('monitored_matches', 0)}")
                print(f"   Total checks: {ms.get('total_checks', 0)}")
                print(f"   Success rate: {ms.get('success_rate', 0):.1f}%")
            
            if status.get('football_api'):
                api = status['football_api']
                print(f"   API requests: {api.get('total_requests', 0)}")
                print(f"   API errors: {api.get('total_errors', 0)}")
                print(f"   Cache hit rate: {api.get('cache_stats', {}).get('hit_rate', 0):.1f}%")
            
            return 0
            
    except Exception as e:
        logger.error(f"❌ Status check failed: {e}")
        print(f"❌ Status check failed: {e}")
        return 1


async def run_test_connection():
    """Test API connection and exit."""
    try:
        async with create_app() as app:
            if app.football_api:
                logger.info("🔍 Testing API connection...")
                
                connection_ok = await app.football_api.test_connection()
                
                if connection_ok:
                    print("✅ API connection test successful")
                    return 0
                else:
                    print("❌ API connection test failed")
                    return 1
            else:
                print("❌ No API client available")
                return 1
                
    except Exception as e:
        logger.error(f"❌ Connection test failed: {e}")
        print(f"❌ Connection test failed: {e}")
        return 1


async def run_dashboard_export(export_directory: str = "dashboard/public/data"):
    """Export dashboard data and exit."""
    try:
        async with create_app() as app:
            logger.info("🗂️  Exporting dashboard data...")
            
            exported_files = await app.export_dashboard_data(export_directory)
            
            print("✅ Dashboard export completed successfully!")
            print(f"📁 Export directory: {export_directory}")
            print("📄 Files exported:")
            for data_type, file_path in exported_files.items():
                print(f"   - {data_type}: {file_path}")
            
            return 0
            
    except Exception as e:
        logger.error(f"❌ Dashboard export failed: {e}")
        print(f"❌ Dashboard export failed: {e}")
        return 1


def main():
    """Main entry point for async LineupTracker."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="LineupTracker - Async Football Lineup Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'command',
        choices=['run', 'status', 'test', 'export'],
        help='Command to execute'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    parser.add_argument(
        '--export-dir',
        default='dashboard/public/data',
        help='Directory to export dashboard data (default: dashboard/public/data)'
    )
    
    args = parser.parse_args()
    
    # Set up basic logging
    log_level = "DEBUG" if args.debug else "INFO"
    configure_logging(log_level=log_level, enable_console=True)
    
    # Run appropriate command
    try:
        with CorrelationContext():
            if args.command == 'run':
                exit_code = asyncio.run(run_async_monitoring())
            elif args.command == 'status':
                exit_code = asyncio.run(run_status_check())
            elif args.command == 'test':
                exit_code = asyncio.run(run_test_connection())
            elif args.command == 'export':
                exit_code = asyncio.run(run_dashboard_export(args.export_dir))
            else:
                print(f"Unknown command: {args.command}")
                exit_code = 1
        
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
