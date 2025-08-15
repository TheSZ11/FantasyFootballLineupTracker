#!/usr/bin/env python3
"""
Quick squad-only export script to get real dashboard data working immediately.

This bypasses the API issues and just exports your actual roster data.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lineup_tracker.repositories.csv_squad_repository import CSVSquadRepository
from sofascore_wrapper.api import SofascoreAPI
from sofascore_wrapper.league import League
from sofascore_wrapper.match import Match


async def get_predicted_lineups():
    """Fetch predicted lineups from Sofascore API for Premier League matches."""
    predicted_lineups = {}
    
    try:
        print("🔮 Fetching predicted lineups from Sofascore...")
        api = SofascoreAPI()
        
        # Get Premier League
        premier_league = League(api, league_id=17)
        
        # Get upcoming fixtures
        fixtures = await premier_league.next_fixtures()
        
        if not fixtures:
            print("❌ No upcoming Premier League fixtures found")
            return predicted_lineups
        
        print(f"📅 Found {len(fixtures)} upcoming Premier League fixtures")
        
        # Process each fixture to get predicted lineups
        for fixture in fixtures[:5]:  # Limit to first 5 matches to avoid overloading
            try:
                match_id = fixture.get('id')
                home_team = fixture.get('homeTeam', {}).get('name', 'Unknown')
                away_team = fixture.get('awayTeam', {}).get('name', 'Unknown')
                
                print(f"  📋 Checking {home_team} vs {away_team}...")
                
                match = Match(api, match_id=match_id)
                
                # Get predicted lineups for both teams
                home_lineup = await match.lineups_home()
                away_lineup = await match.lineups_away()
                
                # Process home team lineup
                if home_lineup and home_lineup.get('starters'):
                    predicted_lineups[home_team] = {
                        'confirmed': home_lineup.get('confirmed', False),
                        'formation': home_lineup.get('formation', 'Unknown'),
                        'starters': [
                            player.get('player', {}).get('name', 'Unknown')
                            for player in home_lineup.get('starters', [])
                        ],
                        'substitutes': [
                            player.get('player', {}).get('name', 'Unknown') 
                            for player in home_lineup.get('substitutes', [])
                        ],
                        'missing_players': [
                            player.get('player', {}).get('name', 'Unknown')
                            for player in home_lineup.get('missing_players', [])
                        ]
                    }
                    print(f"    ✅ Got {home_team} lineup ({len(predicted_lineups[home_team]['starters'])} starters)")
                
                # Process away team lineup
                if away_lineup and away_lineup.get('starters'):
                    predicted_lineups[away_team] = {
                        'confirmed': away_lineup.get('confirmed', False),
                        'formation': away_lineup.get('formation', 'Unknown'),
                        'starters': [
                            player.get('player', {}).get('name', 'Unknown')
                            for player in away_lineup.get('starters', [])
                        ],
                        'substitutes': [
                            player.get('player', {}).get('name', 'Unknown') 
                            for player in away_lineup.get('substitutes', [])
                        ],
                        'missing_players': [
                            player.get('player', {}).get('name', 'Unknown')
                            for player in away_lineup.get('missing_players', [])
                        ]
                    }
                    print(f"    ✅ Got {away_team} lineup ({len(predicted_lineups[away_team]['starters'])} starters)")
                
            except Exception as e:
                print(f"    ❌ Error getting lineup for {home_team} vs {away_team}: {e}")
                continue
        
        print(f"🔮 Predicted lineups collected for {len(predicted_lineups)} teams")
        return predicted_lineups
        
    except Exception as e:
        print(f"❌ Error fetching predicted lineups: {e}")
        return predicted_lineups


def get_predicted_status(player_name, team_name, predicted_lineups):
    """Determine predicted lineup status for a player."""
    if team_name not in predicted_lineups:
        return 'no_prediction', False
    
    team_lineup = predicted_lineups[team_name]
    is_confirmed = team_lineup.get('confirmed', False)
    
    # Check if player is in starting lineup
    if player_name in team_lineup.get('starters', []):
        return 'predicted_starting' if not is_confirmed else 'confirmed_starting', is_confirmed
    
    # Check if player is on bench
    if player_name in team_lineup.get('substitutes', []):
        return 'predicted_bench' if not is_confirmed else 'confirmed_bench', is_confirmed
    
    # Check if player is missing/injured
    if player_name in team_lineup.get('missing_players', []):
        return 'predicted_unavailable', is_confirmed
    
    # Player not in any lineup - might be dropped or data incomplete
    return 'no_prediction', is_confirmed


async def export_squad_only():
    """Export just the squad data (your real roster) for the dashboard."""
    print("🚀 Exporting your REAL squad data...")
    
    try:
        # Load your actual roster
        squad_repo = CSVSquadRepository()
        squad = squad_repo.load_squad("my_roster.csv")
        
        print(f"✅ Loaded your squad: {squad.total_count} players ({squad.active_count} active, {squad.reserve_count} reserve)")
        
        # Get predicted lineups from Sofascore
        predicted_lineups = await get_predicted_lineups()
        
        # Create export directory
        export_dir = Path("dashboard/public/data")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        # Export squad data
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
                    'fantasy_points': player.fantasy_points,
                    'average_points': player.average_points,
                    'age': player.age,
                    'opponent': player.opponent,
                    'games_played': player.games_played,
                    'draft_percentage': player.draft_percentage
                }
                for player in squad.players
            ]
        }
        
        # Export lineup status with predicted lineup data
        player_status = []
        for player in squad.players:
            # Get predicted lineup status for this player
            predicted_status, is_confirmed = get_predicted_status(
                player.name, 
                player.team.name, 
                predicted_lineups
            )
            
            # Determine final lineup status
            if predicted_status in ['confirmed_starting', 'confirmed_bench']:
                lineup_status = predicted_status
                status_color = 'green' if predicted_status == 'confirmed_starting' else 'red'
            elif predicted_status in ['predicted_starting', 'predicted_bench']:
                lineup_status = predicted_status
                status_color = 'blue' if predicted_status == 'predicted_starting' else 'orange'
            elif predicted_status == 'predicted_unavailable':
                lineup_status = 'predicted_unavailable'
                status_color = 'gray'
            else:
                lineup_status = 'no_prediction'
                status_color = 'gray'
            
            player_info = {
                'id': player.id,
                'name': player.name,
                'team': player.team.name,
                'team_abbreviation': player.team.abbreviation,
                'position': player.position.value,
                'expected_status': player.status.value,
                'is_expected_starter': player.is_active,
                'lineup_status': lineup_status,
                'predicted_status': predicted_status,
                'is_confirmed': is_confirmed,
                'status_color': status_color,
                'fantasy_points': player.fantasy_points,
                'average_points': player.average_points,
                'opponent': player.opponent,
                'match_info': None,
                'prediction_info': {
                    'team_has_prediction': player.team.name in predicted_lineups,
                    'formation': predicted_lineups.get(player.team.name, {}).get('formation'),
                    'confirmed': is_confirmed
                } if player.team.name in predicted_lineups else None
            }
            player_status.append(player_info)
        
        # Calculate summary statistics including predictions
        predicted_starting = len([p for p in player_status if p['predicted_status'] == 'predicted_starting'])
        predicted_bench = len([p for p in player_status if p['predicted_status'] == 'predicted_bench'])
        confirmed_starting = len([p for p in player_status if p['predicted_status'] == 'confirmed_starting'])
        confirmed_bench = len([p for p in player_status if p['predicted_status'] == 'confirmed_bench'])
        predicted_unavailable = len([p for p in player_status if p['predicted_status'] == 'predicted_unavailable'])
        no_prediction = len([p for p in player_status if p['predicted_status'] == 'no_prediction'])
        players_with_predictions = len([p for p in player_status if p['prediction_info'] is not None])
        
        summary = {
            'total_players': len(player_status),
            'players_with_predictions': players_with_predictions,
            'predicted_starting': predicted_starting,
            'predicted_bench': predicted_bench,
            'confirmed_starting': confirmed_starting,
            'confirmed_bench': confirmed_bench,
            'predicted_unavailable': predicted_unavailable,
            'no_prediction': no_prediction,
            'teams_with_predictions': len(predicted_lineups)
        }
        
        lineup_data = {
            'generated_at': datetime.now().isoformat(),
            'date': datetime.now().date().isoformat(),
            'summary': summary,
            'relevant_matches': len(predicted_lineups) // 2,  # Matches (each has 2 teams)
            'players': player_status,
            'predicted_lineups': predicted_lineups
        }
        
        # Create basic status and metadata
        status_data = {
            'generated_at': datetime.now().isoformat(),
            'monitoring': {'is_running': False, 'last_check_time': None},
            'export_info': {
                'export_directory': str(export_dir),
                'note': 'Squad export with predicted lineups from Sofascore',
                'predicted_lineups_available': len(predicted_lineups) > 0,
                'teams_with_predictions': list(predicted_lineups.keys())
            }
        }
        
        metadata = {
            'generated_at': datetime.now().isoformat(),
            'format_version': '1.0',
            'dashboard_version': '1.0.0',
            'data_files': {
                'squad': 'squad.json',
                'lineup_status': 'lineup_status.json',
                'status': 'status.json'
            },
            'refresh_info': {
                'last_refresh': datetime.now().isoformat(),
                'refresh_interval_seconds': 300,
                'next_recommended_refresh': datetime.now().isoformat()
            }
        }
        
        # Write files
        files_written = {}
        
        with open(export_dir / "squad.json", 'w', encoding='utf-8') as f:
            json.dump(squad_data, f, indent=2, ensure_ascii=False)
        files_written['squad'] = str(export_dir / "squad.json")
        
        with open(export_dir / "lineup_status.json", 'w', encoding='utf-8') as f:
            json.dump(lineup_data, f, indent=2, ensure_ascii=False)
        files_written['lineup_status'] = str(export_dir / "lineup_status.json")
        
        with open(export_dir / "status.json", 'w', encoding='utf-8') as f:
            json.dump(status_data, f, indent=2, ensure_ascii=False)
        files_written['status'] = str(export_dir / "status.json")
        
        with open(export_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        files_written['metadata'] = str(export_dir / "metadata.json")
        
        print("✅ Export completed successfully!")
        print(f"📁 Export directory: {export_dir}")
        print("📄 Files exported:")
        for data_type, file_path in files_written.items():
            file_size = Path(file_path).stat().st_size
            print(f"   - {data_type}: {file_path} ({file_size} bytes)")
        
        print(f"\n🎮 Your REAL roster data is ready!")
        print(f"👥 Teams: {', '.join(squad.get_teams())}")
        print(f"📊 {squad.active_count} active players, {squad.reserve_count} reserves")
        
        # Show predicted lineup summary
        if predicted_lineups:
            print(f"\n🔮 PREDICTED LINEUPS AVAILABLE!")
            print(f"   📈 {summary['players_with_predictions']}/{summary['total_players']} players have prediction data")
            print(f"   🟦 {summary['predicted_starting']} predicted to start")
            print(f"   🟧 {summary['predicted_bench']} predicted on bench")
            if summary['confirmed_starting'] > 0:
                print(f"   🟢 {summary['confirmed_starting']} confirmed starting")
            if summary['confirmed_bench'] > 0:
                print(f"   🔴 {summary['confirmed_bench']} confirmed on bench")
            if summary['predicted_unavailable'] > 0:
                print(f"   ⚠️  {summary['predicted_unavailable']} predicted unavailable/injured")
            print(f"   🏆 Teams with lineups: {', '.join(predicted_lineups.keys())}")
        else:
            print(f"\n❌ No predicted lineups available yet")
        
        print(f"\n🌐 Start your dashboard: cd dashboard && npm run dev")
        
        return True
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(export_squad_only())
    sys.exit(0 if success else 1)
