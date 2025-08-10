import asyncio
import os
from datetime import datetime
import logging
from sofascore_wrapper.api import SofascoreAPI
from sofascore_wrapper.league import League
from sofascore_wrapper.match import Match

logger = logging.getLogger(__name__)

class FootballAPI:
    """
    Sofascore client for Premier League fixture and lineup data.
    Uses a dedicated event loop to avoid conflicts.
    """
    
    def __init__(self):
        self._loop = None
        self._api = None
        
    def _get_loop(self):
        """Get or create a dedicated event loop"""
        if self._loop is None or self._loop.is_closed():
            try:
                # Try to create a new loop
                self._loop = asyncio.new_event_loop()
            except RuntimeError:
                # If that fails, get the current one
                try:
                    self._loop = asyncio.get_event_loop()
                except RuntimeError:
                    # Create a new one as last resort
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
        return self._loop
    
    def _run_async(self, coro):
        """Run an async function synchronously"""
        loop = self._get_loop()
        try:
            if loop.is_running():
                # If loop is running, we need to handle this differently
                # For now, just log and return empty result
                logger.warning("Event loop is already running, skipping async operation")
                return []
            else:
                return loop.run_until_complete(coro)
        except Exception as e:
            logger.error(f"Error running async operation: {e}")
            return []
    
    async def _ensure_api(self):
        """Ensure API connection is active"""
        if self._api is None:
            self._api = SofascoreAPI()
            logger.info("Sofascore API connection established")
    
    def get_premier_league_fixtures(self, date=None):
        """
        Get Premier League fixtures for specific date.
        
        Args:
            date (str, optional): Date string (YYYY-MM-DD). Ignored for Sofascore.
            
        Returns:
            list: List of fixtures in standardized format
        """
        return self._run_async(self._get_premier_league_fixtures_async(date))
    
    async def _get_premier_league_fixtures_async(self, date=None):
        """Async implementation of fixture retrieval"""
        try:
            await self._ensure_api()
            
            # Get Premier League (ID: 17)
            premier_league = League(self._api, league_id=17)
            
            # Get upcoming fixtures
            fixtures = await premier_league.next_fixtures()
            
            if not fixtures:
                logger.warning("No upcoming Premier League fixtures found")
                return []
                
            logger.info(f"Retrieved {len(fixtures)} Premier League fixtures")
            
            # Convert to standardized format
            converted_fixtures = []
            
            for fixture in fixtures:
                try:
                    converted_fixture = {
                        'fixture': {
                            'id': fixture.get('id'),
                            'date': self._convert_timestamp_to_iso(fixture.get('startTimestamp')),
                            'status': {
                                'short': self._convert_status(fixture.get('status', {})),
                                'elapsed': fixture.get('status', {}).get('elapsed')
                            }
                        },
                        'teams': {
                            'home': {
                                'name': fixture.get('homeTeam', {}).get('name', 'Unknown')
                            },
                            'away': {
                                'name': fixture.get('awayTeam', {}).get('name', 'Unknown')
                            }
                        }
                    }
                    converted_fixtures.append(converted_fixture)
                    
                except Exception as e:
                    logger.error(f"Error converting fixture {fixture.get('id', 'unknown')}: {e}")
                    continue
                    
            return converted_fixtures
            
        except Exception as e:
            logger.error(f"Error getting Premier League fixtures: {e}")
            return []
    
    def get_lineup(self, fixture_id):
        """
        Get lineup for specific fixture.
        
        Args:
            fixture_id (int): The fixture/match ID
            
        Returns:
            list: List of team lineups in standardized format
        """
        return self._run_async(self._get_lineup_async(fixture_id))
    
    async def _get_lineup_async(self, fixture_id):
        """Async implementation of lineup retrieval"""
        try:
            await self._ensure_api()
            
            match = Match(self._api, match_id=fixture_id)
            
            # Get both team lineups
            home_lineup = await match.lineups_home()
            away_lineup = await match.lineups_away()
            
            if not home_lineup or not away_lineup:
                logger.info(f"Lineup data not available yet for fixture {fixture_id}")
                return []
                
            # Get team names from match info
            match_info = await match.get_match()
            home_team_name = match_info.get('homeTeam', {}).get('name', 'Home Team')
            away_team_name = match_info.get('awayTeam', {}).get('name', 'Away Team')
            
            # Validate lineup data
            home_starters = home_lineup.get('starters', [])
            away_starters = away_lineup.get('starters', [])
            
            if len(home_starters) != 11 or len(away_starters) != 11:
                logger.warning(f"Unexpected lineup size - Home: {len(home_starters)}, Away: {len(away_starters)}")
            
            # Convert to standardized format
            lineup_data = [
                {
                    'team': {'name': home_team_name},
                    'startXI': [
                        {'player': {'name': player['player']['name']}}
                        for player in home_starters
                        if 'player' in player and 'name' in player['player']
                    ]
                },
                {
                    'team': {'name': away_team_name},
                    'startXI': [
                        {'player': {'name': player['player']['name']}}
                        for player in away_starters
                        if 'player' in player and 'name' in player['player']
                    ]
                }
            ]
            
            logger.info(f"Retrieved lineup data for {home_team_name} vs {away_team_name}")
            logger.info(f"Home starters: {len(lineup_data[0]['startXI'])}, Away starters: {len(lineup_data[1]['startXI'])}")
            
            return lineup_data
            
        except Exception as e:
            error_msg = str(e)
            if "404" in error_msg:
                logger.info(f"Lineup not yet available for fixture {fixture_id} (404 response)")
            elif "403" in error_msg:
                logger.warning(f"Access denied for fixture {fixture_id} (403 response) - possible rate limiting")
            else:
                logger.error(f"Error getting lineup for fixture {fixture_id}: {e}")
            return []
    
    def test_connection(self):
        """
        Test API connection and return status.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        return self._run_async(self._test_connection_async())
    
    async def _test_connection_async(self):
        """Async implementation of connection test"""
        try:
            await self._ensure_api()
            
            # Test by getting Premier League seasons
            premier_league = League(self._api, league_id=17)
            seasons = await premier_league.get_seasons()
            
            if seasons and len(seasons) > 0:
                logger.info(f"Sofascore API connection test successful - found {len(seasons)} seasons")
                return True
            else:
                logger.error("Sofascore API connection test failed - no seasons returned")
                return False
                
        except Exception as e:
            logger.error(f"Sofascore API connection test failed: {e}")
            return False
    
    def _convert_timestamp_to_iso(self, timestamp):
        """Convert Unix timestamp to ISO format"""
        if not timestamp:
            return None
        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.isoformat() + 'Z'
        except Exception as e:
            logger.error(f"Error converting timestamp {timestamp}: {e}")
            return None
    
    def _convert_status(self, status_obj):
        """Convert Sofascore status to standardized format"""
        if not status_obj:
            return 'TBD'
            
        status_desc = status_obj.get('description', '').lower()
        status_code = status_obj.get('code', 0)
        
        # Map Sofascore status codes to standardized format
        if status_code == 0 or 'not started' in status_desc:
            return 'NS'  # Not Started
        elif status_code == 100 or 'finished' in status_desc:
            return 'FT'  # Full Time
        elif 'live' in status_desc or 'progress' in status_desc or status_code in [6, 7]:
            return 'LIVE'  # Live/In Progress
        elif 'postponed' in status_desc:
            return 'PST'  # Postponed
        elif 'cancelled' in status_desc:
            return 'CANC'  # Cancelled
        else:
            return 'TBD'  # To Be Determined
    
    def close(self):
        """Close connections and cleanup"""
        if self._api:
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.run_until_complete(self._api.close())
                self._api = None
                logger.info("Sofascore API connection closed")
            except Exception as e:
                logger.warning(f"Error during cleanup: {e}")
                
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.close()
            except Exception:
                pass
    
    def __del__(self):
        """Cleanup on object destruction"""
        self.close()
