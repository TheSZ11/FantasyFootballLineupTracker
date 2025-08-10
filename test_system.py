#!/usr/bin/env python3
"""
LineupTracker System Test Script

This script tests all components of your LineupTracker setup to ensure everything
is working correctly before you start monitoring.

Usage:
    python test_system.py
    python test_system.py --verbose
    python test_system.py --component notifications
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from typing import List, Tuple, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
    
    from src.lineup_tracker.config.app_config import AppConfig
    from src.lineup_tracker.container import Container
    from src.lineup_tracker.domain.models import Player, Team, Position, PlayerStatus
    from src.lineup_tracker.domain.enums import AlertUrgency
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


class Colors:
    """Terminal colors for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class TestResult:
    """Represents the result of a test."""
    
    def __init__(self, name: str, passed: bool, message: str, details: Optional[str] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details


class SystemTester:
    """Main system testing class."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[TestResult] = []
        self.config: Optional[AppConfig] = None
        self.container: Optional[Container] = None
    
    def print_header(self):
        """Print test header."""
        print(f"{Colors.BOLD}{Colors.CYAN}=" * 60)
        print("🧪 LineupTracker System Test")
        print("=" * 60 + Colors.END)
        print()
        print("This script will test all components of your LineupTracker setup.")
        print("Each test will show ✅ for pass or ❌ for fail with details.")
        print()
    
    def print_result(self, result: TestResult):
        """Print a test result."""
        status = f"{Colors.GREEN}✅{Colors.END}" if result.passed else f"{Colors.RED}❌{Colors.END}"
        print(f"{status} {result.name}: {result.message}")
        
        if not result.passed or (self.verbose and result.details):
            if result.details:
                print(f"   {Colors.YELLOW}Details: {result.details}{Colors.END}")
    
    def add_result(self, name: str, passed: bool, message: str, details: Optional[str] = None):
        """Add a test result."""
        result = TestResult(name, passed, message, details)
        self.results.append(result)
        self.print_result(result)
    
    def test_dependencies(self) -> bool:
        """Test if all required dependencies are available."""
        print(f"{Colors.BOLD}📦 Testing Dependencies{Colors.END}")
        
        if not IMPORTS_AVAILABLE:
            self.add_result(
                "Import Test", 
                False, 
                "Failed to import required modules",
                f"Error: {IMPORT_ERROR}. Run 'pip install -r requirements.txt'"
            )
            return False
        
        # Test individual dependencies
        dependencies = [
            ('pandas', 'pandas'),
            ('requests', 'requests'),
            ('discord_webhook', 'discord-webhook'),
            ('sofascore_wrapper', 'sofascore-wrapper'),
            ('schedule', 'schedule'),
            ('dotenv', 'python-dotenv'),
        ]
        
        all_good = True
        for module, package in dependencies:
            try:
                __import__(module.replace('-', '_'))
                self.add_result(f"Dependency: {package}", True, "Available")
            except ImportError:
                self.add_result(
                    f"Dependency: {package}", 
                    False, 
                    "Missing",
                    f"Install with: pip install {package}"
                )
                all_good = False
        
        print()
        return all_good
    
    def test_configuration(self) -> bool:
        """Test configuration loading and validation."""
        print(f"{Colors.BOLD}⚙️ Testing Configuration{Colors.END}")
        
        # Test .env file exists
        env_path = Path(".env")
        if not env_path.exists():
            self.add_result(
                "Environment File",
                False,
                ".env file not found",
                "Copy env.example to .env and configure it"
            )
            return False
        
        self.add_result("Environment File", True, ".env file found")
        
        # Test configuration loading
        try:
            self.config = AppConfig.from_env()
            self.add_result("Configuration Loading", True, "Successfully loaded configuration")
        except Exception as e:
            self.add_result(
                "Configuration Loading",
                False,
                "Failed to load configuration",
                str(e)
            )
            return False
        
        # Test runtime requirements
        issues = self.config.validate_runtime_requirements()
        if issues:
            for issue in issues:
                self.add_result("Runtime Validation", False, issue)
            return False
        else:
            self.add_result("Runtime Validation", True, "All runtime requirements met")
        
        # Test notification configuration
        if not self.config.notification_settings.discord_enabled and not self.config.notification_settings.email_enabled:
            self.add_result(
                "Notification Setup",
                False,
                "No notification providers enabled",
                "Enable Discord or Email notifications in .env"
            )
        else:
            enabled = []
            if self.config.notification_settings.discord_enabled:
                enabled.append("Discord")
            if self.config.notification_settings.email_enabled:
                enabled.append("Email")
            
            self.add_result(
                "Notification Setup",
                True,
                f"Notifications enabled: {', '.join(enabled)}"
            )
        
        print()
        return True
    
    def test_squad_file(self) -> bool:
        """Test squad file loading."""
        print(f"{Colors.BOLD}📋 Testing Squad File{Colors.END}")
        
        if not self.config:
            self.add_result("Squad File", False, "Configuration not loaded")
            return False
        
        squad_path = Path(self.config.monitoring_settings.squad_file_path)
        
        # Test file exists
        if not squad_path.exists():
            self.add_result(
                "Squad File Exists",
                False,
                f"Squad file not found: {squad_path}",
                "Create your squad file or copy from examples/"
            )
            return False
        
        self.add_result("Squad File Exists", True, f"Found: {squad_path}")
        
        # Test file loading
        try:
            self.container = Container(self.config)
            squad_repo = self.container.squad_repository
            squad = squad_repo.load_squad(str(squad_path))
            
            player_count = len(squad.players)
            active_count = len(squad.active_players)
            reserve_count = len(squad.reserve_players)
            
            self.add_result(
                "Squad Loading",
                True,
                f"Loaded {player_count} players ({active_count} active, {reserve_count} reserve)"
            )
            
            # Test squad composition
            if player_count == 0:
                self.add_result("Squad Composition", False, "No players found in squad file")
                return False
            elif active_count == 0:
                self.add_result(
                    "Squad Composition",
                    False,
                    "No active players found",
                    "Set some players' status to 'Act' or currently_starting to true"
                )
            else:
                self.add_result("Squad Composition", True, f"{active_count} players set as starters")
            
            # Show team breakdown if verbose
            if self.verbose and squad.players:
                teams = {}
                for player in squad.players:
                    team = player.team.name
                    if team not in teams:
                        teams[team] = {'active': 0, 'reserve': 0}
                    if player.status == PlayerStatus.ACTIVE:
                        teams[team]['active'] += 1
                    else:
                        teams[team]['reserve'] += 1
                
                team_details = []
                for team, counts in teams.items():
                    team_details.append(f"{team}: {counts['active']}A/{counts['reserve']}R")
                
                self.add_result(
                    "Team Breakdown",
                    True,
                    f"{len(teams)} teams",
                    ", ".join(team_details)
                )
            
        except Exception as e:
            self.add_result(
                "Squad Loading",
                False,
                "Failed to load squad file",
                str(e)
            )
            return False
        
        print()
        return True
    
    async def test_api_connection(self) -> bool:
        """Test API connection."""
        print(f"{Colors.BOLD}📡 Testing API Connection{Colors.END}")
        
        if not self.container:
            self.add_result("API Connection", False, "Container not initialized")
            return False
        
        try:
            football_api = self.container.football_api
            
            # Test basic connection
            connection_ok = await football_api.test_connection()
            if connection_ok:
                self.add_result("API Connection", True, "Successfully connected to Sofascore API")
            else:
                self.add_result("API Connection", False, "Failed to connect to API")
                return False
            
            # Test fixture retrieval
            fixtures = await football_api.get_fixtures()
            if fixtures is not None:
                self.add_result(
                    "Fixture Retrieval",
                    True,
                    f"Retrieved {len(fixtures)} fixtures"
                )
                
                if self.verbose and fixtures:
                    # Show upcoming matches
                    upcoming = [f for f in fixtures if hasattr(f, 'kickoff')][:3]
                    if upcoming:
                        match_details = []
                        for match in upcoming:
                            match_details.append(f"{match.home_team.name} vs {match.away_team.name}")
                        self.add_result(
                            "Upcoming Matches",
                            True,
                            f"Next {len(match_details)} matches",
                            "; ".join(match_details)
                        )
            else:
                self.add_result("Fixture Retrieval", False, "Failed to retrieve fixtures")
                return False
            
        except Exception as e:
            self.add_result(
                "API Connection",
                False,
                "API test failed",
                str(e)
            )
            return False
        
        print()
        return True
    
    async def test_notifications(self) -> bool:
        """Test notification systems."""
        print(f"{Colors.BOLD}📢 Testing Notifications{Colors.END}")
        
        if not self.container:
            self.add_result("Notifications", False, "Container not initialized")
            return False
        
        try:
            notification_service = self.container.notification_service
            
            # Test Discord notifications
            if self.config.notification_settings.discord_enabled:
                try:
                    discord_provider = self.container.discord_provider
                    test_result = await discord_provider.test_connection()
                    
                    if test_result:
                        self.add_result("Discord Notifications", True, "Discord webhook working")
                    else:
                        self.add_result("Discord Notifications", False, "Discord webhook test failed")
                except Exception as e:
                    self.add_result(
                        "Discord Notifications",
                        False,
                        "Discord test failed",
                        str(e)
                    )
            else:
                self.add_result("Discord Notifications", True, "Disabled (not configured)")
            
            # Test Email notifications
            if self.config.notification_settings.email_enabled:
                try:
                    email_provider = self.container.email_provider
                    test_result = await email_provider.test_connection()
                    
                    if test_result:
                        self.add_result("Email Notifications", True, "Email configuration working")
                    else:
                        self.add_result("Email Notifications", False, "Email test failed")
                except Exception as e:
                    self.add_result(
                        "Email Notifications",
                        False,
                        "Email test failed",
                        str(e)
                    )
            else:
                self.add_result("Email Notifications", True, "Disabled (not configured)")
            
        except Exception as e:
            self.add_result(
                "Notifications",
                False,
                "Notification test failed",
                str(e)
            )
            return False
        
        print()
        return True
    
    async def test_full_monitoring_cycle(self) -> bool:
        """Test a complete monitoring cycle."""
        print(f"{Colors.BOLD}🔄 Testing Full Monitoring Cycle{Colors.END}")
        
        if not self.container:
            self.add_result("Monitoring Cycle", False, "Container not initialized")
            return False
        
        try:
            monitoring_service = self.container.lineup_monitoring_service
            
            # Test monitoring cycle (dry run)
            self.add_result("Monitoring Service", True, "Service initialized successfully")
            
            # Note: We don't actually run a full cycle to avoid spam notifications
            # Instead, we verify all components are ready
            components = [
                ("Football API", self.container.football_api),
                ("Squad Repository", self.container.squad_repository),
                ("Notification Service", self.container.notification_service),
            ]
            
            all_ready = True
            for name, component in components:
                if component is not None:
                    self.add_result(f"{name} Ready", True, "Component initialized")
                else:
                    self.add_result(f"{name} Ready", False, "Component not available")
                    all_ready = False
            
            if all_ready:
                self.add_result(
                    "System Readiness",
                    True,
                    "All components ready for monitoring"
                )
            else:
                self.add_result("System Readiness", False, "Some components not ready")
                return False
            
        except Exception as e:
            self.add_result(
                "Monitoring Cycle",
                False,
                "Failed to initialize monitoring",
                str(e)
            )
            return False
        
        print()
        return True
    
    def print_summary(self):
        """Print test summary."""
        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)
        failed = total - passed
        
        print(f"{Colors.BOLD}📊 Test Summary{Colors.END}")
        print("=" * 40)
        
        if failed == 0:
            print(f"{Colors.GREEN}🎉 All tests passed! ({passed}/{total}){Colors.END}")
            print()
            print("Your LineupTracker setup is ready! 🚀")
            print("You can now run: python main.py")
        else:
            print(f"{Colors.RED}❌ {failed} test(s) failed out of {total}{Colors.END}")
            print(f"{Colors.GREEN}✅ {passed} test(s) passed{Colors.END}")
            print()
            print("Please fix the issues above before running the main application.")
            print("Run this test again after making changes.")
        
        print()
        print("💡 Tips:")
        print("• Run 'python setup.py' for guided configuration")
        print("• Check the README.md for detailed setup instructions")
        print("• Use --verbose flag for more detailed output")
    
    async def run_tests(self, component: Optional[str] = None):
        """Run all tests or specific component tests."""
        self.print_header()
        
        if component is None:
            # Run all tests
            if not self.test_dependencies():
                self.print_summary()
                return
            
            if not self.test_configuration():
                self.print_summary()
                return
            
            if not self.test_squad_file():
                self.print_summary()
                return
            
            if not await self.test_api_connection():
                self.print_summary()
                return
            
            if not await self.test_notifications():
                self.print_summary()
                return
            
            await self.test_full_monitoring_cycle()
        
        else:
            # Run specific component tests
            if component == "dependencies":
                self.test_dependencies()
            elif component == "config":
                self.test_configuration()
            elif component == "squad":
                self.test_squad_file()
            elif component == "api":
                await self.test_api_connection()
            elif component == "notifications":
                await self.test_notifications()
            elif component == "monitoring":
                await self.test_full_monitoring_cycle()
            else:
                print(f"{Colors.RED}Unknown component: {component}{Colors.END}")
                print("Available components: dependencies, config, squad, api, notifications, monitoring")
                return
        
        self.print_summary()


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test LineupTracker system components")
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--component", "-c",
        choices=["dependencies", "config", "squad", "api", "notifications", "monitoring"],
        help="Test only specific component"
    )
    
    args = parser.parse_args()
    
    tester = SystemTester(verbose=args.verbose)
    await tester.run_tests(args.component)


if __name__ == "__main__":
    asyncio.run(main())
