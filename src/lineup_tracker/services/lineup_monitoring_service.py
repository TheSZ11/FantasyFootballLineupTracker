"""
Core lineup monitoring service.

Orchestrates the entire lineup monitoring workflow, from loading squad data
to analyzing lineups and sending notifications.
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from ..domain.interfaces import FootballDataProvider, SquadRepository
from ..domain.models import Match, Squad, Lineup, Alert
from ..domain.enums import MatchStatus
from ..domain.exceptions import LineupMonitorError, SquadLoadError, APIConnectionError
from ..business.lineup_analyzer import LineupAnalyzer
from ..business.alert_generator import AlertGenerator

logger = logging.getLogger(__name__)


class LineupMonitoringService:
    """
    Main service for monitoring lineup changes and generating alerts.
    
    This service coordinates all the components needed for lineup monitoring:
    - Loading squad data
    - Fetching fixture data
    - Getting lineup information
    - Analyzing discrepancies
    - Generating alerts
    """
    
    def __init__(
        self,
        football_api: FootballDataProvider,
        squad_repository: SquadRepository,
        notification_service: 'NotificationService',  # Forward reference
        lineup_analyzer: LineupAnalyzer,
        alert_generator: AlertGenerator
    ):
        self.football_api = football_api
        self.squad_repository = squad_repository
        self.notification_service = notification_service
        self.lineup_analyzer = lineup_analyzer
        self.alert_generator = alert_generator
        
        # State tracking
        self._last_squad_load: Optional[datetime] = None
        self._cached_squad: Optional[Squad] = None
        self._monitoring_stats = {
            'cycles_run': 0,
            'matches_checked': 0,
            'alerts_generated': 0,
            'last_run': None
        }
    
    async def run_monitoring_cycle(self) -> Dict[str, any]:
        """
        Execute one complete monitoring cycle.
        
        Returns:
            Dictionary with cycle results and statistics
        """
        cycle_start = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting lineup monitoring cycle")
        
        try:
            # Load current squad
            squad = await self._load_current_squad()
            
            # Get relevant matches
            matches = await self._get_relevant_matches(squad)
            
            if not matches:
                logger.info("No relevant matches found for monitoring")
                return self._create_cycle_result(cycle_start, 0, 0, "No matches")
            
            logger.info(f"Found {len(matches)} relevant matches to monitor")
            
            # Process each match
            total_alerts = 0
            matches_processed = 0
            
            for match in matches:
                try:
                    alerts_for_match = await self._process_match(match, squad)
                    total_alerts += len(alerts_for_match)
                    matches_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing match {match.id}: {e}")
                    continue
            
            # Update statistics
            self._monitoring_stats['cycles_run'] += 1
            self._monitoring_stats['matches_checked'] += matches_processed
            self._monitoring_stats['alerts_generated'] += total_alerts
            self._monitoring_stats['last_run'] = cycle_start
            
            cycle_result = self._create_cycle_result(
                cycle_start, matches_processed, total_alerts, "Success"
            )
            
            logger.info(f"Monitoring cycle completed: {matches_processed} matches, {total_alerts} alerts")
            return cycle_result
            
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            
            # Send error notification
            await self._send_error_notification(str(e))
            
            return self._create_cycle_result(cycle_start, 0, 0, f"Error: {str(e)}")
        
        finally:
            logger.info("=" * 50)
    
    async def _load_current_squad(self) -> Squad:
        """Load the current squad, using cache if recent."""
        now = datetime.now()
        
        # Use cached squad if loaded recently (within 10 minutes)
        if (self._cached_squad and 
            self._last_squad_load and 
            (now - self._last_squad_load).total_seconds() < 600):
            logger.debug("Using cached squad data")
            return self._cached_squad
        
        try:
            logger.info(f"Loading squad from {self.squad_file_path}")
            squad = self.squad_repository.load_squad(self.squad_file_path)
            
            # Cache the loaded squad
            self._cached_squad = squad
            self._last_squad_load = now
            
            logger.info(f"Squad loaded: {squad.total_count} players "
                       f"({squad.active_count} active, {squad.reserve_count} reserve)")
            
            return squad
            
        except SquadLoadError as e:
            logger.error(f"Failed to load squad: {e}")
            raise LineupMonitorError(f"Cannot load squad: {e}")
    
    async def _get_relevant_matches(self, squad: Squad) -> List[Match]:
        """Get matches involving squad players."""
        try:
            # Get today's fixtures
            all_fixtures = await self.football_api.get_fixtures()
            
            if not all_fixtures:
                logger.info("No fixtures found for today")
                return []
            
            # Filter for matches involving squad teams
            squad_teams = set(squad.get_teams())
            relevant_matches = []
            
            for match in all_fixtures:
                if (match.home_team.name in squad_teams or 
                    match.away_team.name in squad_teams):
                    
                    # Only monitor matches that haven't started yet or are live
                    if match.status in [MatchStatus.NOT_STARTED, MatchStatus.LIVE, MatchStatus.TO_BE_DETERMINED]:
                        relevant_matches.append(match)
                        logger.debug(f"Relevant match: {match.home_team.name} vs {match.away_team.name}")
            
            return relevant_matches
            
        except APIConnectionError as e:
            logger.error(f"API connection failed: {e}")
            raise LineupMonitorError(f"Cannot fetch fixtures: {e}")
    
    async def _process_match(self, match: Match, squad: Squad) -> List[Alert]:
        """Process a single match for lineup monitoring."""
        logger.info(f"Processing match: {match.home_team.name} vs {match.away_team.name}")
        
        # Check if we should analyze this match (rate limiting)
        if not self.lineup_analyzer.should_analyze_match(match):
            logger.debug(f"Skipping match {match.id} - analyzed recently")
            return []
        
        # Skip if match already started
        if match.is_started:
            logger.debug(f"Skipping match {match.id} - already started")
            return []
        
        try:
            # Get lineups for the match
            lineups = await self._get_match_lineups(match)
            
            if not lineups:
                logger.info(f"Lineups not yet available for {match.home_team.name} vs {match.away_team.name}")
                return []
            
            # Analyze lineup discrepancies
            discrepancies = self.lineup_analyzer.analyze_match_lineups(match, lineups, squad)
            
            if not discrepancies:
                logger.debug(f"No discrepancies found for match {match.id}")
                return []
            
            # Generate alerts from discrepancies
            alerts = self.alert_generator.generate_alerts(discrepancies)
            
            # Send notifications
            await self._send_alerts(alerts)
            
            # Log analysis summary
            summary = self.lineup_analyzer.get_analysis_summary(discrepancies)
            alert_summary = self.alert_generator.get_alert_summary(alerts)
            
            logger.info(f"Match {match.id} analysis complete:")
            logger.info(f"  Players analyzed: {summary['total_players_analyzed']}")
            logger.info(f"  Unexpected benchings: {summary['unexpected_benchings']}")
            logger.info(f"  Unexpected startings: {summary['unexpected_startings']}")
            logger.info(f"  Alerts generated: {alert_summary['total_alerts']}")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error processing match {match.id}: {e}")
            raise
    
    async def _get_match_lineups(self, match: Match) -> List[Lineup]:
        """Get lineups for a match."""
        try:
            # Note: The API typically returns lineups for both teams
            # We'll need to handle this based on the actual API response format
            lineup_data = await self.football_api.get_lineup(match.id)
            
            if not lineup_data:
                return []
            
            # If lineup_data is a single Lineup object, wrap it in a list
            if hasattr(lineup_data, 'starting_eleven'):
                return [lineup_data]
            
            # If it's already a list, return as-is
            if isinstance(lineup_data, list):
                return lineup_data
            
            logger.warning(f"Unexpected lineup data format for match {match.id}")
            return []
            
        except Exception as e:
            logger.error(f"Error getting lineup for match {match.id}: {e}")
            return []
    
    async def _send_alerts(self, alerts: List[Alert]) -> None:
        """Send generated alerts via notification service."""
        if not alerts:
            return
        
        try:
            for alert in alerts:
                await self.notification_service.send_alert(alert)
            
            logger.info(f"Sent {len(alerts)} alerts successfully")
            
        except Exception as e:
            logger.error(f"Error sending alerts: {e}")
            # Don't re-raise - we don't want to fail the entire cycle for notification issues
    
    async def _send_error_notification(self, error_message: str) -> None:
        """Send error notification."""
        try:
            await self.notification_service.send_error_notification(
                f"⚠️ Lineup monitoring error: {error_message}"
            )
        except Exception as e:
            logger.error(f"Failed to send error notification: {e}")
    
    def _create_cycle_result(
        self, 
        start_time: datetime, 
        matches_processed: int, 
        alerts_generated: int, 
        status: str
    ) -> Dict[str, any]:
        """Create cycle result dictionary."""
        duration = (datetime.now() - start_time).total_seconds()
        
        return {
            'start_time': start_time.isoformat(),
            'duration_seconds': duration,
            'matches_processed': matches_processed,
            'alerts_generated': alerts_generated,
            'status': status,
            'statistics': self._monitoring_stats.copy()
        }
    
    def get_monitoring_statistics(self) -> Dict[str, any]:
        """Get monitoring statistics."""
        return self._monitoring_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset monitoring statistics."""
        self._monitoring_stats = {
            'cycles_run': 0,
            'matches_checked': 0,
            'alerts_generated': 0,
            'last_run': None
        }
    
    async def force_squad_reload(self) -> Squad:
        """Force reload of squad data."""
        self._cached_squad = None
        self._last_squad_load = None
        return await self._load_current_squad()
    
    def get_squad_summary(self) -> str:
        """Get summary of current squad for debugging."""
        if not self._cached_squad:
            return "No squad loaded"
        
        squad = self._cached_squad
        teams = {}
        
        for player in squad.players:
            team = player.team.name
            if team not in teams:
                teams[team] = {'starters': [], 'bench': []}
            
            if player.is_active:
                teams[team]['starters'].append(player.name)
            else:
                teams[team]['bench'].append(player.name)
        
        summary = f"Roster Summary ({squad.total_count} players):\n"
        for team, players in teams.items():
            summary += f"\n{team}:\n"
            summary += f"  Active ({len(players['starters'])}): {', '.join(players['starters'])}\n"
            summary += f"  Reserve ({len(players['bench'])}): {', '.join(players['bench'])}\n"
        
        return summary
