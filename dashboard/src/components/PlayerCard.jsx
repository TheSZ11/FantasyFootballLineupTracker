const PlayerCard = ({ player }) => {
  const getTeamClass = (teamName) => {
    if (!teamName) return 'team-default'
    
    const teamMap = {
      'Arsenal': 'team-arsenal',
      'Aston Villa': 'team-aston-villa',
      'Bournemouth': 'team-bournemouth',
      'Brentford': 'team-brentford',
      'Brighton': 'team-brighton',
      'Brighton & Hove Albion': 'team-brighton',
      'Burnley': 'team-burnley',
      'Chelsea': 'team-chelsea',
      'Crystal Palace': 'team-crystal-palace',
      'Everton': 'team-everton',
      'Fulham': 'team-fulham',
      'Ipswich Town': 'team-ipswich',
      'Leicester City': 'team-leicester',
      'Leeds United': 'team-leeds',
      'Liverpool': 'team-liverpool',
      'Luton Town': 'team-luton',
      'Manchester City': 'team-manchester-city',
      'Manchester United': 'team-manchester-united',
      'Newcastle United': 'team-newcastle',
      'Nottingham Forest': 'team-nottingham-forest',
      'Sheffield United': 'team-sheffield-united',
      'Southampton': 'team-southampton',
      'Tottenham Hotspur': 'team-tottenham',
      'Watford': 'team-watford',
      'West Ham United': 'team-west-ham',
      'Wolverhampton Wanderers': 'team-wolverhampton',
      'Sunderland': 'team-sunderland',
      'Norwich City': 'team-norwich',
      'Cardiff City': 'team-cardiff'
    }
    
    return teamMap[teamName] || 'team-default'
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

  return (
    <div className={`player-card team-card ${getTeamClass(player.team)} status-${player.status_color} ${isUrgent() ? 'ring-2 ring-red-400' : ''}`}>
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
        <span className="font-medium">{player.team_abbreviation}</span>
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
        <div className="bg-gray-700 rounded p-2 mb-3 text-sm">
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
  )
}

export default PlayerCard
