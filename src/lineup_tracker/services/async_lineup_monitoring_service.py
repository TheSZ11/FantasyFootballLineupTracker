"""
Async lineup monitoring service with concurrent operations and performance optimizations.

Provides high-performance lineup monitoring with async/await patterns,
concurrent API calls, intelligent scheduling, and real-time notifications.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Set, Any
from dataclasses import dataclass

from ..domain.models import Match, Lineup, Squad, Alert, AlertType, AlertUrgency, MatchStatus
from ..domain.interfaces import (
    FootballDataProvider, NotificationProvider, SquadRepository, 
    LineupAnalyzer, AlertGenerator
)
from ..domain.exceptions import LineupMonitoringError, DataNotAvailableError
from ..utils.cache import cached_async
from ..utils.retry import graceful_degradation
from ..utils.logging import get_logger, log_performance, CorrelationContext
from ..config.app_config import MonitoringConfig

logger = get_logger(__name__)


@dataclass
class MonitoringState:
    """Current state of the monitoring system."""
    is_running: bool = False
    last_check_time: Optional[datetime] = None
    monitored_matches: Set[str] = None
    total_checks: int = 0
    successful_checks: int = 0
    errors_count: int = 0
    
    def __post_init__(self):
        if self.monitored_matches is None:
            self.monitored_matches = set()


@dataclass
class MatchMonitoringInfo:
    """Information about a match being monitored."""
    match: Match
    squad_players: Set[str]
    last_lineup_check: Optional[datetime] = None
    lineup_found: bool = False
    alerts_sent: int = 0
    priority: int = 1  # 1=highest, 5=lowest


class AsyncLineupMonitoringService:
    """
    High-performance async lineup monitoring service.
    
    Features:
    - Concurrent lineup fetching for multiple matches
    - Intelligent scheduling based on match proximity
    - Real-time notifications with priority handling
    - Performance monitoring and metrics
    - Graceful error handling and recovery
    - Configurable monitoring intervals
    """
    
    def __init__(
        self,
        football_api: FootballDataProvider,
        squad_repository: SquadRepository,
        notification_service: Any,  # NotificationService
        lineup_analyzer: LineupAnalyzer,
        alert_generator: AlertGenerator,
        config: MonitoringConfig
    ):
        self.football_api = football_api
        self.squad_repository = squad_repository
        self.notification_service = notification_service
        self.lineup_analyzer = lineup_analyzer
        self.alert_generator = alert_generator
        self.config = config
        
        # Monitoring state
        self.state = MonitoringState()
        self.monitored_matches: Dict[str, MatchMonitoringInfo] = {}
        self.monitoring_task: Optional[asyncio.Task] = None
        self.squad: Optional[Squad] = None
        
        # Performance tracking
        self._start_time: Optional[datetime] = None
        self._cycles_today = 0
        self._last_daily_reset = datetime.now().date()
    
    async def start_monitoring(self):
        """Start the async monitoring process."""
        if self.state.is_running:
            logger.warning("Monitoring is already running")
            return
        
        logger.info("🚀 Starting async lineup monitoring service")
        
        try:
            # Load squad data
            await self._load_squad()
            
            # Set up initial state
            self.state.is_running = True
            self._start_time = datetime.now()
            
            # Send startup notification
            await self._send_startup_notification()
            
            # Start the main monitoring loop
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            
            logger.info("✅ Async lineup monitoring service started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring service: {e}")
            self.state.is_running = False
            raise LineupMonitoringError(f"Failed to start monitoring: {e}")
    
    async def stop_monitoring(self):
        """Stop the monitoring process gracefully."""
        if not self.state.is_running:
            logger.warning("Monitoring is not running")
            return
        
        logger.info("🛑 Stopping async lineup monitoring service")
        
        self.state.is_running = False
        
        # Cancel monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        # Send shutdown notification
        await self._send_shutdown_notification()
        
        # Clean up resources
        if hasattr(self.football_api, 'close'):
            await self.football_api.close()
        
        logger.info("✅ Async lineup monitoring service stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop with intelligent scheduling."""
        logger.info("📊 Starting main monitoring loop")
        
        while self.state.is_running:
            try:
                # Check daily cycle limit
                await self._check_daily_limits()
                
                # Get upcoming matches
                matches = await self._get_relevant_matches()
                
                if not matches:
                    logger.debug("No relevant matches found, waiting...")
                    await asyncio.sleep(60)  # Wait 1 minute before next check
                    continue
                
                # Update monitored matches
                await self._update_monitored_matches(matches)
                
                # Perform concurrent lineup checks
                await self._perform_concurrent_lineup_checks()
                
                # Update monitoring state
                self.state.last_check_time = datetime.now()
                self.state.total_checks += 1
                self._cycles_today += 1
                
                # Calculate next check interval
                sleep_duration = self._calculate_next_check_interval()
                
                logger.debug(f"💤 Sleeping for {sleep_duration} seconds until next check")
                await asyncio.sleep(sleep_duration)
                
            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                self.state.errors_count += 1
                
                # Exponential backoff on errors
                error_sleep = min(300, 30 * (self.state.errors_count ** 2))
                logger.info(f"Sleeping {error_sleep}s due to error")
                await asyncio.sleep(error_sleep)
    
    @cached_async(ttl=300)  # Cache for 5 minutes
    async def _get_relevant_matches(self) -> List[Match]:
        """Get matches that are relevant for monitoring."""
        try:
            with CorrelationContext.create():
                logger.debug("🔍 Fetching relevant matches")
                
                # Get upcoming fixtures
                fixtures = await self.football_api.get_fixtures()
                
                # Filter for relevant matches (within monitoring window)
                now = datetime.now()
                monitoring_window = timedelta(minutes=self.config.pre_match_window_minutes)
                
                relevant_matches = []
                for match in fixtures:
                    time_until_match = match.start_time - now
                    
                    # Include matches starting within our monitoring window
                    if timedelta(0) <= time_until_match <= monitoring_window:
                        relevant_matches.append(match)
                    
                    # Include live matches
                    elif match.status == MatchStatus.LIVE:
                        relevant_matches.append(match)
                
                logger.info(f"📅 Found {len(relevant_matches)} relevant matches")
                return relevant_matches
                
        except Exception as e:
            logger.error(f"Error getting relevant matches: {e}")
            raise DataNotAvailableError(f"Failed to get matches: {e}")
    
    async def _update_monitored_matches(self, matches: List[Match]):
        """Update the set of monitored matches."""
        if not self.squad:
            logger.warning("No squad loaded, cannot update monitored matches")
            return
        
        squad_player_names = {player.name for player in self.squad.players}
        
        for match in matches:
            if match.id not in self.monitored_matches:
                # Determine if this match involves our players
                # (This is a simplified check - in reality you'd need team mapping)
                monitor_info = MatchMonitoringInfo(
                    match=match,
                    squad_players=squad_player_names,
                    priority=self._calculate_match_priority(match)
                )
                
                self.monitored_matches[match.id] = monitor_info
                logger.info(f"🎯 Now monitoring match: {match.home_team.name} vs {match.away_team.name}")
        
        # Remove old matches
        current_match_ids = {match.id for match in matches}
        old_match_ids = set(self.monitored_matches.keys()) - current_match_ids
        
        for match_id in old_match_ids:
            del self.monitored_matches[match_id]
            logger.debug(f"🗑️ Removed old match from monitoring: {match_id}")
    
    @log_performance
    async def _perform_concurrent_lineup_checks(self):
        """Perform lineup checks for all monitored matches concurrently."""
        if not self.monitored_matches:
            logger.debug("No matches to check")
            return
        
        logger.info(f"🔄 Checking lineups for {len(self.monitored_matches)} matches")
        
        # Sort matches by priority
        sorted_matches = sorted(
            self.monitored_matches.values(),
            key=lambda x: (x.priority, x.match.start_time)
        )
        
        # Create concurrent tasks
        tasks = []
        for monitor_info in sorted_matches:
            if self._should_check_lineup(monitor_info):
                task = asyncio.create_task(
                    self._check_single_match_lineup(monitor_info)
                )
                tasks.append(task)
        
        if not tasks:
            logger.debug("No lineup checks needed at this time")
            return
        
        # Execute concurrently
        logger.info(f"🚄 Running {len(tasks)} concurrent lineup checks")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_checks = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Lineup check failed: {result}")
            else:
                successful_checks += 1
        
        self.state.successful_checks += successful_checks
        logger.info(f"✅ Completed {successful_checks}/{len(tasks)} lineup checks successfully")
    
    async def _check_single_match_lineup(self, monitor_info: MatchMonitoringInfo):
        """Check lineup for a single match and generate alerts if needed."""
        match = monitor_info.match
        
        try:
            with CorrelationContext.create(match_id=match.id):
                logger.debug(f"🔍 Checking lineup for {match.home_team.name} vs {match.away_team.name}")
                
                # Get lineup from API
                lineup = await self.football_api.get_lineup(match.id)
                
                # Update monitoring info
                monitor_info.last_lineup_check = datetime.now()
                
                if lineup:
                    monitor_info.lineup_found = True
                    logger.info(f"📋 Lineup found for match {match.id}")
                    
                    # Analyze lineup against our squad
                    await self._analyze_and_alert(match, lineup, monitor_info)
                else:
                    logger.debug(f"📋 No lineup yet available for match {match.id}")
                    
        except Exception as e:
            logger.error(f"Error checking lineup for match {match.id}: {e}")
            raise
    
    async def _analyze_and_alert(self, match: Match, lineup: Lineup, monitor_info: MatchMonitoringInfo):
        """Analyze lineup and send alerts if needed."""
        try:
            # Analyze lineup for discrepancies
            discrepancies = self.lineup_analyzer.analyze_match_lineups(
                match, [lineup], self.squad
            )
            
            if discrepancies:
                logger.warning(f"⚠️ Found {len(discrepancies)} lineup discrepancies")
                
                # Generate alerts
                alerts = self.alert_generator.generate_alerts(discrepancies, match)
                
                if alerts:
                    # Send notifications concurrently
                    await self._send_alerts_concurrently(alerts)
                    monitor_info.alerts_sent += len(alerts)
                    
                    logger.info(f"📨 Sent {len(alerts)} alerts for match {match.id}")
            else:
                logger.info(f"✅ No lineup issues found for match {match.id}")
                
        except Exception as e:
            logger.error(f"Error analyzing lineup for match {match.id}: {e}")
            raise
    
    async def _send_alerts_concurrently(self, alerts: List[Alert]):
        """Send multiple alerts concurrently."""
        if not alerts:
            return
        
        # Group alerts by urgency
        urgent_alerts = [alert for alert in alerts if alert.urgency == AlertUrgency.HIGH]
        normal_alerts = [alert for alert in alerts if alert.urgency != AlertUrgency.HIGH]
        
        # Send urgent alerts first
        if urgent_alerts:
            await asyncio.gather(*[
                self.notification_service.send_alert(alert)
                for alert in urgent_alerts
            ], return_exceptions=True)
        
        # Then send normal alerts
        if normal_alerts:
            await asyncio.gather(*[
                self.notification_service.send_alert(alert)
                for alert in normal_alerts
            ], return_exceptions=True)
    
    def _should_check_lineup(self, monitor_info: MatchMonitoringInfo) -> bool:
        """Determine if we should check lineup for this match."""
        now = datetime.now()
        match = monitor_info.match
        
        # Always check if no lineup found yet
        if not monitor_info.lineup_found:
            return True
        
        # Check based on match timing
        time_until_match = match.start_time - now
        
        # More frequent checks closer to match time
        if time_until_match <= timedelta(minutes=self.config.final_sprint_minutes):
            # Final sprint mode - check every minute
            min_interval = timedelta(minutes=self.config.final_sprint_interval_minutes)
        else:
            # Normal mode - check based on configuration
            min_interval = timedelta(minutes=self.config.min_analysis_interval_minutes)
        
        # Check if enough time has passed since last check
        if monitor_info.last_lineup_check:
            time_since_last_check = now - monitor_info.last_lineup_check
            return time_since_last_check >= min_interval
        
        return True
    
    def _calculate_match_priority(self, match: Match) -> int:
        """Calculate priority for match monitoring (1=highest, 5=lowest)."""
        now = datetime.now()
        time_until_match = match.start_time - now
        
        # Higher priority for matches starting soon
        if time_until_match <= timedelta(minutes=15):
            return 1  # Highest priority
        elif time_until_match <= timedelta(hours=1):
            return 2
        elif time_until_match <= timedelta(hours=6):
            return 3
        elif time_until_match <= timedelta(hours=24):
            return 4
        else:
            return 5  # Lowest priority
    
    def _calculate_next_check_interval(self) -> int:
        """Calculate intelligent sleep interval based on upcoming matches."""
        if not self.monitored_matches:
            return self.config.check_interval_minutes * 60
        
        now = datetime.now()
        min_time_until_match = min(
            (info.match.start_time - now).total_seconds()
            for info in self.monitored_matches.values()
            if info.match.start_time > now
        )
        
        # Adaptive interval based on proximity to matches
        if min_time_until_match <= self.config.final_sprint_minutes * 60:
            # Final sprint mode
            return self.config.final_sprint_interval_minutes * 60
        elif min_time_until_match <= 3600:  # 1 hour
            # Frequent checks
            return max(60, self.config.check_interval_minutes * 60 // 4)
        else:
            # Normal interval
            return self.config.check_interval_minutes * 60
    
    async def _load_squad(self):
        """Load squad data from repository."""
        try:
            logger.info("📚 Loading squad data")
            self.squad = await self.squad_repository.load_squad(self.config.squad_file_path)
            
            if not self.squad or not self.squad.players:
                raise LineupMonitoringError("No squad data found or squad is empty")
            
            logger.info(f"✅ Loaded squad with {len(self.squad.players)} players")
            
        except Exception as e:
            logger.error(f"Failed to load squad: {e}")
            raise LineupMonitoringError(f"Failed to load squad: {e}")
    
    async def _check_daily_limits(self):
        """Check and enforce daily monitoring limits."""
        today = datetime.now().date()
        
        # Reset daily counter if new day
        if today > self._last_daily_reset:
            self._cycles_today = 0
            self._last_daily_reset = today
            logger.info("🌅 Daily monitoring cycle counter reset")
        
        # Check limits
        if self._cycles_today >= self.config.max_monitoring_cycles_per_day:
            logger.warning(f"⚠️ Daily monitoring limit reached ({self.config.max_monitoring_cycles_per_day})")
            await asyncio.sleep(3600)  # Sleep for 1 hour
    
    @graceful_degradation(fallback_value=None)
    async def _send_startup_notification(self):
        """Send startup notification."""
        try:
            startup_msg = (
                f"🚀 LineupTracker monitoring started\n"
                f"⏰ Check interval: {self.config.check_interval_minutes} minutes\n"
                f"👥 Squad size: {len(self.squad.players) if self.squad else 0} players\n"
                f"🎯 Ready to monitor lineups!"
            )
            
            await self.notification_service.send_message(startup_msg)
            logger.info("📨 Startup notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send startup notification: {e}")
    
    @graceful_degradation(fallback_value=None)
    async def _send_shutdown_notification(self):
        """Send shutdown notification."""
        try:
            uptime = datetime.now() - self._start_time if self._start_time else timedelta(0)
            
            shutdown_msg = (
                f"🛑 LineupTracker monitoring stopped\n"
                f"⏱️ Uptime: {uptime}\n"
                f"📊 Total checks: {self.state.total_checks}\n"
                f"✅ Successful: {self.state.successful_checks}\n"
                f"❌ Errors: {self.state.errors_count}"
            )
            
            await self.notification_service.send_message(shutdown_msg)
            logger.info("📨 Shutdown notification sent")
            
        except Exception as e:
            logger.error(f"Failed to send shutdown notification: {e}")
    
    async def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        uptime = datetime.now() - self._start_time if self._start_time else timedelta(0)
        
        # Get performance stats from football API if available
        api_stats = {}
        if hasattr(self.football_api, 'get_performance_stats'):
            try:
                api_stats = await self.football_api.get_performance_stats()
            except Exception as e:
                logger.warning(f"Could not get API stats: {e}")
        
        return {
            'is_running': self.state.is_running,
            'uptime_seconds': uptime.total_seconds(),
            'last_check_time': self.state.last_check_time.isoformat() if self.state.last_check_time else None,
            'monitored_matches': len(self.monitored_matches),
            'total_checks': self.state.total_checks,
            'successful_checks': self.state.successful_checks,
            'error_count': self.state.errors_count,
            'success_rate': (
                self.state.successful_checks / self.state.total_checks * 100
                if self.state.total_checks > 0 else 0
            ),
            'cycles_today': self._cycles_today,
            'max_cycles_per_day': self.config.max_monitoring_cycles_per_day,
            'squad_size': len(self.squad.players) if self.squad else 0,
            'api_performance': api_stats
        }
