"""
Dashboard export service for static JSON data generation.

Exports current squad status, match data, and monitoring statistics to JSON files
that can be consumed by a static dashboard frontend.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from ..domain.models import Squad, Match, Alert, Player
from ..domain.enums import PlayerStatus, MatchStatus, AlertType, AlertUrgency
from ..domain.interfaces import FootballDataProvider, SquadRepository
from ..business.lineup_analyzer import LineupAnalyzer
from ..business.alert_generator import AlertGenerator
from ..utils.logging import get_logger
from ..utils.team_mappings import get_full_team_name, normalize_team_name

logger = get_logger(__name__)


class DashboardExportService:
    """
    Service for exporting lineup tracking data to JSON files for dashboard consumption.
    
    Generates static JSON files that can be read by a frontend dashboard,
    enabling deployment to static hosting platforms like GitHub Pages.
    """
    
    def __init__(
        self,
        export_directory: str = "dashboard/public/data",
        football_api: Optional[FootballDataProvider] = None,
        squad_repository: Optional[SquadRepository] = None,
        lineup_analyzer: Optional[LineupAnalyzer] = None,
        alert_generator: Optional[AlertGenerator] = None
    ):
        self.export_directory = Path(export_directory)
        self.football_api = football_api
        self.squad_repository = squad_repository
        self.lineup_analyzer = lineup_analyzer
        self.alert_generator = alert_generator
        
        # Ensure export directory exists
        self.export_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Dashboard export service initialized, export directory: {self.export_directory}")
    
    async def export_all_data(self, monitoring_status: Dict[str, Any] = None) -> Dict[str, str]:
        """
        Export all dashboard data to JSON files.
        
        Args:
            monitoring_status: Optional monitoring status data
            
        Returns:
            Dictionary mapping data types to file paths
        """
        logger.info("Starting full dashboard data export")
        
        exported_files = {}
        
        try:
            # Export squad data
            squad_file = await self.export_squad_data()
            exported_files['squad'] = squad_file
            
            # Export today's matches (backward compatibility)
            matches_file = await self.export_todays_matches()
            exported_files['matches'] = matches_file
            
            # Export gameweek matches (new feature)
            gameweek_file = await self.export_gameweek_matches()
            exported_files['gameweek_matches'] = gameweek_file
            
            # Export system status
            status_file = await self.export_system_status(monitoring_status)
            exported_files['status'] = status_file
            
            # Export lineup status (combines squad + match data)
            lineup_file = await self.export_lineup_status()
            exported_files['lineup_status'] = lineup_file
            
            # Export metadata
            meta_file = await self.export_metadata()
            exported_files['metadata'] = meta_file
            
            logger.info(f"Dashboard export completed successfully. Files: {list(exported_files.keys())}")
            return exported_files
            
        except Exception as e:
            logger.error(f"Dashboard export failed: {e}")
            raise
    
    async def export_squad_data(self) -> str:
        """Export current squad data to JSON."""
        if not self.squad_repository:
            logger.warning("No squad repository available for export")
            return ""
        
        try:
            # Get squad from Fantrax API repository
            squad = await self.squad_repository.get_squad()
            
            squad_data = {
                'last_updated': squad.last_updated.isoformat(),
                'total_players': squad.total_count,
                'active_players': squad.active_count,
                'reserve_players': squad.reserve_count,
                'teams_represented': squad.get_teams(),
                'players': [
                    {
                        'id': player.id,
                        'name': player.name,
                        'team': {
                            'name': player.team.name,
                            'abbreviation': player.team.abbreviation
                        },
                        'position': player.position.value,
                        'status': player.status.value,
                        'is_active': player.is_active,
                        'age': player.age,
                        'opponent': player.opponent,
                        'games_played': player.games_played,
                        'draft_percentage': player.draft_percentage
                    }
                    for player in squad.players
                ]
            }
            
            file_path = self.export_directory / "squad.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(squad_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Squad data exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export squad data: {e}")
            raise
    
    async def export_todays_matches(self) -> str:
        """Export today's Premier League matches."""
        if not self.football_api:
            logger.warning("No football API available for match export")
            return ""
        
        try:
            # Get today's matches
            today = datetime.now()
            matches = await self.football_api.get_fixtures(today)
            
            matches_data = {
                'date': today.date().isoformat(),
                'total_matches': len(matches),
                'matches': [
                    {
                        'id': match.id,
                        'home_team': {
                            'name': match.home_team.name,
                            'abbreviation': match.home_team.abbreviation
                        },
                        'away_team': {
                            'name': match.away_team.name,
                            'abbreviation': match.away_team.abbreviation
                        },
                        'kickoff': match.kickoff.isoformat(),
                        'status': match.status.value,
                        'elapsed_time': match.elapsed_time,
                        'is_started': match.is_started
                    }
                    for match in matches
                ]
            }
            
            file_path = self.export_directory / "matches.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(matches_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Matches data exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export matches data: {e}")
            raise
    
    async def export_gameweek_matches(self) -> str:
        """Export complete gameweek matches (Friday-Monday) with fetch status information."""
        if not self.football_api:
            logger.warning("No football API available for gameweek match export")
            return ""
        
        try:
            # Get gameweek fixtures (Friday-Monday)
            gameweek_result = await self.football_api.get_gameweek_fixtures()
            
            # Build comprehensive gameweek data
            gameweek_data = {
                'generated_at': datetime.now().isoformat(),
                'gameweek_info': {
                    'total_matches': gameweek_result['total_matches'],
                    'successful_dates': gameweek_result['successful_dates'],
                    'failed_dates': gameweek_result['failed_dates'],
                    'fetch_summary': gameweek_result['fetch_summary'],
                    'data_quality': 'complete' if not gameweek_result['failed_dates'] else 'partial',
                    'errors': gameweek_result['errors']
                },
                'matches': [
                    {
                        'id': match.id,
                        'home_team': {
                            'name': match.home_team.name,
                            'abbreviation': match.home_team.abbreviation
                        },
                        'away_team': {
                            'name': match.away_team.name,
                            'abbreviation': match.away_team.abbreviation
                        },
                        'kickoff': match.kickoff.isoformat(),
                        'kickoff_day': match.kickoff.strftime('%A'),  # e.g., "Friday"
                        'kickoff_date': match.kickoff.date().isoformat(),
                        'kickoff_time': match.kickoff.strftime('%H:%M'),
                        'status': match.status.value,
                        'elapsed_time': match.elapsed_time,
                        'is_started': match.is_started,
                        'time_until_kickoff': self._calculate_time_until_kickoff(match.kickoff),
                        'match_day_category': self._get_match_day_category(match.kickoff)
                    }
                    for match in gameweek_result['matches']
                ],
                'date_breakdown': self._create_date_breakdown(gameweek_result['matches']),
                'summary_stats': {
                    'total_matches': len(gameweek_result['matches']),
                    'matches_by_status': self._get_matches_by_status(gameweek_result['matches']),
                    'matches_by_day': self._get_matches_by_day(gameweek_result['matches'])
                }
            }
            
            file_path = self.export_directory / "gameweek_matches.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(gameweek_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Gameweek matches exported to {file_path} - {gameweek_result['fetch_summary']}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export gameweek matches: {e}")
            raise
    
    def _calculate_time_until_kickoff(self, kickoff: datetime) -> Dict[str, Any]:
        """Calculate time remaining until kickoff."""
        now = datetime.now()
        
        if kickoff <= now:
            return {
                'status': 'started_or_finished',
                'seconds': 0,
                'human_readable': 'Match started'
            }
        
        time_diff = kickoff - now
        total_seconds = int(time_diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 24:
            days = hours // 24
            remaining_hours = hours % 24
            human_readable = f"{days}d {remaining_hours}h"
        elif hours > 0:
            human_readable = f"{hours}h {minutes}m"
        else:
            human_readable = f"{minutes}m"
        
        return {
            'status': 'upcoming',
            'seconds': total_seconds,
            'human_readable': human_readable
        }
    
    def _get_match_day_category(self, kickoff: datetime) -> str:
        """Categorize match by timing (today, tomorrow, this_weekend, etc.)."""
        now = datetime.now()
        today = now.date()
        match_date = kickoff.date()
        
        days_diff = (match_date - today).days
        
        if days_diff < 0:
            return "past"
        elif days_diff == 0:
            return "today"
        elif days_diff == 1:
            return "tomorrow"
        elif days_diff <= 3:
            return "this_weekend"
        else:
            return "future"
    
    def _create_date_breakdown(self, matches: List[Match]) -> Dict[str, List[Dict]]:
        """Create breakdown of matches by date."""
        date_breakdown = {}
        
        for match in matches:
            date_str = match.kickoff.date().isoformat()
            day_name = match.kickoff.strftime('%A')
            
            if date_str not in date_breakdown:
                date_breakdown[date_str] = {
                    'date': date_str,
                    'day_name': day_name,
                    'matches': []
                }
            
            date_breakdown[date_str]['matches'].append({
                'id': match.id,
                'home_team': match.home_team.name,
                'away_team': match.away_team.name,
                'kickoff_time': match.kickoff.strftime('%H:%M'),
                'status': match.status.value
            })
        
        # Sort by date
        return dict(sorted(date_breakdown.items()))
    
    def _get_matches_by_status(self, matches: List[Match]) -> Dict[str, int]:
        """Count matches by status."""
        status_counts = {}
        for match in matches:
            status = match.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        return status_counts
    
    def _get_matches_by_day(self, matches: List[Match]) -> Dict[str, int]:
        """Count matches by day of week."""
        day_counts = {}
        for match in matches:
            day = match.kickoff.strftime('%A')
            day_counts[day] = day_counts.get(day, 0) + 1
        return day_counts

    def _player_team_matches_fixture(self, player_team_abbrev: str, match: Match) -> bool:
        """
        Check if a player's team (abbreviation) matches either team in a fixture (full names).
        
        Args:
            player_team_abbrev: Player's team abbreviation (e.g., 'EVE')
            match: Match object with full team names
            
        Returns:
            True if the player's team is playing in this match
        """
        if not player_team_abbrev:
            return False
            
        # Convert player's team abbreviation to full name
        player_full_team_name = get_full_team_name(player_team_abbrev)
        
        # Normalize all team names for comparison
        player_normalized = normalize_team_name(player_full_team_name).lower()
        home_normalized = normalize_team_name(match.home_team.name).lower()  
        away_normalized = normalize_team_name(match.away_team.name).lower()
        
        # Check if player's team matches either home or away team
        return player_normalized == home_normalized or player_normalized == away_normalized

    async def export_lineup_status(self) -> str:
        """Export combined lineup status for dashboard main view."""
        if not (self.squad_repository and self.football_api):
            logger.warning("Missing dependencies for lineup status export")
            return ""
        
        try:
            # Get squad from Fantrax API
            squad = await self.squad_repository.get_squad()
            
            # Get gameweek matches (Friday-Monday)
            gameweek_result = await self.football_api.get_gameweek_fixtures()
            all_matches = gameweek_result['matches']
            
            # Filter matches involving squad players
            squad_teams = set(squad.get_teams())
            relevant_matches = [
                match for match in all_matches
                if any(self._player_team_matches_fixture(team, match) for team in squad_teams)
            ]
            
            # Build player lineup status
            player_status = []
            
            for player in squad.players:
                # Find player's match today (if any)
                player_match = None
                lineup_status = "no_match_today"
                opponent = None
                
                for match in relevant_matches:
                    if self._player_team_matches_fixture(player.team.name, match):
                        player_match = match
                        # Get opponent based on which team the player plays for
                        player_full_team_name = get_full_team_name(player.team.name)
                        opponent = (
                            match.away_team.name if normalize_team_name(match.home_team.name) == normalize_team_name(player_full_team_name)
                            else match.home_team.name
                        )
                        
                        # Determine lineup status
                        if match.status == MatchStatus.NOT_STARTED:
                            lineup_status = "lineup_pending"
                        else:
                            # Try to get actual lineup status
                            try:
                                lineups = await self.football_api.get_lineups(match.id)
                                player_full_team_name = get_full_team_name(player.team.name)
                                team_lineup = next((
                                    l for l in lineups 
                                    if normalize_team_name(l.team.name).lower() == normalize_team_name(player_full_team_name).lower()
                                ), None)
                                
                                if team_lineup:
                                    if team_lineup.has_player_starting(player.name):
                                        lineup_status = "confirmed_starting"
                                    elif team_lineup.has_player_on_bench(player.name):
                                        lineup_status = "confirmed_bench"
                                    else:
                                        lineup_status = "not_in_squad"
                                else:
                                    lineup_status = "lineup_unavailable"
                            except:
                                lineup_status = "lineup_unavailable"
                        break
                
                # Calculate status color for dashboard
                status_color = self._get_status_color(player, lineup_status)
                
                player_info = {
                    'id': player.id,
                    'name': player.name,
                    'team': player.team.name,
                    'team_abbreviation': player.team.abbreviation,
                    'position': player.position.value,
                    'expected_status': player.status.value,
                    'is_expected_starter': player.is_active,
                    'lineup_status': lineup_status,
                    'status_color': status_color,
                    'opponent': opponent,
                    'match_info': {
                        'id': player_match.id if player_match else None,
                        'kickoff': player_match.kickoff.isoformat() if player_match else None,
                        'status': player_match.status.value if player_match else None,
                        'home_team': player_match.home_team.name if player_match else None,
                        'away_team': player_match.away_team.name if player_match else None
                    } if player_match else None
                }
                
                player_status.append(player_info)
            
            # Summary statistics
            summary = {
                'total_players': len(player_status),
                'players_with_matches_today': len([p for p in player_status if p['match_info']]),
                'confirmed_starting': len([p for p in player_status if p['lineup_status'] == 'confirmed_starting']),
                'confirmed_bench': len([p for p in player_status if p['lineup_status'] == 'confirmed_bench']),
                'lineup_pending': len([p for p in player_status if p['lineup_status'] == 'lineup_pending']),
                'no_match_today': len([p for p in player_status if p['lineup_status'] == 'no_match_today'])
            }
            
            lineup_data = {
                'generated_at': datetime.now().isoformat(),
                'date': datetime.now().date().isoformat(),
                'summary': summary,
                'relevant_matches': len(relevant_matches),
                'players': player_status
            }
            
            file_path = self.export_directory / "lineup_status.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(lineup_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Lineup status exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export lineup status: {e}")
            raise
    
    async def export_system_status(self, monitoring_status: Dict[str, Any] = None) -> str:
        """Export system monitoring status."""
        try:
            status_data = {
                'generated_at': datetime.now().isoformat(),
                'monitoring': monitoring_status or {},
                'export_info': {
                    'export_directory': str(self.export_directory),
                    'services_available': {
                        'football_api': self.football_api is not None,
                        'squad_repository': self.squad_repository is not None,
                        'lineup_analyzer': self.lineup_analyzer is not None,
                        'alert_generator': self.alert_generator is not None
                    }
                }
            }
            
            file_path = self.export_directory / "status.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"System status exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export system status: {e}")
            raise
    
    async def export_metadata(self) -> str:
        """Export metadata about the export process."""
        try:
            metadata = {
                'generated_at': datetime.now().isoformat(),
                'format_version': '1.1',
                'dashboard_version': '1.1.0',
                'data_files': {
                    'squad': 'squad.json',
                    'matches': 'matches.json',
                    'gameweek_matches': 'gameweek_matches.json',
                    'lineup_status': 'lineup_status.json',
                    'status': 'status.json'
                },
                'features': {
                    'gameweek_fixtures': {
                        'enabled': True,
                        'description': 'Complete Friday-Monday gameweek fixture data',
                        'fetch_method': '4x concurrent API calls',
                        'error_handling': 'graceful degradation with partial data'
                    },
                    'legacy_matches': {
                        'enabled': True,
                        'description': 'Today-only matches for backward compatibility'
                    }
                },
                'refresh_info': {
                    'last_refresh': datetime.now().isoformat(),
                    'refresh_interval_seconds': 300,  # 5 minutes
                    'next_recommended_refresh': (datetime.now() + timedelta(minutes=5)).isoformat()
                }
            }
            
            file_path = self.export_directory / "metadata.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"Metadata exported to {file_path}")
            return str(file_path)
            
        except Exception as e:
            logger.error(f"Failed to export metadata: {e}")
            raise
    
    def _get_status_color(self, player: Player, lineup_status: str) -> str:
        """Get color code for player status in dashboard."""
        if lineup_status == "no_match_today":
            return "gray"
        elif lineup_status == "lineup_pending":
            return "yellow"
        elif lineup_status == "confirmed_starting":
            return "green" if player.is_active else "orange"  # Orange if unexpected starter
        elif lineup_status == "confirmed_bench":
            return "red" if player.is_active else "gray"     # Red if unexpected bench
        else:
            return "gray"  # For unavailable/unknown status
    
    def get_export_directory(self) -> Path:
        """Get the export directory path."""
        return self.export_directory
    
    def cleanup_old_exports(self, max_age_hours: int = 24):
        """Clean up old export files."""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in self.export_directory.glob("*.json"):
                if file_path.stat().st_mtime < cutoff_time.timestamp():
                    file_path.unlink()
                    logger.debug(f"Cleaned up old export file: {file_path}")
                    
        except Exception as e:
            logger.warning(f"Failed to cleanup old exports: {e}")
