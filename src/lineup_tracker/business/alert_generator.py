"""
Alert generation business logic.

Creates well-formatted alerts from lineup discrepancies with rich context
including fantasy points, player stats, and match information.
"""

from typing import List, Dict, Any
from datetime import datetime
import logging

from ..domain.models import Alert, LineupDiscrepancy, Player, Match
from ..domain.enums import AlertType, AlertUrgency

logger = logging.getLogger(__name__)


class AlertGenerator:
    """
    Generates alerts from lineup discrepancies.
    
    Creates rich, contextual alerts with fantasy football data
    to help users make informed lineup decisions.
    """
    
    def __init__(self):
        self._alert_templates = self._initialize_alert_templates()
    
    def generate_alerts(self, discrepancies: List[LineupDiscrepancy]) -> List[Alert]:
        """
        Generate alerts from a list of lineup discrepancies.
        
        Args:
            discrepancies: List of lineup discrepancies to process
            
        Returns:
            List of Alert objects ready for notification
        """
        alerts = []
        
        logger.info(f"Generating alerts for {len(discrepancies)} discrepancies")
        
        for discrepancy in discrepancies:
            # Only generate alerts for actual discrepancies
            if discrepancy.discrepancy_type != AlertType.LINEUP_CONFIRMED:
                alert = self._create_alert_from_discrepancy(discrepancy)
                alerts.append(alert)
                logger.debug(f"Generated {discrepancy.discrepancy_type.value} alert for {discrepancy.player.name}")
            else:
                # For confirmations, we might want to send info updates
                # but with lower priority
                alert = self._create_confirmation_alert(discrepancy)
                alerts.append(alert)
        
        logger.info(f"Generated {len(alerts)} alerts")
        return alerts
    
    def _create_alert_from_discrepancy(self, discrepancy: LineupDiscrepancy) -> Alert:
        """Create an alert from a lineup discrepancy."""
        alert_type = discrepancy.discrepancy_type
        urgency = discrepancy.urgency
        
        message = self._format_alert_message(discrepancy)
        extra_context = self._build_extra_context(discrepancy)
        
        return Alert(
            player=discrepancy.player,
            match=discrepancy.match,
            alert_type=alert_type,
            urgency=urgency,
            message=message,
            extra_context=extra_context,
            timestamp=datetime.now()
        )
    
    def _create_confirmation_alert(self, discrepancy: LineupDiscrepancy) -> Alert:
        """Create a confirmation alert for expected lineups."""
        message = self._format_confirmation_message(discrepancy)
        
        return Alert(
            player=discrepancy.player,
            match=discrepancy.match,
            alert_type=AlertType.LINEUP_CONFIRMED,
            urgency=AlertUrgency.INFO,
            message=message,
            extra_context=self._build_extra_context(discrepancy),
            timestamp=datetime.now()
        )
    
    def _format_alert_message(self, discrepancy: LineupDiscrepancy) -> str:
        """Format the main alert message based on discrepancy type."""
        player = discrepancy.player
        match = discrepancy.match
        template_key = discrepancy.discrepancy_type.value
        
        template = self._alert_templates.get(template_key, self._alert_templates['default'])
        
        # Determine opponent team
        opponent_team = (
            match.away_team.name if player.team.name == match.home_team.name
            else match.home_team.name
        )
        
        # Format message using template
        message = template.format(
            player_name=player.name,
            team_name=player.team.name,
            position=player.position.value,
            home_team=match.home_team.name,
            away_team=match.away_team.name,
            opponent=opponent_team,
            kickoff_time=match.kickoff.strftime('%H:%M'),
            games_played=player.games_played or 'N/A',
            draft_percentage=player.draft_percentage or 'N/A'
        )
        
        return message
    
    def _format_confirmation_message(self, discrepancy: LineupDiscrepancy) -> str:
        """Format confirmation message for expected lineups."""
        player = discrepancy.player
        match = discrepancy.match
        
        if discrepancy.expected_starting and discrepancy.actually_starting:
            opponent = (
                match.away_team.name if player.team.name == match.home_team.name
                else match.home_team.name
            )
            return f"✅ {player.name} confirmed starting for {player.team.name} vs {opponent}"
        else:
            return f"✅ {player.name} lineup status as expected ({player.team.name})"
    
    def _build_extra_context(self, discrepancy: LineupDiscrepancy) -> Dict[str, Any]:
        """Build extra context data for the alert."""
        player = discrepancy.player
        match = discrepancy.match
        
        return {
            'player_id': player.id,
            'team_abbreviation': player.team.abbreviation,
            'match_id': match.id,
            'kickoff_timestamp': match.kickoff.isoformat(),
            'player_data': {
                'games_played': player.games_played,
                'age': player.age,
                'draft_percentage': player.draft_percentage,
                'opponent': player.opponent
            },
            'discrepancy_details': {
                'expected_starting': discrepancy.expected_starting,
                'actually_starting': discrepancy.actually_starting,
                'discrepancy_type': discrepancy.discrepancy_type.value
            }
        }
    
    def _initialize_alert_templates(self) -> Dict[str, str]:
        """Initialize message templates for different alert types."""
        return {
            'unexpected_benching': (
                "🚨 **{player_name}** BENCHED!\n\n"
                "**Team:** {team_name}\n"
                "**Position:** {position}\n"
                "**Match:** {home_team} vs {away_team}\n"
                "**Kickoff:** {kickoff_time}\n"
                "**Games Played:** {games_played}\n\n"
                "⚠️ You may want to update your lineup!"
            ),
            'unexpected_starting': (
                "⚡ **{player_name}** STARTING!\n\n"
                "**Team:** {team_name}\n"
                "**Position:** {position}\n"
                "**Match:** {home_team} vs {away_team}\n"
                "**Kickoff:** {kickoff_time}\n"
                "**Draft %:** {draft_percentage}%\n\n"
                "💡 Consider moving to starting XI!"
            ),
            'default': (
                "📋 **{player_name}** Lineup Update\n\n"
                "**Team:** {team_name}\n"
                "**Match:** {home_team} vs {away_team}\n"
                "**Kickoff:** {kickoff_time}\n"
            )
        }
    
    def filter_alerts_by_importance(self, alerts: List[Alert], min_urgency: AlertUrgency = AlertUrgency.INFO) -> List[Alert]:
        """
        Filter alerts by minimum urgency level.
        
        Args:
            alerts: List of alerts to filter
            min_urgency: Minimum urgency level to include
            
        Returns:
            Filtered list of alerts
        """
        urgency_order = {
            AlertUrgency.INFO: 0,
            AlertUrgency.WARNING: 1,
            AlertUrgency.IMPORTANT: 2,
            AlertUrgency.URGENT: 3
        }
        
        min_level = urgency_order[min_urgency]
        
        return [
            alert for alert in alerts
            if urgency_order[alert.urgency] >= min_level
        ]
    
    def group_alerts_by_team(self, alerts: List[Alert]) -> Dict[str, List[Alert]]:
        """Group alerts by team name for organized notifications."""
        grouped = {}
        
        for alert in alerts:
            team_name = alert.player.team.name
            if team_name not in grouped:
                grouped[team_name] = []
            grouped[team_name].append(alert)
        
        return grouped
    
    def get_alert_summary(self, alerts: List[Alert]) -> Dict[str, int]:
        """Get summary statistics for generated alerts."""
        summary = {
            'total_alerts': len(alerts),
            'urgent': 0,
            'important': 0,
            'info': 0,
            'warnings': 0,
            'benchings': 0,
            'unexpected_starts': 0,
            'confirmations': 0
        }
        
        for alert in alerts:
            # Count by urgency
            summary[alert.urgency.value] += 1
            
            # Count by type
            if alert.alert_type == AlertType.UNEXPECTED_BENCHING:
                summary['benchings'] += 1
            elif alert.alert_type == AlertType.UNEXPECTED_STARTING:
                summary['unexpected_starts'] += 1
            elif alert.alert_type == AlertType.LINEUP_CONFIRMED:
                summary['confirmations'] += 1
        
        return summary
