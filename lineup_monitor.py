import pandas as pd
import logging
from datetime import datetime, timedelta
import pytz
from sofascore_client import FootballAPI
from notifications import NotificationHandler
from src.lineup_tracker.utils.team_mappings import get_full_team_name

logger = logging.getLogger(__name__)

class LineupMonitor:
    def __init__(self, squad_csv_path="my_roster.csv"):
        self.squad_csv_path = squad_csv_path
        self.api = FootballAPI()
        self.notifier = NotificationHandler()
        self.last_check = {}  # Track last check times to avoid spam
        
    def load_squad(self):
        """Load current squad from Fantrax CSV file"""
        try:
            # Custom parser for Fantrax CSV with mixed column structures
            processed_squad = []
            
            with open(self.squad_csv_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            current_section = None
            current_headers = None
            
            for line_num, line in enumerate(lines, 1):
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Parse CSV line (handle quoted fields)
                import csv
                try:
                    row_data = next(csv.reader([line]))
                except:
                    logger.warning(f"Could not parse line {line_num}: {line}")
                    continue
                
                # Check if this is a section header
                if len(row_data) >= 2 and row_data[1] in ['Goalkeeper', 'Outfielder']:
                    current_section = row_data[1]
                    logger.debug(f"Found section: {current_section}")
                    continue
                
                # Check if this is a column header row
                if len(row_data) > 0 and row_data[0] == 'ID':
                    current_headers = row_data
                    logger.debug(f"Found headers for {current_section}: {len(current_headers)} columns")
                    continue
                
                # Check if this is a player row (has ID starting with *)
                if len(row_data) > 0 and row_data[0].startswith('*') and current_headers:
                    try:
                        # Create player dict from row data
                        player_data = {}
                        for i, header in enumerate(current_headers):
                            if i < len(row_data):
                                player_data[header] = row_data[i]
                            else:
                                player_data[header] = ''
                        
                        # Extract the core fields we need
                        player = {
                            'player_name': player_data.get('Player', ''),
                            'team_name': get_full_team_name(player_data.get('Team', '')),
                            'position': self._map_position(player_data.get('Pos', '')),
                            'currently_starting': player_data.get('Status', '').upper() == 'ACT',
                            
                            # Additional Fantrax data
                            'fantrax_id': player_data.get('ID', ''),
                            'team_abbreviation': player_data.get('Team', ''),
                            'age': player_data.get('Age', ''),
                            'opponent': player_data.get('Opponent', ''),
                            'fantasy_points': player_data.get('Fantasy Points', ''),
                            'average_points': player_data.get('Average Fantasy Points per Game', ''),
                            'draft_percentage': player_data.get('% of leagues in which player was drafted', ''),
                            'average_draft_position': player_data.get('Average draft position among all leagues on Fantrax', ''),
                            'games_played': player_data.get('GP', ''),
                            'section': current_section  # Track if goalkeeper or outfielder
                        }
                        
                        # Only add if we have essential data
                        if player['player_name'] and player['team_name']:
                            processed_squad.append(player)
                            logger.debug(f"Added player: {player['player_name']} ({player['team_name']})")
                        
                    except Exception as e:
                        logger.warning(f"Error processing player row {line_num}: {e}")
                        continue
            
            if not processed_squad:
                logger.error("No valid players found in roster file")
                return []

            
            logger.info(f"Loaded roster: {len(processed_squad)} players")
            
            # Enhanced squad summary with Fantrax data
            active_players = [p for p in processed_squad if p['currently_starting']]
            reserve_players = [p for p in processed_squad if not p['currently_starting']]
            
            logger.info(f"Squad composition: {len(active_players)} active, {len(reserve_players)} reserve")
            
            # Log team breakdown
            teams = {}
            for player in processed_squad:
                team = player['team_name']
                if team not in teams:
                    teams[team] = {'active': 0, 'reserve': 0}
                
                if player['currently_starting']:
                    teams[team]['active'] += 1
                else:
                    teams[team]['reserve'] += 1
            
            logger.info("Team breakdown:")
            for team, counts in teams.items():
                logger.info(f"  {team}: {counts['active']} active, {counts['reserve']} reserve")
            
            return processed_squad
            
        except FileNotFoundError:
            logger.error(f"Roster file not found: {self.squad_csv_path}")
            logger.error("Please ensure my_roster.csv exists with your Fantrax roster export")
            return []
        except Exception as e:
            logger.error(f"Failed to load roster: {e}")
            return []
    
    def _map_position(self, fantrax_position):
        """Map Fantrax position codes to readable positions"""
        position_map = {
            'G': 'Goalkeeper',
            'D': 'Defender', 
            'M': 'Midfielder',
            'F': 'Forward'
        }
        return position_map.get(fantrax_position, fantrax_position)
    
    def get_matches_with_squad_players(self):
        """Get matches with squad players - combines CSV timing with API fixture data"""
        squad = self.load_squad()
        
        if not squad:
            return []
        
        # First get CSV-based match timing (accurate)
        csv_matches = self._get_csv_matches(squad)
        
        # Then get API fixtures to map to real fixture IDs
        api_fixtures = self.api.get_premier_league_fixtures()
        
        # Combine both datasets
        relevant_matches = []
        eastern_tz = pytz.timezone('US/Eastern')
        
        for csv_match in csv_matches:
            # Try to find matching API fixture
            api_fixture = self._find_matching_api_fixture(csv_match, api_fixtures, eastern_tz)
            
            if api_fixture:
                # Use CSV timing but API fixture data
                relevant_matches.append({
                    'fixture_id': api_fixture['fixture']['id'],
                    'home_team': api_fixture['teams']['home']['name'],
                    'away_team': api_fixture['teams']['away']['name'],
                    'kickoff': csv_match['kickoff'],  # Use accurate CSV timing
                    'status': api_fixture['fixture']['status']['short'],
                    'elapsed': api_fixture['fixture']['status'].get('elapsed'),
                    'players': csv_match['players']
                })
            else:
                # Fallback to CSV-only data (no lineup checking possible)
                logger.warning(f"Could not find API fixture for {csv_match['home_team']} vs {csv_match['away_team']}")
                csv_match['fixture_id'] = None  # Mark as no API data
                relevant_matches.append(csv_match)
        
        if relevant_matches:
            logger.info(f"Found {len(relevant_matches)} matches with squad players")
            for match in relevant_matches:
                match_date = match['kickoff'].strftime('%a %b %d')
                match_time = match['kickoff'].strftime('%I:%M %p')
                tz_name = match['kickoff'].strftime('%Z')
                players = ', '.join(match['players'])
                fixture_info = f"(ID: {match.get('fixture_id', 'No API')})" 
                logger.info(f"  {match['home_team']} vs {match['away_team']} - {match_date} {match_time} {tz_name} {fixture_info} ({players})")
        
        return relevant_matches
    
    def _get_csv_matches(self, squad):
        """Parse matches from CSV opponent data"""
        csv_matches = []
        eastern_tz = pytz.timezone('US/Eastern')
        
        for player in squad:
            opponent_str = player.get('opponent', '')
            
            if not opponent_str or 'no match' in opponent_str.lower():
                continue
                
            # Parse opponent string like "@LEE Mon 3:00PM" or "BOU Fri 3:00PM"
            import re
            match = re.match(r'^(@)?(\w+)\s+(\w+)\s+(\d{1,2}:\d{2}(AM|PM))$', opponent_str)
            if not match:
                continue
                
            is_away, opponent, day_of_week, time_str = match.groups()[:4]
            
            # Map day names to numbers (0 = Sunday, 1 = Monday, etc.)
            day_map = {
                'Sun': 0, 'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Fri': 5, 'Sat': 6
            }
            
            target_day = day_map.get(day_of_week)
            if target_day is None:
                continue
                
            # Get current date and calculate target date
            now = datetime.now(eastern_tz)
            current_day = (now.weekday() + 1) % 7  # Convert Python weekday to Sunday=0 format
                
            # Calculate days until target day
            days_until = target_day - current_day
            if days_until < 0:
                days_until += 7  # Next week
            elif days_until == 0:
                # Same day - check if time has passed
                time_part = time_str.split('M')[0] + 'M'  # Get "3:00PM" part
                hour_min, period = time_part[:-2], time_part[-2:]
                hours, minutes = map(int, hour_min.split(':'))
                hour24 = hours + 12 if period == 'PM' and hours != 12 else (0 if period == 'AM' and hours == 12 else hours)
                
                target_time = now.replace(hour=hour24, minute=minutes, second=0, microsecond=0)
                if target_time <= now:
                    days_until = 7  # Next week same day
            
            # Create target datetime
            target_date = now + timedelta(days=days_until)
            time_part = time_str.split('M')[0] + 'M'  # Get "3:00PM" part
            hour_min, period = time_part[:-2], time_part[-2:]
            hours, minutes = map(int, hour_min.split(':'))
            hour24 = hours + 12 if period == 'PM' and hours != 12 else (0 if period == 'AM' and hours == 12 else hours)
            
            kickoff_time = target_date.replace(hour=hour24, minute=minutes, second=0, microsecond=0)
            
            # Convert opponent abbreviation to full team name
            from src.lineup_tracker.utils.team_mappings import TEAM_ABBREVIATIONS
            opponent_full = TEAM_ABBREVIATIONS.get(opponent, opponent)
            
            # Create match entry  
            home_team = player['team_name'] if not is_away else opponent_full
            away_team = opponent_full if not is_away else player['team_name']
            
            match_key = f"{home_team}_vs_{away_team}_{kickoff_time.isoformat()}"
            
            # Avoid duplicates
            existing_match = next((m for m in csv_matches if m.get('match_key') == match_key), None)
            if not existing_match:
                csv_matches.append({
                    'match_key': match_key,
                    'home_team': home_team,
                    'away_team': away_team,
                    'kickoff': kickoff_time,
                    'status': 'scheduled',
                    'players': [player['player_name']]
                })
            else:
                # Add player to existing match
                existing_match['players'].append(player['player_name'])
        
        return csv_matches
    
    def _find_matching_api_fixture(self, csv_match, api_fixtures, eastern_tz):
        """Find API fixture that matches CSV match data"""
        from src.lineup_tracker.utils.team_mappings import TEAM_NAME_VARIANTS
        
        def normalize_team_name(team_name):
            """Normalize team name using variants mapping"""
            # Check if it's a variant that should be normalized
            normalized = TEAM_NAME_VARIANTS.get(team_name, team_name)
            return normalized
        
        def teams_match(api_home, api_away, csv_home, csv_away):
            """Check if teams match with flexible name matching"""
            # Normalize API team names
            norm_api_home = normalize_team_name(api_home)
            norm_api_away = normalize_team_name(api_away)
            
            # Direct match
            if ((norm_api_home == csv_home and norm_api_away == csv_away) or 
                (norm_api_home == csv_away and norm_api_away == csv_home)):
                return True
            
            # Partial name matching (e.g., "Brighton & Hove Albion" matches "Brighton")
            def name_contains(full_name, partial_name):
                return partial_name.lower() in full_name.lower() or full_name.lower() in partial_name.lower()
            
            # Check all combinations with both original and normalized names
            teams_to_check = [
                (api_home, api_away, csv_home, csv_away),
                (norm_api_home, norm_api_away, csv_home, csv_away),
                (api_home, api_away, csv_away, csv_home),
                (norm_api_home, norm_api_away, csv_away, csv_home)
            ]
            
            for ah, aa, ch, ca in teams_to_check:
                if ((name_contains(ah, ch) and name_contains(aa, ca)) or
                    (ah == ch and aa == ca)):
                    return True
                    
            return False
        
        for fixture in api_fixtures:
            api_home = fixture['teams']['home']['name']
            api_away = fixture['teams']['away']['name']
            
            if teams_match(api_home, api_away, csv_match['home_team'], csv_match['away_team']):
                # Convert API time to Eastern to compare
                api_kickoff_utc = datetime.fromisoformat(fixture['fixture']['date'].replace('Z', '+00:00'))
                api_kickoff_eastern = api_kickoff_utc.astimezone(eastern_tz)
                
                # Check if times are within 6 hours (to handle timezone issues)
                time_diff = abs((api_kickoff_eastern - csv_match['kickoff']).total_seconds() / 3600)
                logger.info(f"🕐 Time comparison: API={api_kickoff_eastern} vs CSV={csv_match['kickoff']} (diff: {time_diff:.1f}h)")
                if time_diff <= 6:
                    logger.info(f"✅ Matched CSV '{csv_match['home_team']} vs {csv_match['away_team']}' to API '{api_home} vs {api_away}'")
                    return fixture
        
        return None
    
    def check_lineups_for_match(self, match):
        """Check lineups for a specific match and send notifications"""
        fixture_id = match.get('fixture_id')
        
        # Skip if no API fixture ID available
        if not fixture_id:
            logger.debug(f"Skipping {match['home_team']} vs {match['away_team']} - no API fixture ID")
            return
        
        # Skip if match already started or finished
        if match['status'] not in ['TBD', 'NS']:  # TBD = To Be Determined, NS = Not Started
            logger.debug(f"Skipping match {fixture_id} - status: {match['status']}")
            return
            
        # Check if we've already processed this match recently (avoid spam)
        last_check_key = f"{fixture_id}_lineup"
        now = datetime.now()
        
        if last_check_key in self.last_check:
            time_since_last = (now - self.last_check[last_check_key]).total_seconds() / 60
            if time_since_last < 5:  # Don't check same match lineup more than once per 5 minutes
                return
        
        # Get lineup data
        lineup_data = self.api.get_lineup(fixture_id)
        
        if not lineup_data:
            # Only send "lineups not available" warning once per match
            warning_key = f"{fixture_id}_warning"
            if warning_key not in self.last_check:
                self.notifier.send_warning(
                    f"⏳ Lineups not yet available for {match['home_team']} vs {match['away_team']}\n"
                    f"Kickoff: {match['kickoff'].strftime('%H:%M')}"
                )
                self.last_check[warning_key] = now
            return
            
        # Record successful check
        self.last_check[last_check_key] = now
        
        # Process lineups for each team
        for team_lineup in lineup_data:
            team_name = team_lineup['team']['name']
            starting_xi = [player['player']['name'] for player in team_lineup['startXI']]
            
            logger.info(f"Processing lineup for {team_name}: {len(starting_xi)} starters")
            self.check_team_lineup(team_name, starting_xi, match)
    
    def check_team_lineup(self, team_name, starting_xi, match):
        """Check specific team lineup against squad expectations"""
        squad = self.load_squad()
        team_players = [p for p in squad if p['team_name'] == team_name]
        
        if not team_players:
            return
        
        for player in team_players:
            player_name = player['player_name']
            expected_to_start = player['currently_starting']
            is_actually_starting = player_name in starting_xi
            
            # Generate notifications based on discrepancies
            if expected_to_start and not is_actually_starting:
                # Enhanced notification with Fantrax data
                avg_points = player.get('average_points', 'N/A')
                opponent = player.get('opponent', 'Unknown')
                
                message = (f"🚨 **{player_name}** BENCHED!\n\n"
                          f"**Team:** {team_name}\n"
                          f"**Position:** {player.get('position', 'Unknown')}\n"
                          f"**Match:** {match['home_team']} vs {match['away_team']}\n"
                          f"**Kickoff:** {match['kickoff'].strftime('%H:%M')}\n"
                          f"**Avg Points:** {avg_points} per game\n"
                          f"**Next Opponent:** {opponent}\n\n"
                          f"⚠️ You may want to update your lineup!")
                
                self.notifier.send_urgent_alert(message)
                logger.warning(f"URGENT: {player_name} benched for {team_name}")
                
            elif not expected_to_start and is_actually_starting:
                # Enhanced notification with Fantrax data
                avg_points = player.get('average_points', 'N/A')
                draft_pct = player.get('draft_percentage', 'N/A')
                
                message = (f"⚡ **{player_name}** STARTING!\n\n"
                          f"**Team:** {team_name}\n"
                          f"**Position:** {player.get('position', 'Unknown')}\n"
                          f"**Match:** {match['home_team']} vs {match['away_team']}\n"
                          f"**Kickoff:** {match['kickoff'].strftime('%H:%M')}\n"
                          f"**Avg Points:** {avg_points} per game\n"
                          f"**Draft %:** {draft_pct}%\n\n"
                          f"💡 Consider moving to starting XI!")
                
                self.notifier.send_important_alert(message)
                logger.info(f"IMPORTANT: {player_name} unexpectedly starting for {team_name}")
                
            else:
                # Only send confirmation for expected starters to avoid spam
                if expected_to_start:
                    message = f"✅ {player_name} confirmed starting for {team_name} vs {match['away_team'] if team_name == match['home_team'] else match['home_team']}"
                    self.notifier.send_info_update(message)
                    logger.info(f"Confirmed: {player_name} starting as expected")
    
    def run_monitoring_cycle(self):
        """Run one complete monitoring cycle"""
        logger.info("=" * 50)
        logger.info("Starting monitoring cycle")
        
        try:
            matches = self.get_matches_with_squad_players()
            
            if not matches:
                logger.info("No relevant matches today")
                return
                
            logger.info(f"Monitoring {len(matches)} matches with squad players")
            
            for match in matches:
                try:
                    logger.info(f"Checking match: {match['home_team']} vs {match['away_team']}")
                    self.check_lineups_for_match(match)
                except Exception as e:
                    logger.error(f"Error checking match {match['fixture_id']}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in monitoring cycle: {e}")
            self.notifier.send_warning(f"⚠️ Monitoring error: {str(e)}")
                
        logger.info("Monitoring cycle completed")
        logger.info("=" * 50)
    
    def get_squad_summary(self):
        """Get a summary of the current squad for testing/debugging"""
        squad = self.load_squad()
        
        if not squad:
            return "No squad loaded"
        
        teams = {}
        for player in squad:
            team = player['team_name']
            if team not in teams:
                teams[team] = {'starters': [], 'bench': []}
            
            if player['currently_starting']:
                teams[team]['starters'].append(player['player_name'])
            else:
                teams[team]['bench'].append(player['player_name'])
        
        summary = f"Roster Summary ({len(squad)} players):\n"
        for team, players in teams.items():
            summary += f"\n{team}:\n"
            summary += f"  Active ({len(players['starters'])}): {', '.join(players['starters'])}\n"
            summary += f"  Reserve ({len(players['bench'])}): {', '.join(players['bench'])}\n"
        
        return summary