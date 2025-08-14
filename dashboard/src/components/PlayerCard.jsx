import { getTeamLogoConfig } from '../utils/teamLogos';

const PlayerCard = ({ player }) => {
  const getTeamClass = (teamName) => {
    if (!teamName) return 'team-default'
    
    // Premier League 2025-26 teams only
    const teamMap = {
      'Arsenal': 'team-arsenal',
      'Aston Villa': 'team-aston-villa',
      'Bournemouth': 'team-bournemouth',
      'AFC Bournemouth': 'team-bournemouth',
      'Brentford': 'team-brentford',
      'Brighton': 'team-brighton',
      'Brighton & Hove Albion': 'team-brighton',
      'Burnley': 'team-burnley',
      'Chelsea': 'team-chelsea',
      'Crystal Palace': 'team-crystal-palace',
      'Everton': 'team-everton',
      'Fulham': 'team-fulham',
      'Leeds United': 'team-leeds',
      'Leeds': 'team-leeds',
      'Liverpool': 'team-liverpool',
      'Manchester City': 'team-manchester-city',
      'Manchester United': 'team-manchester-united',
      'Newcastle United': 'team-newcastle',
      'Newcastle': 'team-newcastle',
      'Nottingham Forest': 'team-nottingham-forest',
      'Sunderland': 'team-sunderland',
      'Tottenham Hotspur': 'team-tottenham',
      'Tottenham': 'team-tottenham',
      'Spurs': 'team-tottenham',
      'West Ham United': 'team-west-ham',
      'West Ham': 'team-west-ham',
      'Wolverhampton Wanderers': 'team-wolverhampton',
      'Wolves': 'team-wolverhampton'
    }
    
    return teamMap[teamName] || 'team-default'
  }

  // Get team logo for background
  const getTeamLogo = () => {
    const teamName = player.team?.name || player.team;
    const logoConfig = getTeamLogoConfig(teamName);
    return logoConfig.exists ? logoConfig.src : null;
  }

  const getStatusText = () => {
    switch (player.lineup_status) {
      case 'confirmed_starting':
        return player.is_expected_starter ? 'Starting ✓' : 'Unexpected Start!'
      case 'confirmed_bench':
        return player.is_expected_starter ? 'Benched ✗' : 'On Bench'
      case 'lineup_pending':
        return 'Lineup TBD'
      case 'no_match_today':
        return 'No Match Today'
      default:
        return 'Unknown'
    }
  }

  const getStatusIcon = () => {
    switch (player.lineup_status) {
      case 'confirmed_starting':
        return player.is_expected_starter ? '✅' : '⚡'
      case 'confirmed_bench':
        return player.is_expected_starter ? '🚨' : '⏸️'
      case 'lineup_pending':
        return '⏱️'
      case 'no_match_today':
        return '😴'
      default:
        return '❓'
    }
  }

  const formatKickoffTime = (kickoff) => {
    if (!kickoff) return null
    const date = new Date(kickoff)
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  const getPositionColor = (position) => {
    switch (position.toLowerCase()) {
      case 'goalkeeper':
        return 'bg-yellow-900/30 text-yellow-300 border border-yellow-700'
      case 'defender':
        return 'bg-blue-900/30 text-blue-300 border border-blue-700'
      case 'midfielder':
        return 'bg-green-900/30 text-green-300 border border-green-700'
      case 'forward':
        return 'bg-red-900/30 text-red-300 border border-red-700'
      default:
        return 'bg-gray-700 text-gray-300 border border-gray-600'
    }
  }

  const isUrgent = () => {
    return (player.lineup_status === 'confirmed_bench' && player.is_expected_starter) ||
           (player.lineup_status === 'confirmed_starting' && !player.is_expected_starter)
  }

  const teamLogo = getTeamLogo();
  
  return (
    <div className={`player-card team-card ${getTeamClass(player.team)} status-${player.status_color} ${isUrgent() ? 'ring-2 ring-red-400' : ''} relative overflow-hidden`}>
      {/* Logo background with reduced opacity */}
      {teamLogo && (
        <img 
          src={teamLogo}
          alt="Team logo background"
          className="absolute top-2 right-2 w-32 h-32 object-contain opacity-20 pointer-events-none z-0"
        />
      )}
      
      {/* Content overlay to ensure readability */}
      <div className="relative z-10">
        {/* Header with status icon and urgency */}
        <div className="flex justify-between items-start mb-3">
          <div className="flex items-center">
            <span className="text-2xl mr-2">{getStatusIcon()}</span>
            {isUrgent() && (
              <span className="bg-red-100 text-red-800 text-xs px-2 py-1 rounded-full font-medium">
                Alert!
              </span>
            )}
          </div>
          <span className={`px-2 py-1 rounded-full text-xs font-medium ${getPositionColor(player.position)}`}>
            {player.position}
          </span>
        </div>

        {/* Player Name */}
        <h3 className="font-bold text-lg text-gray-100 mb-1">{player.name}</h3>
        
        {/* Team */}
        <div className="flex items-center text-sm text-gray-300 mb-2">
          <div className="flex items-center">
            <TeamLogo teamName={player.team?.name || player.team} className="w-6 h-6 mr-2" />
            <span className="font-medium">{player.team?.abbreviation || player.team_abbreviation}</span>
          </div>
          {player.opponent && (
            <span className="ml-2">vs {player.opponent}</span>
          )}
        </div>

        {/* Status */}
        <div className={`text-sm font-medium mb-3 ${
          player.lineup_status === 'confirmed_starting' 
            ? player.is_expected_starter ? 'text-green-600' : 'text-orange-600'
            : player.lineup_status === 'confirmed_bench'
            ? player.is_expected_starter ? 'text-red-600' : 'text-gray-600'
            : player.lineup_status === 'lineup_pending'
            ? 'text-yellow-600'
            : 'text-gray-500'
        }`}>
          {getStatusText()}
        </div>

        {/* Match Info */}
        {player.match_info && (
          <div className="bg-gray-700/80 backdrop-blur-sm rounded p-2 mb-3 text-sm">
            <div className="font-medium text-gray-200">
              {player.match_info.home_team} vs {player.match_info.away_team}
            </div>
            <div className="text-gray-400">
              Kickoff: {formatKickoffTime(player.match_info.kickoff)}
            </div>
          </div>
        )}

        {/* Fantasy Stats */}
        <div className="border-t border-gray-600 pt-3 mt-3">
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <div className="text-gray-400">Avg Points</div>
              <div className="font-semibold text-gray-100">{player.average_points}</div>
            </div>
            <div>
              <div className="text-gray-400">Total Points</div>
              <div className="font-semibold text-gray-100">{player.fantasy_points}</div>
            </div>
          </div>
        </div>

        {/* Expected Status Indicator */}
        <div className="mt-2 flex items-center justify-between text-xs">
          <span className={`px-2 py-1 rounded ${
            player.is_expected_starter 
              ? 'bg-blue-900/30 text-blue-300 border border-blue-700' 
              : 'bg-gray-700 text-gray-300 border border-gray-600'
          }`}>
            {player.expected_status === 'Act' ? 'Expected Starter' : 'Bench Player'}
          </span>
          
          {/* Status color indicator */}
          <span className={`status-indicator ${player.status_color}`}></span>
        </div>
      </div>
    </div>
  )
}

// Team Logo Component
const TeamLogo = ({ teamName, className = "w-8 h-8" }) => {
  const logoConfig = getTeamLogoConfig(teamName);
  
  if (!logoConfig.exists) {
    // Fallback to team initial if no logo
    return (
      <div className={`${className} bg-gray-600 rounded-full flex items-center justify-center text-xs font-bold text-white`}>
        {teamName ? teamName.charAt(0).toUpperCase() : '?'}
      </div>
    );
  }

  return (
    <img 
      src={logoConfig.src}
      alt={logoConfig.alt}
      className={`${className} object-contain`}
      onError={(e) => {
        // Replace with fallback on error
        e.target.style.display = 'none';
        e.target.nextSibling.style.display = 'flex';
      }}
    />
  );
};

export default PlayerCard
