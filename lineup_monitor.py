import pandas as pd
import logging
from datetime import datetime, timedelta
from sofascore_client import FootballAPI
from notifications import NotificationHandler
from team_mappings import get_full_team_name

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
        """Get today's Premier League matches that include squad players"""
        fixtures = self.api.get_premier_league_fixtures()
        squad = self.load_squad()
        
        if not squad:
            return []
        
        squad_teams = {player['team_name'] for player in squad}
        relevant_matches = []
        
        for fixture in fixtures:
            home_team = fixture['teams']['home']['name']
            away_team = fixture['teams']['away']['name']
            
            if home_team in squad_teams or away_team in squad_teams:
                kickoff_time = datetime.fromisoformat(fixture['fixture']['date'].replace('Z', '+00:00'))
                
                relevant_matches.append({
                    'fixture_id': fixture['fixture']['id'],
                    'home_team': home_team,
                    'away_team': away_team,
                    'kickoff': kickoff_time,
                    'status': fixture['fixture']['status']['short'],
                    'elapsed': fixture['fixture']['status'].get('elapsed')
                })
        
        if relevant_matches:
            logger.info(f"Found {len(relevant_matches)} matches with squad players")
            for match in relevant_matches:
                logger.info(f"  {match['home_team']} vs {match['away_team']} - {match['kickoff'].strftime('%H:%M')}")
        
        return relevant_matches
    
    def check_lineups_for_match(self, match):
        """Check lineups for a specific match and send notifications"""
        fixture_id = match['fixture_id']
        
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