#!/usr/bin/env python3
"""
Simple test script for dashboard export functionality.

Tests the dashboard export service with mock data to verify JSON generation works.
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from lineup_tracker.services.dashboard_export_service import DashboardExportService
from lineup_tracker.domain.models import Player, Team, Squad, Match
from lineup_tracker.domain.enums import Position, PlayerStatus, MatchStatus


def create_mock_squad():
    """Create a mock squad for testing."""
    # Create teams
    liverpool = Team("Liverpool", "LIV")
    man_city = Team("Manchester City", "MCI")
    brighton = Team("Brighton", "BHA")
    everton = Team("Everton", "EVE")
    
    # Create players
    players = [
        Player(
            id="salah1",
            name="Mohamed Salah",
            team=liverpool,
            position=Position.FORWARD,
            status=PlayerStatus.ACTIVE,
            fantasy_points=571.75,
            average_points=18.44,
            age=33,
            opponent="BOU",
            games_played=31
        ),
        Player(
            id="mitoma1",
            name="Kaoru Mitoma",
            team=brighton,
            position=Position.MIDFIELDER,
            status=PlayerStatus.ACTIVE,
            fantasy_points=332.0,
            average_points=13.83,
            age=28,
            games_played=24
        ),
        Player(
            id="pickford1",
            name="Jordan Pickford",
            team=everton,
            position=Position.GOALKEEPER,
            status=PlayerStatus.ACTIVE,
            fantasy_points=274.25,
            average_points=7.22,
            age=31,
            games_played=38
        ),
        Player(
            id="haaland1",
            name="Erling Haaland",
            team=man_city,
            position=Position.FORWARD,
            status=PlayerStatus.RESERVE,
            fantasy_points=420.0,
            average_points=15.5,
            age=24,
            games_played=25
        )
    ]
    
    return Squad(players=players, last_updated=datetime.now())


def create_mock_matches():
    """Create mock matches for testing."""
    liverpool = Team("Liverpool", "LIV")
    bournemouth = Team("Bournemouth", "BOU")
    brighton = Team("Brighton", "BHA")
    fulham = Team("Fulham", "FUL")
    
    return [
        Match(
            id="match1",
            home_team=liverpool,
            away_team=bournemouth,
            kickoff=datetime.now() + timedelta(hours=2),
            status=MatchStatus.NOT_STARTED
        ),
        Match(
            id="match2",
            home_team=brighton,
            away_team=fulham,
            kickoff=datetime.now() + timedelta(hours=1),
            status=MatchStatus.NOT_STARTED
        )
    ]


class MockSquadRepository:
    """Mock squad repository for testing."""
    
    def __init__(self, squad):
        self.squad = squad
    
    async def load_squad(self):
        return self.squad


class MockFootballAPI:
    """Mock football API for testing."""
    
    def __init__(self, matches):
        self.matches = matches
    
    async def get_matches_for_date(self, date):
        return self.matches
    
    async def get_lineups(self, match_id):
        # Return empty lineups for testing
        return []


async def test_dashboard_export():
    """Test the dashboard export functionality."""
    print("🧪 Testing Dashboard Export Service")
    
    # Create test directory
    test_dir = "test_dashboard_export"
    if os.path.exists(test_dir):
        import shutil
        shutil.rmtree(test_dir)
    
    try:
        # Create mock data
        squad = create_mock_squad()
        matches = create_mock_matches()
        
        # Create mock dependencies
        squad_repo = MockSquadRepository(squad)
        football_api = MockFootballAPI(matches)
        
        # Create export service
        export_service = DashboardExportService(
            export_directory=test_dir,
            football_api=football_api,
            squad_repository=squad_repo
        )
        
        print(f"📁 Export directory: {export_service.get_export_directory()}")
        
        # Test individual exports
        print("\n📊 Testing squad data export...")
        squad_file = await export_service.export_squad_data()
        print(f"✅ Squad data exported to: {squad_file}")
        
        print("\n⚽ Testing matches export...")
        matches_file = await export_service.export_todays_matches()
        print(f"✅ Matches data exported to: {matches_file}")
        
        print("\n🎯 Testing lineup status export...")
        lineup_file = await export_service.export_lineup_status()
        print(f"✅ Lineup status exported to: {lineup_file}")
        
        print("\n📈 Testing system status export...")
        status_file = await export_service.export_system_status({"test": "data"})
        print(f"✅ System status exported to: {status_file}")
        
        print("\n📋 Testing metadata export...")
        meta_file = await export_service.export_metadata()
        print(f"✅ Metadata exported to: {meta_file}")
        
        print("\n🎉 Testing full export...")
        exported_files = await export_service.export_all_data({"is_running": True})
        
        print("\n✅ Full export completed successfully!")
        print("📄 Generated files:")
        for data_type, file_path in exported_files.items():
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                print(f"   - {data_type}: {file_path} ({file_size} bytes)")
            else:
                print(f"   - {data_type}: {file_path} (NOT FOUND)")
        
        # Show content of one file as example
        print("\n📖 Sample content (lineup_status.json):")
        if os.path.exists(lineup_file):
            with open(lineup_file, 'r') as f:
                import json
                data = json.load(f)
                print(f"   - Generated at: {data['generated_at']}")
                print(f"   - Total players: {data['summary']['total_players']}")
                print(f"   - Players with matches today: {data['summary']['players_with_matches_today']}")
                print(f"   - First player: {data['players'][0]['name']} ({data['players'][0]['team']}) - {data['players'][0]['status_color']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Dashboard Export Test")
    success = asyncio.run(test_dashboard_export())
    
    if success:
        print("\n🎉 All tests passed! Dashboard export functionality is working.")
        print("📁 Check the 'test_dashboard_export' directory for generated files.")
    else:
        print("\n❌ Tests failed. Check the error messages above.")
        sys.exit(1)
