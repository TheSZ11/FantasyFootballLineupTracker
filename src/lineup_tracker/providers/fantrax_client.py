"""
Fantrax API client for fetching league and team data.
"""

import asyncio
import logging
from typing import Dict, List, Optional
import aiohttp

from ..domain.models import Player, Team
from ..domain.enums import Position, PlayerStatus
from ..domain.exceptions import APIError
from ..utils.retry import retry

logger = logging.getLogger(__name__)


class FantraxClient:
    """Client for interacting with Fantrax API."""
    
    BASE_URL = "https://www.fantrax.com/fxea/general"
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self._should_close_session = session is None
        
    async def __aenter__(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._should_close_session and self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure the session is initialized."""
        if self.session is None:
            self.session = aiohttp.ClientSession()
            self._should_close_session = True
    
    @retry(max_attempts=3, base_delay=1.0)
    async def get_team_roster(self, league_id: str, team_id: str) -> List[Dict]:
        """
        Get the roster for a specific team in a league.
        
        Args:
            league_id: Fantrax league ID
            team_id: Fantrax team ID
            
        Returns:
            List of player dictionaries with roster information
            
        Raises:
            APIError: If API request fails or returns invalid data
        """
        try:
            await self._ensure_session()
            
            url = f"{self.BASE_URL}/getTeamRosters"
            params = {"leagueId": league_id}
            
            logger.debug(f"Fetching team rosters for league {league_id}")
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise APIError(f"Fantrax API returned status {response.status}")
                    
                # Fantrax returns JSON but with text/plain content-type, so we need to parse manually
                response_text = await response.text()
                if not response_text.strip():
                    raise APIError("Empty response from Fantrax API")
                
                try:
                    import json
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise APIError(f"Invalid JSON response from Fantrax API: {e}")
                
                if "rosters" not in data:
                    raise APIError("Invalid response format from Fantrax API")
                
                if team_id not in data["rosters"]:
                    raise APIError(f"Team {team_id} not found in league {league_id}")
                
                team_data = data["rosters"][team_id]
                roster_items = team_data.get("rosterItems", [])
                
                logger.info(f"Successfully fetched {len(roster_items)} players for team {team_data.get('teamName', team_id)}")
                return roster_items
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching Fantrax data: {e}")
            raise APIError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching Fantrax data: {e}")
            raise APIError(f"Unexpected error: {e}")
    
    @retry(max_attempts=3, base_delay=1.0)
    async def get_league_info(self, league_id: str) -> Dict:
        """
        Get league information including team details and player pool.
        
        Args:
            league_id: Fantrax league ID
            
        Returns:
            Dictionary with league information
            
        Raises:
            APIError: If API request fails or returns invalid data
        """
        try:
            await self._ensure_session()
            
            url = f"{self.BASE_URL}/getLeagueInfo"
            params = {"leagueId": league_id}
            
            logger.debug(f"Fetching league info for {league_id}")
            
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    raise APIError(f"Fantrax API returned status {response.status}")
                    
                # Fantrax returns JSON but with text/plain content-type, so we need to parse manually
                response_text = await response.text()
                if not response_text.strip():
                    raise APIError("Empty response from Fantrax API")
                
                try:
                    import json
                    data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise APIError(f"Invalid JSON response from Fantrax API: {e}")
                
                logger.info(f"Successfully fetched league info for {data.get('leagueName', league_id)}")
                return data
                
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching league info: {e}")
            raise APIError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error fetching league info: {e}")
            raise APIError(f"Unexpected error: {e}")
    
    def map_fantrax_position(self, fantrax_position: str) -> Position:
        """
        Map Fantrax position codes to Position enums.
        
        Args:
            fantrax_position: Fantrax position code (G, D, M, F)
            
        Returns:
            Position enum value
        """
        position_mapping = {
            "G": Position.GOALKEEPER,
            "D": Position.DEFENDER, 
            "M": Position.MIDFIELDER,
            "F": Position.FORWARD
        }
        return position_mapping.get(fantrax_position, Position.MIDFIELDER)  # Default fallback
    
    def map_fantrax_status(self, fantrax_status: str) -> PlayerStatus:
        """
        Map Fantrax player status to PlayerStatus enum.
        
        Args:
            fantrax_status: Fantrax status (ACTIVE, RESERVE, INJURED_RESERVE)
            
        Returns:
            PlayerStatus enum value
        """
        status_mapping = {
            "ACTIVE": PlayerStatus.ACTIVE,
            "RESERVE": PlayerStatus.RESERVE, 
            "INJURED_RESERVE": PlayerStatus.RESERVE  # Injured players are also reserves
        }
        return status_mapping.get(fantrax_status, PlayerStatus.RESERVE)  # Default fallback
    
    async def get_team_players(self, league_id: str, team_id: str) -> List[Player]:
        """
        Get players for a team, mapped to lineup tracker Player objects.
        
        Args:
            league_id: Fantrax league ID
            team_id: Fantrax team ID
            
        Returns:
            List of Player objects ready for lineup tracker
        """
        roster_items = await self.get_team_roster(league_id, team_id)
        league_info = await self.get_league_info(league_id)
        
        # Get player pool information for names and details
        player_info = league_info.get("playerInfo", {})
        
        players = []
        for item in roster_items:
            player_id = item["id"]
            fantrax_position = item["position"]
            fantrax_status = item["status"]
            
            # Get additional player info from league data
            player_details = player_info.get(player_id, {})
            
            # Create team object - placeholder for now
            team = Team(
                name="Unknown Team",  # Would need team lookup
                abbreviation="UNK"
            )
            
            # Create player with proper types
            player = Player(
                id=player_id,
                name=f"Player_{player_id}",  # Placeholder - would need player name lookup
                team=team,
                position=self.map_fantrax_position(fantrax_position),
                status=self.map_fantrax_status(fantrax_status),
                fantasy_points=0.0,  # Placeholder
                average_points=0.0   # Placeholder
            )
            
            players.append(player)
            
        logger.info(f"Mapped {len(players)} Fantrax players to Player objects")
        return players


# Convenience function for standalone usage
async def get_fantrax_team_players(league_id: str, team_id: str) -> List[Player]:
    """
    Convenience function to get team players from Fantrax.
    
    Args:
        league_id: Fantrax league ID
        team_id: Fantrax team ID
        
    Returns:
        List of Player objects
    """
    async with FantraxClient() as client:
        return await client.get_team_players(league_id, team_id)


# Test function
async def test_fantrax_client():
    """Test the Fantrax client with real data."""
    league_id = "phdac771md8duf07"
    team_id = "xeewd9htmd8duf0g"  # player_name_team_pun
    
    try:
        async with FantraxClient() as client:
            # Test roster fetch
            roster = await client.get_team_roster(league_id, team_id)
            print(f"✅ Fetched {len(roster)} roster items")
            
            # Test league info
            league_info = await client.get_league_info(league_id)
            print(f"✅ Fetched league info for '{league_info.get('leagueName')}'")
            
            # Test player mapping
            players = await client.get_team_players(league_id, team_id)
            print(f"✅ Mapped {len(players)} players")
            
            for player in players[:3]:  # Show first 3 players
                print(f"  - {player.id}: {player.position} ({player.expected_status})")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_fantrax_client())
