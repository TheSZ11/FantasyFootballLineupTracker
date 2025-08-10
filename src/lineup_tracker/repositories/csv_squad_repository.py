"""
CSV-based squad repository implementation.

Loads squad data from Fantrax CSV exports with full parsing support
for the mixed Goalkeeper/Outfielder format with different columns.
"""

import csv
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..domain.interfaces import BaseSquadRepository
from ..domain.models import Squad, Player, Team
from ..domain.enums import Position, PlayerStatus
from ..domain.exceptions import SquadLoadError, SquadValidationError, CSVParsingError
from ..utils.team_mappings import get_full_team_name

logger = logging.getLogger(__name__)


class CSVSquadRepository(BaseSquadRepository):
    """
    Repository for loading squad data from Fantrax CSV exports.
    
    Handles the complex CSV format with mixed sections (Goalkeeper vs Outfielder)
    and different column structures, converting the data into proper domain models.
    """
    
    def __init__(self):
        self._position_mappings = self._create_position_mappings()
    
    def load_squad(self, file_path: str) -> Squad:
        """
        Load squad from Fantrax CSV export.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Squad object with all parsed players
            
        Raises:
            SquadLoadError: When file cannot be loaded
            SquadValidationError: When squad data is invalid
        """
        logger.info(f"Loading squad from {file_path}")
        
        try:
            if not Path(file_path).exists():
                raise SquadLoadError(f"Squad file not found: {file_path}")
            
            players = self._parse_csv_file(file_path)
            
            if not players:
                raise SquadValidationError("No valid players found in squad file")
            
            squad = Squad(players=players)
            
            logger.info(f"Successfully loaded squad: {squad.total_count} players "
                       f"({squad.active_count} active, {squad.reserve_count} reserve)")
            
            self._log_squad_summary(squad)
            
            return squad
            
        except (SquadLoadError, SquadValidationError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error loading squad: {e}")
            raise SquadLoadError(f"Failed to load squad from {file_path}", str(e))
    
    def save_squad(self, squad: Squad, file_path: str) -> bool:
        """
        Save squad to CSV file.
        
        Note: This is a simplified implementation. Full Fantrax format
        saving would require preserving all the original columns.
        
        Args:
            squad: Squad to save
            file_path: Path where to save
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Saving squad to {file_path}")
            
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                # Write header
                writer.writerow([
                    'ID', 'Player', 'Team', 'Position', 'Status',
                    'Fantasy Points', 'Average Points', 'Age', 'Games Played'
                ])
                
                # Write players
                for player in squad.players:
                    writer.writerow([
                        player.id,
                        player.name,
                        player.team.abbreviation,
                        self._position_to_fantrax_code(player.position),
                        player.status.value,
                        player.fantasy_points,
                        player.average_points,
                        player.age or '',
                        player.games_played or ''
                    ])
            
            logger.info("Squad saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save squad: {e}")
            return False
    
    def squad_exists(self, file_path: str) -> bool:
        """
        Check if squad file exists.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return Path(file_path).exists()
    
    def _parse_csv_file(self, file_path: str) -> List[Player]:
        """
        Parse Fantrax CSV file with mixed Goalkeeper/Outfielder sections.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            List of parsed Player objects
        """
        players = []
        current_section = None
        current_headers = None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            logger.debug(f"Processing {len(lines)} lines from CSV file")
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    # Parse CSV line (handle quoted fields properly)
                    row_data = next(csv.reader([line]))
                except csv.Error as e:
                    logger.warning(f"Could not parse line {line_num}: {e}")
                    continue
                
                # Check if this is a section header (Goalkeeper/Outfielder)
                if len(row_data) >= 2 and row_data[1] in ['Goalkeeper', 'Outfielder']:
                    current_section = row_data[1]
                    logger.debug(f"Found section: {current_section}")
                    continue
                
                # Check if this is a column header row
                if len(row_data) > 0 and row_data[0] == 'ID':
                    current_headers = row_data
                    logger.debug(f"Found headers for {current_section}: {len(current_headers)} columns")
                    continue
                
                # Check if this is a player row (ID starts with *)
                if (len(row_data) > 0 and 
                    row_data[0].startswith('*') and 
                    current_headers and 
                    current_section):
                    
                    player = self._create_player_from_row(
                        row_data, current_headers, current_section, line_num
                    )
                    
                    if player:
                        players.append(player)
                        logger.debug(f"Added player: {player.name} ({player.team.name})")
        
        except Exception as e:
            raise CSVParsingError(f"Error parsing CSV file: {e}")
        
        logger.info(f"Parsed {len(players)} players from CSV")
        return players
    
    def _create_player_from_row(
        self, 
        row_data: List[str], 
        headers: List[str], 
        section: str, 
        line_num: int
    ) -> Optional[Player]:
        """
        Create a Player object from CSV row data.
        
        Args:
            row_data: List of values from CSV row
            headers: List of column headers
            section: Current section (Goalkeeper/Outfielder)
            line_num: Line number for error reporting
            
        Returns:
            Player object if successful, None if failed
        """
        try:
            # Create player data dictionary
            player_data = {}
            for i, header in enumerate(headers):
                value = row_data[i] if i < len(row_data) else ''
                player_data[header] = value
            
            # Extract core fields
            player_id = player_data.get('ID', '').strip()
            player_name = player_data.get('Player', '').strip()
            team_abbrev = player_data.get('Team', '').strip()
            
            if not player_id or not player_name or not team_abbrev:
                logger.warning(f"Line {line_num}: Missing essential player data")
                return None
            
            # Create team object
            team = Team(
                name=get_full_team_name(team_abbrev),
                abbreviation=team_abbrev
            )
            
            # Determine position
            position = self._determine_position(player_data, section)
            
            # Determine status
            status = self._determine_status(player_data.get('Status', ''))
            
            # Parse numeric fields safely
            fantasy_points = self._safe_float_parse(player_data.get('Fantasy Points', '0'))
            average_points = self._safe_float_parse(player_data.get('Average Fantasy Points per Game', '0'))
            age = self._safe_int_parse(player_data.get('Age', ''))
            games_played = self._safe_int_parse(player_data.get('GP', ''))
            
            # Create player object
            player = Player(
                id=player_id,
                name=player_name,
                team=team,
                position=position,
                status=status,
                fantasy_points=fantasy_points,
                average_points=average_points,
                age=age,
                opponent=player_data.get('Opponent', '').strip(),
                games_played=games_played,
                draft_percentage=player_data.get('% of leagues in which player was drafted', '').strip(),
                average_draft_position=player_data.get('Average draft position among all leagues on Fantrax', '').strip()
            )
            
            return player
            
        except Exception as e:
            logger.warning(f"Line {line_num}: Error creating player: {e}")
            return None
    
    def _determine_position(self, player_data: Dict[str, str], section: str) -> Position:
        """Determine player position from data and section."""
        # First try to get position from Pos column
        pos_code = player_data.get('Pos', '').strip()
        if pos_code in self._position_mappings:
            return self._position_mappings[pos_code]
        
        # Fall back to section-based determination
        if section == 'Goalkeeper':
            return Position.GOALKEEPER
        else:
            # For outfielders without position code, default to midfielder
            return Position.MIDFIELDER
    
    def _determine_status(self, status_str: str) -> PlayerStatus:
        """Determine player status from status string."""
        status_upper = status_str.strip().upper()
        
        if status_upper == 'ACT':
            return PlayerStatus.ACTIVE
        elif status_upper == 'RES':
            return PlayerStatus.RESERVE
        else:
            # Default to reserve if unclear
            logger.debug(f"Unknown status '{status_str}', defaulting to RESERVE")
            return PlayerStatus.RESERVE
    
    def _safe_float_parse(self, value: str) -> float:
        """Safely parse float value, returning 0.0 if invalid."""
        try:
            return float(value.strip()) if value.strip() else 0.0
        except (ValueError, AttributeError):
            return 0.0
    
    def _safe_int_parse(self, value: str) -> Optional[int]:
        """Safely parse int value, returning None if invalid."""
        try:
            return int(value.strip()) if value.strip() else None
        except (ValueError, AttributeError):
            return None
    
    def _create_position_mappings(self) -> Dict[str, Position]:
        """Create mapping from Fantrax position codes to Position enum."""
        return {
            'G': Position.GOALKEEPER,
            'D': Position.DEFENDER,
            'M': Position.MIDFIELDER,
            'F': Position.FORWARD
        }
    
    def _position_to_fantrax_code(self, position: Position) -> str:
        """Convert Position enum back to Fantrax code."""
        reverse_mapping = {
            Position.GOALKEEPER: 'G',
            Position.DEFENDER: 'D',
            Position.MIDFIELDER: 'M',
            Position.FORWARD: 'F'
        }
        return reverse_mapping.get(position, 'M')
    
    def _log_squad_summary(self, squad: Squad) -> None:
        """Log a detailed summary of the loaded squad."""
        logger.info("Squad summary:")
        logger.info(f"  Total players: {squad.total_count}")
        logger.info(f"  Active players: {squad.active_count}")
        logger.info(f"  Reserve players: {squad.reserve_count}")
        
        # Team breakdown
        teams = {}
        for player in squad.players:
            team_name = player.team.name
            if team_name not in teams:
                teams[team_name] = {'active': 0, 'reserve': 0}
            
            if player.status == PlayerStatus.ACTIVE:
                teams[team_name]['active'] += 1
            else:
                teams[team_name]['reserve'] += 1
        
        logger.info("Team breakdown:")
        for team_name, counts in teams.items():
            logger.info(f"  {team_name}: {counts['active']} active, {counts['reserve']} reserve")
        
        # Position breakdown
        positions = {}
        for player in squad.players:
            pos = player.position.value
            if pos not in positions:
                positions[pos] = {'active': 0, 'reserve': 0}
            
            if player.status == PlayerStatus.ACTIVE:
                positions[pos]['active'] += 1
            else:
                positions[pos]['reserve'] += 1
        
        logger.info("Position breakdown:")
        for position, counts in positions.items():
            logger.info(f"  {position}: {counts['active']} active, {counts['reserve']} reserve")
