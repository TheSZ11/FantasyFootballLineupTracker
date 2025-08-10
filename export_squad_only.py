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


async def export_squad_only():
    """Export just the squad data (your real roster) for the dashboard."""
    print("🚀 Exporting your REAL squad data...")
    
    try:
        # Load your actual roster
        squad_repo = CSVSquadRepository()
        squad = squad_repo.load_squad("my_roster.csv")
        
        print(f"✅ Loaded your squad: {squad.total_count} players ({squad.active_count} active, {squad.reserve_count} reserve)")
        
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
        
        # Export lineup status (your actual players with no match data for now)
        player_status = []
        for player in squad.players:
            player_info = {
                'id': player.id,
                'name': player.name,
                'team': player.team.name,
                'team_abbreviation': player.team.abbreviation,
                'position': player.position.value,
                'expected_status': player.status.value,
                'is_expected_starter': player.is_active,
                'lineup_status': 'no_match_today',  # Since we're not fetching API data
                'status_color': 'gray',
                'fantasy_points': player.fantasy_points,
                'average_points': player.average_points,
                'opponent': player.opponent,
                'match_info': None
            }
            player_status.append(player_info)
        
        summary = {
            'total_players': len(player_status),
            'players_with_matches_today': 0,  # Will be populated when API works
            'confirmed_starting': 0,
            'confirmed_bench': 0,
            'lineup_pending': 0,
            'no_match_today': len(player_status)
        }
        
        lineup_data = {
            'generated_at': datetime.now().isoformat(),
            'date': datetime.now().date().isoformat(),
            'summary': summary,
            'relevant_matches': 0,
            'players': player_status
        }
        
        # Create basic status and metadata
        status_data = {
            'generated_at': datetime.now().isoformat(),
            'monitoring': {'is_running': False, 'last_check_time': None},
            'export_info': {
                'export_directory': str(export_dir),
                'note': 'Squad-only export - API integration pending'
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
