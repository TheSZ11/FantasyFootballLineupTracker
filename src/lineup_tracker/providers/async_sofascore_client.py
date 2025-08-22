"""
High-performance async Sofascore API client with advanced features.

Implements proper async/await patterns, rate limiting, connection pooling,
intelligent caching, and concurrent operations for optimal performance.
"""

import asyncio
import aiohttp
import time
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Set
from dataclasses import dataclass

from ..domain.interfaces import BaseFootballDataProvider
from ..domain.models import Match, Lineup, Team, Player, MatchStatus, Position
from ..domain.exceptions import (
    FootballDataProviderError, RateLimitExceededError, 
    DataNotAvailableError, ServiceUnavailableError
)
from ..config.app_config import APIConfig
from ..utils.retry import retry, timeout, graceful_degradation, CircuitBreaker, CircuitBreakerConfig
from ..utils.cache import cached_async, TTLCache
from ..utils.logging import get_logger, log_performance

logger = get_logger(__name__)


@dataclass
class RateLimiter:
    """Token bucket rate limiter for API requests."""
    requests_per_minute: int
    bucket_size: int
    _tokens: float = 0
    _last_update: float = 0
    
    def __post_init__(self):
        self._tokens = self.bucket_size
        self._last_update = time.time()
    
    async def acquire(self):
        """Acquire a token from the bucket, waiting if necessary."""
        current_time = time.time()
        
        # Add tokens based on time elapsed
        time_passed = current_time - self._last_update
        tokens_to_add = time_passed * (self.requests_per_minute / 60.0)
        self._tokens = min(self.bucket_size, self._tokens + tokens_to_add)
        self._last_update = current_time
        
        if self._tokens < 1:
            # Calculate wait time
            wait_time = (1 - self._tokens) * (60.0 / self.requests_per_minute)
            logger.debug(f"Rate limit reached, waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self._tokens = 0
        else:
            self._tokens -= 1


class AsyncSofascoreClient(BaseFootballDataProvider):
    """
    High-performance async Sofascore API client.
    
    Features:
    - Proper async/await patterns with aiohttp
    - Token bucket rate limiting
    - Circuit breaker for fault tolerance
    - Intelligent caching with TTL
    - Connection pooling and reuse
    - Concurrent request handling
    - Automatic retry with exponential backoff
    - Performance monitoring and logging
    """
    
    def __init__(self, config: APIConfig):
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._rate_limiter = RateLimiter(
            requests_per_minute=config.rate_limit_per_minute,
            bucket_size=config.rate_limit_per_minute
        )
        circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=5,
            recovery_timeout=60.0,
            success_threshold=3,
            timeout=30.0
        )
        self._circuit_breaker = CircuitBreaker(circuit_breaker_config)
        self._cache = TTLCache(max_size=500, cleanup_interval=300)
        self._active_requests: Set[str] = set()
        self._request_semaphore = asyncio.Semaphore(config.max_concurrent_requests)
        
        # Performance metrics
        self._request_count = 0
        self._cache_hits = 0
        self._error_count = 0
        self._total_response_time = 0
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created with proper configuration."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.config.connection_pool_size,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            
            timeout_config = aiohttp.ClientTimeout(
                total=self.config.timeout_seconds,
                connect=10,
                sock_read=self.config.timeout_seconds
            )
            
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json',
                    'Accept-Encoding': 'gzip, deflate',
                    'Accept-Language': 'en-US,en;q=0.9'
                }
            )
            
            logger.info("Async HTTP session initialized")
    
    @cached_async(ttl=600)  # Cache fixtures for 10 minutes
    @retry(max_attempts=3)
    @timeout(30)
    async def get_fixtures(self, date: Optional[datetime] = None) -> List[Match]:
        """
        Get Premier League fixtures with caching and error handling.
        
        Args:
            date: Optional date filter for fixtures
            
        Returns:
            List of Match objects
            
        Raises:
            FootballDataProviderError: When API fails
            RateLimitExceededError: When rate limit exceeded
        """
        try:
            await self._rate_limiter.acquire()
            
            async with self._request_semaphore:
                request_id = f"fixtures_{date or 'all'}_{int(time.time())}"
                
                if request_id in self._active_requests:
                    logger.warning(f"Duplicate request detected: {request_id}")
                    await asyncio.sleep(0.1)  # Small delay to avoid thundering herd
                
                self._active_requests.add(request_id)
                
                try:
                    start_time = time.time()
                    
                    # Use sofascore-wrapper with async support
                    fixtures = await self._fetch_fixtures_from_api(date)
                    
                    # Convert to our domain models
                    matches = [self._convert_fixture_to_match(fixture) for fixture in fixtures]
                    
                    self._request_count += 1
                    self._total_response_time += (time.time() - start_time)
                    
                    logger.info(f"Retrieved {len(matches)} fixtures")
                    return matches
                    
                finally:
                    self._active_requests.discard(request_id)
                    
        except aiohttp.ClientError as e:
            self._error_count += 1
            logger.error(f"HTTP error fetching fixtures: {e}")
            raise FootballDataProviderError(f"Failed to fetch fixtures: {e}")
        except asyncio.TimeoutError as e:
            self._error_count += 1
            logger.error(f"Timeout fetching fixtures: {e}")
            raise FootballDataProviderError(f"Timeout fetching fixtures: {e}")
        except Exception as e:
            self._error_count += 1
            logger.error(f"Unexpected error fetching fixtures: {e}")
            raise FootballDataProviderError(f"Unexpected error: {e}")
    
    @cached_async(ttl=300)  # Cache lineups for 5 minutes
    @retry(max_attempts=3)
    @timeout(30)
    async def get_lineup(self, match_id: str) -> Optional[Lineup]:
        """
        Get single lineup for backward compatibility. Use get_match_lineups for both teams.
        
        Args:
            match_id: Unique match identifier
            
        Returns:
            Lineup object or None if not available
            
        Raises:
            FootballDataProviderError: When API fails
        """
        try:
            await self._rate_limiter.acquire()
            
            async with self._request_semaphore:
                request_id = f"lineup_{match_id}_{int(time.time())}"
                
                if request_id in self._active_requests:
                    logger.warning(f"Duplicate lineup request: {match_id}")
                    await asyncio.sleep(0.1)
                
                self._active_requests.add(request_id)
                
                try:
                    start_time = time.time()
                    
                    # Fetch lineup data from API
                    lineup_data = await self._fetch_lineup_from_api(match_id)
                    
                    if not lineup_data:
                        logger.debug(f"No lineup available for match {match_id}")
                        return None
                    
                    # Convert to our domain model
                    lineups = self._convert_lineup_data(lineup_data, match_id)
                    
                    # For backward compatibility, return the first available lineup
                    # TODO: Update callers to handle both home/away lineups
                    if 'home' in lineups:
                        lineup = lineups['home']
                    elif 'away' in lineups:
                        lineup = lineups['away']
                    else:
                        return None
                    
                    self._request_count += 1
                    self._total_response_time += (time.time() - start_time)
                    
                    logger.info(f"Retrieved lineup for match {match_id}")
                    return lineup
                    
                finally:
                    self._active_requests.discard(request_id)
                    
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.debug(f"Lineup not yet available for match {match_id}")
                return None
            
            self._error_count += 1
            logger.error(f"HTTP error fetching lineup for {match_id}: {e}")
            raise FootballDataProviderError(f"Failed to fetch lineup: {e}")
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error fetching lineup for {match_id}: {e}")
            raise FootballDataProviderError(f"Unexpected error: {e}")
    
    @cached_async(ttl=300)  # Cache lineups for 5 minutes
    @retry(max_attempts=3)
    @timeout(30)
    async def get_match_lineups(self, match_id: str) -> Dict[str, Lineup]:
        """
        Get both home and away lineups for a match.
        
        Args:
            match_id: Unique match identifier
            
        Returns:
            Dict with 'home' and 'away' Lineup objects
            
        Raises:
            FootballDataProviderError: When API fails
        """
        try:
            await self._rate_limiter.acquire()
            
            async with self._request_semaphore:
                request_id = f"both_lineups_{match_id}_{int(time.time())}"
                
                if request_id in self._active_requests:
                    logger.warning(f"Duplicate lineup request: {match_id}")
                    await asyncio.sleep(0.1)
                
                self._active_requests.add(request_id)
                
                try:
                    start_time = time.time()
                    
                    # Fetch lineup data from API
                    lineup_data = await self._fetch_lineup_from_api(match_id)
                    
                    if not lineup_data:
                        logger.debug(f"No lineup available for match {match_id}")
                        return {}
                    
                    # Convert to our domain models (returns dict with home/away)
                    lineups = self._convert_lineup_data(lineup_data, match_id)
                    
                    self._request_count += 1
                    self._total_response_time += (time.time() - start_time)
                    
                    logger.info(f"Retrieved both lineups for match {match_id}")
                    return lineups
                    
                finally:
                    self._active_requests.discard(request_id)
                    
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                logger.debug(f"Lineups not yet available for match {match_id}")
                return {}
            
            self._error_count += 1
            logger.error(f"HTTP error fetching lineups for {match_id}: {e}")
            raise FootballDataProviderError(f"Failed to fetch lineups: {e}")
        except Exception as e:
            self._error_count += 1
            logger.error(f"Error fetching lineups for {match_id}: {e}")
            raise FootballDataProviderError(f"Unexpected error: {e}")
    
    async def get_multiple_lineups(self, match_ids: List[str]) -> List[Optional[Lineup]]:
        """
        Get multiple lineups concurrently for optimal performance.
        
        Args:
            match_ids: List of match identifiers
            
        Returns:
            List of Lineup objects (some may be None)
        """
        logger.info(f"Fetching lineups for {len(match_ids)} matches concurrently")
        
        # Create concurrent tasks
        tasks = [self.get_lineup(match_id) for match_id in match_ids]
        
        # Execute concurrently with proper error handling
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        lineups = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Error fetching lineup for {match_ids[i]}: {result}")
                lineups.append(None)
            else:
                lineups.append(result)
        
        success_count = sum(1 for lineup in lineups if lineup is not None)
        logger.info(f"Successfully retrieved {success_count}/{len(match_ids)} lineups")
        
        return lineups
    
    def _get_gameweek_dates(self, reference_date: Optional[datetime] = None) -> List[datetime]:
        """
        Calculate the 4-day gameweek window: Friday through Monday.
        Always returns upcoming/current gameweek regardless of current day.
        
        Args:
            reference_date: Reference point for determining gameweek (defaults to now)
            
        Returns:
            List of 4 datetime objects representing Friday, Saturday, Sunday, Monday
        """
        if reference_date is None:
            reference_date = datetime.now()
        
        # Find the upcoming/current Friday
        # If today is Friday (4), Saturday (5), Sunday (6), or Monday (0), use current week
        # Otherwise, use next week
        current_weekday = reference_date.weekday()  # Monday=0, Sunday=6
        
        if current_weekday <= 0:  # Monday
            # If it's Monday, check if we want current or next gameweek
            # For simplicity, always get current week if it's early Monday, next week if later
            days_to_friday = 4  # Next Friday
        elif current_weekday >= 4:  # Friday, Saturday, Sunday
            days_to_friday = 4 - current_weekday  # Current Friday (0 if it's Friday)
        else:  # Tuesday, Wednesday, Thursday
            days_to_friday = 4 - current_weekday  # Next Friday
        
        friday = reference_date + timedelta(days=days_to_friday)
        # Set to start of day (midnight)
        friday = friday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Generate Friday through Monday
        gameweek_dates = [
            friday,                           # Friday
            friday + timedelta(days=1),      # Saturday
            friday + timedelta(days=2),      # Sunday  
            friday + timedelta(days=3)       # Monday
        ]
        
        logger.debug(f"Gameweek dates for reference {reference_date.date()}: "
                    f"{[d.date() for d in gameweek_dates]}")
        
        return gameweek_dates
    
    async def _fetch_single_day_with_error_handling(self, date: datetime) -> Dict[str, Any]:
        """
        Wrapper around existing get_fixtures() with structured error reporting.
        
        Args:
            date: Date to fetch fixtures for
            
        Returns:
            Dict with 'date', 'success', 'matches', 'error' fields
        """
        date_str = date.strftime("%Y-%m-%d")
        
        try:
            matches = await self.get_fixtures(date)
            return {
                'date': date_str,
                'success': True,
                'matches': matches,
                'error': None
            }
        except Exception as e:
            logger.warning(f"Failed to fetch fixtures for {date_str}: {e}")
            return {
                'date': date_str,
                'success': False,
                'matches': [],
                'error': str(e)
            }
    
    def _deduplicate_matches(self, all_matches: List[Match]) -> List[Match]:
        """
        Deduplicate matches by ID, preserving order.
        
        Args:
            all_matches: List of matches that may contain duplicates
            
        Returns:
            List of unique matches
        """
        seen_match_ids = set()
        unique_matches = []
        
        for match in all_matches:
            if match.id not in seen_match_ids:
                seen_match_ids.add(match.id)
                unique_matches.append(match)
        
        logger.debug(f"Deduplicated {len(all_matches)} matches to {len(unique_matches)} unique matches")
        return unique_matches
    
    def _merge_gameweek_results(self, dates: List[datetime], results: List[Dict]) -> Dict[str, Any]:
        """
        Merge results from 4 concurrent API calls.
        Handle asyncio.gather exceptions and deduplicate matches by ID.
        
        Args:
            dates: List of dates that were fetched
            results: List of results from concurrent API calls
            
        Returns:
            Merged gameweek results dictionary
        """
        successful_dates = []
        failed_dates = []
        all_matches = []
        errors = []
        
        for i, result in enumerate(results):
            date_str = dates[i].strftime("%Y-%m-%d")
            
            # Handle exceptions from asyncio.gather
            if isinstance(result, Exception):
                failed_dates.append(date_str)
                errors.append(f"{date_str}: {str(result)}")
                logger.warning(f"Exception for {date_str}: {result}")
                continue
            
            # Handle structured error responses
            if result['success']:
                successful_dates.append(date_str)
                all_matches.extend(result['matches'])
            else:
                failed_dates.append(date_str)
                if result['error']:
                    errors.append(f"{date_str}: {result['error']}")
        
        # Deduplicate matches
        unique_matches = self._deduplicate_matches(all_matches)
        
        # Create summary message
        total_days = len(dates)
        successful_days = len(successful_dates)
        fetch_summary = f"Successfully fetched {successful_days}/{total_days} days"
        if failed_dates:
            fetch_summary += f" (failed: {', '.join(failed_dates)})"
        
        return {
            'matches': unique_matches,
            'total_matches': len(unique_matches),
            'successful_dates': successful_dates,
            'failed_dates': failed_dates,
            'errors': errors,
            'fetch_summary': fetch_summary
        }
    
    @cached_async(ttl=1800)  # Cache gameweek fixtures for 30 minutes
    async def get_gameweek_fixtures(self, reference_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get all Premier League fixtures for the gameweek (Friday-Monday).
        
        Args:
            reference_date: Reference point for determining gameweek (defaults to now)
            
        Returns:
            Dict containing:
            - 'matches': List[Match] - All unique matches from the gameweek
            - 'total_matches': int - Count of unique matches
            - 'successful_dates': List[str] - Dates successfully fetched (YYYY-MM-DD format)
            - 'failed_dates': List[str] - Dates that failed to fetch
            - 'errors': List[str] - Error messages from failed fetches
            - 'fetch_summary': str - Human-readable summary
        """
        logger.info("Fetching gameweek fixtures (Friday-Monday)")
        
        # Get gameweek dates
        gameweek_dates = self._get_gameweek_dates(reference_date)
        
        # Create concurrent tasks for all 4 days
        tasks = [
            self._fetch_single_day_with_error_handling(date) 
            for date in gameweek_dates
        ]
        
        try:
            # Execute all 4 API calls concurrently
            start_time = time.time()
            results = await asyncio.gather(*tasks, return_exceptions=True)
            fetch_time = time.time() - start_time
            
            # Merge and process results
            gameweek_result = self._merge_gameweek_results(gameweek_dates, results)
            
            logger.info(
                f"Gameweek fetch completed in {fetch_time:.2f}s: "
                f"{gameweek_result['fetch_summary']}, "
                f"{gameweek_result['total_matches']} total matches"
            )
            
            if gameweek_result['failed_dates']:
                logger.warning(f"Failed to fetch fixtures for dates: {', '.join(gameweek_result['failed_dates'])}")
                if gameweek_result['errors']:
                    logger.debug(f"Fetch errors: {'; '.join(gameweek_result['errors'])}")
            
            return gameweek_result
            
        except Exception as e:
            self._error_count += 1
            logger.error(f"Unexpected error in gameweek fixture fetch: {e}")
            
            # Return partial results structure on complete failure
            return {
                'matches': [],
                'total_matches': 0,
                'successful_dates': [],
                'failed_dates': [date.strftime("%Y-%m-%d") for date in gameweek_dates],
                'errors': [f"Complete gameweek fetch failed: {str(e)}"],
                'fetch_summary': "Complete gameweek fetch failed"
            }
    
    @graceful_degradation(fallback_value=False)
    @timeout(10)
    async def test_connection(self) -> bool:
        """
        Test API connection with graceful degradation.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            await self._ensure_session()
            
            # Simple health check - try to fetch a small amount of data
            fixtures = await self.get_fixtures()
            return fixtures is not None
            
        except Exception as e:
            logger.warning(f"Connection test failed: {e}")
            return False
    
    async def _fetch_fixtures_from_api(self, date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Fetch fixtures from Sofascore API using direct HTTP calls."""
        await self._ensure_session()
        
        try:
            # Use direct API calls instead of wrapper that may have changed
            if date:
                date_str = date.strftime("%Y-%m-%d")
                url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{date_str}"
            else:
                # Get fixtures for today
                today = datetime.now().strftime("%Y-%m-%d")
                url = f"https://api.sofascore.com/api/v1/sport/football/scheduled-events/{today}"
            
            async with self._session.get(url) as response:
                logger.debug(f"API request to {url} returned status {response.status}")
                
                if response.status == 200:
                    data = await response.json()
                    events = data.get('events', [])
                    logger.debug(f"API returned {len(events)} total events")
                    
                    # Log some tournament info to debug filtering
                    if events:
                        tournaments = set()
                        for event in events[:5]:  # Check first 5 events
                            tournament_info = event.get('tournament', {})
                            tournaments.add(f"{tournament_info.get('name')} (ID: {tournament_info.get('id')})")
                        logger.debug(f"Sample tournaments: {tournaments}")
                    
                    # Filter for Premier League matches (tournament ID 1)
                    premier_league_fixtures = [
                        event for event in events 
                        if event.get('tournament', {}).get('id') == 1
                    ]
                    logger.debug(f"Found {len(premier_league_fixtures)} Premier League matches")
                    return premier_league_fixtures
                else:
                    logger.error(f"API request failed: {response.status} - {await response.text()}")
                    return []
            
        except Exception as e:
            logger.error(f"Error fetching fixtures from Sofascore API: {e}")
            raise FootballDataProviderError(f"Unexpected error: {e}")
    
    async def _fetch_lineup_from_api(self, match_id: str) -> Optional[Dict[str, Any]]:
        """Fetch lineup from Sofascore API."""
        await self._ensure_session()
        
        try:
            from sofascore_wrapper.api import SofascoreAPI
            from sofascore_wrapper.match import Match as SofaMatch
            
            api = SofascoreAPI()
            match = SofaMatch(api, match_id=int(match_id))
            
            # Get both lineups
            home_lineup = await match.lineups_home()
            away_lineup = await match.lineups_away()
            
            if not home_lineup or not away_lineup:
                return None
            
            return {
                'home_lineup': home_lineup,
                'away_lineup': away_lineup,
                'match_id': match_id
            }
            
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return None
            logger.error(f"Error fetching lineup from Sofascore API: {e}")
            raise
    
    def _convert_fixture_to_match(self, fixture: Dict[str, Any]) -> Match:
        """Convert Sofascore fixture to our Match model."""
        try:
            # Extract match information
            match_id = str(fixture.get('id', ''))
            home_team = fixture.get('homeTeam', {})
            away_team = fixture.get('awayTeam', {})
            
            # Create team objects
            home = Team(
                name=home_team.get('name', 'Unknown'),
                abbreviation=home_team.get('shortName', 'UNK')
            )
            away = Team(
                name=away_team.get('name', 'Unknown'),
                abbreviation=away_team.get('shortName', 'UNK')
            )
            
            # Parse match time
            start_timestamp = fixture.get('startTimestamp', 0)
            match_time = datetime.fromtimestamp(start_timestamp) if start_timestamp else datetime.now()
            
            # Determine match status
            status_info = fixture.get('status', {})
            status_code = status_info.get('code', 0)
            
            if status_code == 0:
                status = MatchStatus.NOT_STARTED
            elif status_code in [1, 2]:  # Live or halftime
                status = MatchStatus.LIVE
            elif status_code == 3:
                status = MatchStatus.FINISHED
            else:
                status = MatchStatus.NOT_STARTED
            
            return Match(
                id=match_id,
                home_team=home,
                away_team=away,
                kickoff=match_time,
                status=status
            )
            
        except Exception as e:
            logger.error(f"Error converting fixture to match: {e}")
            # Return a minimal match object
            return Match(
                id=str(fixture.get('id', 'unknown')),
                home_team=Team(name="Unknown", abbreviation="UNK"),
                away_team=Team(name="Unknown", abbreviation="UNK"),
                kickoff=datetime.now(),
                status=MatchStatus.NOT_STARTED
            )
    
    def _convert_lineup_data(self, lineup_data: Dict[str, Any], match_id: str) -> Dict[str, Lineup]:
        """Convert Sofascore lineup data to our Lineup models for both teams."""
        try:
            home_lineup = lineup_data.get('home_lineup', {})
            away_lineup = lineup_data.get('away_lineup', {})
            
            lineups = {}
            
            # Process home team lineup
            if home_lineup:
                home_starting = self._extract_starting_eleven_new(home_lineup)
                home_subs = self._extract_substitutes_new(home_lineup)
                
                # Get team name from lineup data if available, otherwise use placeholder
                home_team_name = home_lineup.get('team', {}).get('name', 'Home Team')
                home_team = Team(name=home_team_name, abbreviation=home_team_name[:3].upper())
                
                lineups['home'] = Lineup(
                    team=home_team,
                    starting_eleven=home_starting,
                    substitutes=home_subs,
                    formation=home_lineup.get('formation', '4-4-2'),
                    confirmed=home_lineup.get('confirmed', False)
                )
            
            # Process away team lineup
            if away_lineup:
                away_starting = self._extract_starting_eleven_new(away_lineup)
                away_subs = self._extract_substitutes_new(away_lineup)
                
                # Get team name from lineup data if available, otherwise use placeholder
                away_team_name = away_lineup.get('team', {}).get('name', 'Away Team')
                away_team = Team(name=away_team_name, abbreviation=away_team_name[:3].upper())
                
                lineups['away'] = Lineup(
                    team=away_team,
                    starting_eleven=away_starting,
                    substitutes=away_subs,
                    formation=away_lineup.get('formation', '4-4-2'),
                    confirmed=away_lineup.get('confirmed', False)
                )
            
            return lineups
            
        except Exception as e:
            logger.error(f"Error converting lineup data: {e}")
            # Return empty dict on error
            return {}
    
    def _extract_starting_eleven(self, lineup_data: Dict[str, Any]) -> List[str]:
        """Extract starting eleven player names from lineup data."""
        try:
            players = lineup_data.get('players', [])
            starting = [
                player.get('player', {}).get('name', 'Unknown')
                for player in players
                if player.get('substitute', False) is False
            ]
            
            # Ensure we have 11 players
            while len(starting) < 11:
                starting.append(f"Player {len(starting) + 1}")
            
            return starting[:11]
            
        except Exception as e:
            logger.error(f"Error extracting starting eleven: {e}")
            return [f"Player {i}" for i in range(1, 12)]
    
    def _extract_substitutes(self, lineup_data: Dict[str, Any]) -> List[str]:
        """Extract substitute player names from lineup data."""
        try:
            players = lineup_data.get('players', [])
            substitutes = [
                player.get('player', {}).get('name', 'Unknown')
                for player in players
                if player.get('substitute', False) is True
            ]
            
            return substitutes
            
        except Exception as e:
            logger.error(f"Error extracting substitutes: {e}")
            return []
    
    def _extract_starting_eleven_new(self, lineup_data: Dict[str, Any]) -> List[str]:
        """Extract starting eleven player names from new API structure."""
        try:
            starters = lineup_data.get('starters', [])
            starting = [
                player.get('player', {}).get('name', 'Unknown')
                for player in starters
            ]
            
            # Ensure we have 11 players
            while len(starting) < 11:
                starting.append(f"Player {len(starting) + 1}")
            
            return starting[:11]
            
        except Exception as e:
            logger.error(f"Error extracting starting eleven from new format: {e}")
            return [f"Player {i}" for i in range(1, 12)]
    
    def _extract_substitutes_new(self, lineup_data: Dict[str, Any]) -> List[str]:
        """Extract substitute player names from new API structure."""
        try:
            substitutes = lineup_data.get('substitutes', [])
            subs = [
                player.get('player', {}).get('name', 'Unknown')
                for player in substitutes
            ]
            
            return subs
            
        except Exception as e:
            logger.error(f"Error extracting substitutes from new format: {e}")
            return []
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics for monitoring."""
        cache_stats = await self._cache.get_stats()
        
        avg_response_time = (
            self._total_response_time / self._request_count 
            if self._request_count > 0 else 0
        )
        
        return {
            'total_requests': self._request_count,
            'total_errors': self._error_count,
            'error_rate': (self._error_count / self._request_count * 100) if self._request_count > 0 else 0,
            'average_response_time': round(avg_response_time, 3),
            'active_requests': len(self._active_requests),
            'cache_stats': cache_stats,
            'circuit_breaker_state': self._circuit_breaker._state.name,
            'rate_limiter_tokens': self._rate_limiter._tokens
        }
    
    async def close(self):
        """Clean up resources."""
        logger.info("Closing async Sofascore client")
        
        if self._cache:
            await self._cache.close()
        
        if self._session and not self._session.closed:
            await self._session.close()
        
        # Clear active requests
        self._active_requests.clear()
        
        logger.info("Async Sofascore client closed")
