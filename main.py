import os
import logging
import schedule
import time
from datetime import datetime, timedelta, timezone
import pytz
from dotenv import load_dotenv
from lineup_monitor import LineupMonitor

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('lineup_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class SmartScheduler:
    """Intelligent scheduler that only monitors when matches are approaching"""
    
    def __init__(self):
        self.monitor = LineupMonitor()
        self.monitoring_active = False
        
    def check_if_monitoring_needed(self):
        """Check if any matches need monitoring in the next 60 minutes"""
        matches = self.monitor.get_matches_with_squad_players()
        # Use Eastern timezone consistently 
        eastern_tz = pytz.timezone('US/Eastern')
        now = datetime.now(eastern_tz)
        
        logger.info(f"DEBUG: Current Eastern time: {now}")
        
        imminent_matches = []
        for match in matches:
            time_until_kickoff = (match['kickoff'] - now).total_seconds() / 60
            logger.info(f"DEBUG: {match['home_team']} vs {match['away_team']}")
            logger.info(f"DEBUG: Match kickoff: {match['kickoff']}")
            logger.info(f"DEBUG: Time until kickoff: {time_until_kickoff:.1f} minutes")
            
            # Start monitoring 60 minutes before kickoff
            if 0 <= time_until_kickoff <= 60:
                imminent_matches.append((match, time_until_kickoff))
                logger.info(f"DEBUG: MATCH WITHIN 60 MINUTES - SHOULD START MONITORING")
        
        if imminent_matches:
            if not self.monitoring_active:
                for match, time_until in imminent_matches:
                    logger.info(f"Starting active monitoring - {match['home_team']} vs {match['away_team']} in {time_until:.0f} minutes")
                self.start_active_monitoring()
            return True
                
        # Stop monitoring if no matches in next 60 minutes
        if self.monitoring_active:
            logger.info("No imminent matches - stopping active monitoring")
            self.stop_active_monitoring()
            
        return False
    
    def start_active_monitoring(self):
        """Start frequent monitoring for imminent matches"""
        self.monitoring_active = True
        
        # Clear any existing schedule
        schedule.clear()
        
        # Monitor every 15 minutes during active period
        schedule.every(15).minutes.do(self.run_cycle_with_frequency_adjustment)
        
        logger.info("Active monitoring started - checking every 15 minutes")
        
    def stop_active_monitoring(self):
        """Stop active monitoring and return to daily checks"""
        self.monitoring_active = False
        schedule.clear()
        
        # Check once per day at 9 AM for upcoming matches
        schedule.every().day.at("09:00").do(self.check_if_monitoring_needed)
        
        logger.info("Active monitoring stopped - daily checks only")
    
    def run_cycle_with_frequency_adjustment(self):
        """Run monitoring cycle with dynamic frequency based on kickoff times"""
        matches = self.monitor.get_matches_with_squad_players()
        # Use Eastern timezone consistently
        eastern_tz = pytz.timezone('US/Eastern')
        now = datetime.now(eastern_tz)
        
        next_check_interval = 15  # Default 15 minutes
        
        for match in matches:
            time_until_kickoff = (match['kickoff'] - now).total_seconds() / 60
            
            if time_until_kickoff <= 5:
                next_check_interval = 1  # Check every minute in final 5 minutes
                break
            elif time_until_kickoff <= 15:
                next_check_interval = 5  # Check every 5 minutes in final 15 minutes
                break
        
        # Run the actual monitoring
        logger.info("⚡ Running lineup monitoring cycle...")
        self.monitor.run_monitoring_cycle()
        
        # Reschedule next check based on calculated interval
        if next_check_interval != 15:
            schedule.clear()
            if next_check_interval == 1:
                schedule.every(1).minutes.do(self.run_cycle_with_frequency_adjustment)
                logger.info("Switched to 1-minute monitoring (final 5 minutes)")
            elif next_check_interval == 5:
                schedule.every(5).minutes.do(self.run_cycle_with_frequency_adjustment)
                logger.info("Switched to 5-minute monitoring (final 15 minutes)")

def main():
    """Main application entry point"""
    logger.info("Starting Fantrax Lineup Monitor with Smart Scheduling")
    
    scheduler = SmartScheduler()
    
    # Test initial setup
    try:
        squad = scheduler.monitor.load_squad()
        if not squad:
            logger.error("No squad loaded - check my_squad.csv")
            return
            
        logger.info(f"Loaded {len(squad)} players")
        
        # Send startup notification
        scheduler.monitor.notifier.send_info_update("🚀 Fantrax Lineup Monitor started with smart scheduling!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        return
    
    # Start with daily checks
    scheduler.stop_active_monitoring()
    
    # Also do an immediate check
    scheduler.check_if_monitoring_needed()
    
    logger.info("Smart scheduler initialized - monitoring as needed")
    
    # Keep running
    try:
        while True:
            schedule.run_pending()
            time.sleep(30)  # Check every 30 seconds for scheduled tasks
            
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
        scheduler.monitor.notifier.send_info_update("📴 Fantrax Lineup Monitor stopped")

if __name__ == "__main__":
    main()