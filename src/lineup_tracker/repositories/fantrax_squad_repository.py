"""
Squad repository that fetches player data from Fantrax instead of CSV files.
"""

import asyncio
import logging
from typing import List, Optional
from datetime import datetime

from ..domain.interfaces import SquadRepository
from ..domain.models import Player, PlayerStatus, Squad
from ..domain.exceptions import APIError
from ..providers.fantrax_client import FantraxClient

logger = logging.getLogger(__name__)


class FantraxSquadRepository(SquadRepository):
    """Squad repository that fetches data from Fantrax API."""
    
    def __init__(
        self, 
        league_id: str, 
        team_id: str,
        fantrax_client: Optional[FantraxClient] = None
    ):
        """
        Initialize the Fantrax squad repository.
        
        Args:
            league_id: Fantrax league ID
            team_id: Fantrax team ID  
            fantrax_client: Optional Fantrax client (will create if not provided)
        """
        self.league_id = league_id
        self.team_id = team_id
        self.fantrax_client = fantrax_client
        self._should_close_fantrax = fantrax_client is None
        
    async def __aenter__(self):
        if self.fantrax_client is None:
            self.fantrax_client = FantraxClient()
            await self.fantrax_client.__aenter__()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_fantrax and self.fantrax_client:
            await self.fantrax_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def get_squad(self) -> List[Player]:
        """
        Get the current squad from Fantrax, enriched with SofaScore data.
        
        Returns:
            List of Player objects with current squad
            
        Raises:
            APIError: If unable to fetch squad data
        """
        try:
            logger.info(f"Fetching squad from Fantrax for team {self.team_id}")
            
            # Get base roster from Fantrax
            fantrax_players = await self.fantrax_client.get_team_players(
                self.league_id, self.team_id
            )
            
            # Return the squad with basic Fantrax data
            logger.info(f"Successfully fetched {len(fantrax_players)} players from Fantrax")
            return Squad(players=fantrax_players)
                
        except Exception as e:
            logger.error(f"Failed to fetch squad from Fantrax: {e}")
            raise APIError(f"Failed to fetch squad: {e}")
    

    async def save_squad(self, players: List[Player]) -> None:
        """
        Save squad data - not supported for Fantrax (read-only).
        
        Args:
            players: List of players to save
            
        Raises:
            NotImplementedError: Fantrax repository is read-only
        """
        raise NotImplementedError(
            "Fantrax repository is read-only. Squad changes must be made in Fantrax directly."
        )
    
    async def get_last_update(self) -> Optional[datetime]:
        """
        Get the last update time - returns current time for live data.
        
        Returns:
            Current datetime as this is live data
        """
        return datetime.now()
    
    async def validate_squad(self) -> bool:
        """
        Validate the current squad from Fantrax.
        
        Returns:
            True if squad is valid, False otherwise
        """
        try:
            squad = await self.get_squad()
            
            # Basic validation
            if not squad or not squad.players:
                logger.error("Squad is empty")
                return False
                
            # Check for required positions (at least 1 goalkeeper)
            goalkeepers = [p for p in squad.players if p.position.value.lower() == "goalkeeper"]
            if not goalkeepers:
                logger.error("No goalkeepers found in squad")
                return False
                
            # Check for reasonable squad size
            if len(squad.players) < 10 or len(squad.players) > 20:
                logger.warning(f"Unusual squad size: {len(squad.players)} players")
                
            logger.info(f"Squad validation passed: {len(squad.players)} players")
            return True
            
        except Exception as e:
            logger.error(f"Squad validation failed: {e}")
            return False


# Factory function for easy creation
def create_fantrax_squad_repository(
    league_id: str,
    team_id: str
) -> FantraxSquadRepository:
    """
    Create a Fantrax squad repository with the given configuration.
    
    Args:
        league_id: Fantrax league ID
        team_id: Fantrax team ID
        
    Returns:
        Configured FantraxSquadRepository
    """
    return FantraxSquadRepository(
        league_id=league_id,
        team_id=team_id
    )


# Test function
async def test_fantrax_squad_repository():
    """Test the Fantrax squad repository."""
    league_id = "phdac771md8duf07"
    team_id = "xeewd9htmd8duf0g"  # player_name_team_pun
    
    try:
        async with create_fantrax_squad_repository(league_id, team_id) as repo:
            # Test squad fetch
            squad = await repo.get_squad()
            print(f"✅ Fetched squad with {len(squad)} players")
            
            # Show some players
            for player in squad[:3]:
                print(f"  - {player.name} ({player.team}): {player.position} - {player.expected_status}")
            
            # Test validation
            is_valid = await repo.validate_squad()
            print(f"✅ Squad validation: {'PASSED' if is_valid else 'FAILED'}")
            
            # Test last update
            last_update = await repo.get_last_update()
            print(f"✅ Last update: {last_update}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_fantrax_squad_repository())
