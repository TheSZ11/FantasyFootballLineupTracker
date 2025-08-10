"""
Lineup analysis business logic.

Contains the core business rules for analyzing lineup discrepancies
between expected fantasy team lineups and actual match lineups.
"""

from typing import List, Dict, Set
from datetime import datetime
import logging

from ..domain.models import Match, Lineup, Squad, Player, LineupDiscrepancy
from ..domain.enums import PlayerStatus, AlertType

logger = logging.getLogger(__name__)


class LineupAnalyzer:
    """
    Analyzes lineup discrepancies between expected and actual team lineups.
    
    This class implements the core business logic for detecting when
    fantasy football expectations don't match reality.
    """
    
    def __init__(self):
        self._last_analysis_time: Dict[str, datetime] = {}
    
    def analyze_match_lineups(self, match: Match, lineups: List[Lineup], squad: Squad) -> List[LineupDiscrepancy]:
        """
        Analyze lineups for a match against squad expectations.
        
        Args:
            match: The match being analyzed
            lineups: List of team lineups (typically home and away)
            squad: Fantasy squad with player expectations
            
        Returns:
            List of lineup discrepancies found
        """
        logger.info(f"Analyzing lineup for match {match.id}: {match.home_team.name} vs {match.away_team.name}")
        
        discrepancies = []
        
        # Get players from teams in this match
        relevant_players = self._get_players_for_match(match, squad)
        
        if not relevant_players:
            logger.debug(f"No squad players involved in match {match.id}")
            return []
        
        logger.info(f"Found {len(relevant_players)} squad players in match")
        
        # Create lookup for actual starting players by team
        starting_players_by_team = self._build_starting_players_lookup(lineups)
        
        # Analyze each relevant player
        for player in relevant_players:
            discrepancy = self._analyze_player_lineup_status(
                player, match, starting_players_by_team
            )
            if discrepancy:
                discrepancies.append(discrepancy)
        
        # Record analysis time
        self._last_analysis_time[match.id] = datetime.now()
        
        logger.info(f"Analysis complete: {len(discrepancies)} discrepancies found")
        return discrepancies
    
    def _get_players_for_match(self, match: Match, squad: Squad) -> List[Player]:
        """Get squad players from teams playing in this match."""
        team_names = {match.home_team.name, match.away_team.name}
        
        relevant_players = [
            player for player in squad.players
            if player.team.name in team_names
        ]
        
        logger.debug(f"Match teams: {team_names}")
        logger.debug(f"Relevant players: {[p.name for p in relevant_players]}")
        
        return relevant_players
    
    def _build_starting_players_lookup(self, lineups: List[Lineup]) -> Dict[str, Set[str]]:
        """Build a lookup of starting players by team name."""
        starting_players = {}
        
        for lineup in lineups:
            team_name = lineup.team.name
            starting_players[team_name] = set(lineup.starting_eleven)
            logger.debug(f"{team_name} starting XI: {lineup.starting_eleven}")
        
        return starting_players
    
    def _analyze_player_lineup_status(
        self, 
        player: Player, 
        match: Match, 
        starting_players_by_team: Dict[str, Set[str]]
    ) -> LineupDiscrepancy:
        """
        Analyze a single player's lineup status.
        
        Args:
            player: The player to analyze
            match: The match context
            starting_players_by_team: Lookup of actual starting players
            
        Returns:
            LineupDiscrepancy if there's a discrepancy, None otherwise
        """
        team_starters = starting_players_by_team.get(player.team.name, set())
        
        expected_starting = player.status == PlayerStatus.ACTIVE
        actually_starting = player.name in team_starters
        
        # Log the analysis
        logger.debug(
            f"Player: {player.name} ({player.team.name}) - "
            f"Expected: {'Starting' if expected_starting else 'Bench'}, "
            f"Actually: {'Starting' if actually_starting else 'Not Starting'}"
        )
        
        # Always create a discrepancy record for tracking
        return LineupDiscrepancy(
            player=player,
            match=match,
            expected_starting=expected_starting,
            actually_starting=actually_starting
        )
    
    def get_last_analysis_time(self, match_id: str) -> datetime:
        """Get the last time this match was analyzed."""
        return self._last_analysis_time.get(match_id)
    
    def should_analyze_match(self, match: Match, min_interval_minutes: int = 5) -> bool:
        """
        Check if enough time has passed since last analysis.
        
        Args:
            match: Match to check
            min_interval_minutes: Minimum minutes between analyses
            
        Returns:
            True if match should be analyzed again
        """
        last_analysis = self.get_last_analysis_time(match.id)
        
        if last_analysis is None:
            return True
        
        time_since_last = (datetime.now() - last_analysis).total_seconds() / 60
        return time_since_last >= min_interval_minutes
    
    def get_analysis_summary(self, discrepancies: List[LineupDiscrepancy]) -> Dict[str, int]:
        """
        Get a summary of analysis results.
        
        Args:
            discrepancies: List of discrepancies to summarize
            
        Returns:
            Dictionary with summary statistics
        """
        summary = {
            'total_players_analyzed': len(discrepancies),
            'unexpected_benchings': 0,
            'unexpected_startings': 0,
            'confirmed_expectations': 0
        }
        
        for discrepancy in discrepancies:
            if discrepancy.discrepancy_type == AlertType.UNEXPECTED_BENCHING:
                summary['unexpected_benchings'] += 1
            elif discrepancy.discrepancy_type == AlertType.UNEXPECTED_STARTING:
                summary['unexpected_startings'] += 1
            else:
                summary['confirmed_expectations'] += 1
        
        return summary
