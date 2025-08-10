const PlayerCard = ({ player }) => {
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
        return 'bg-yellow-100 text-yellow-800'
      case 'defender':
        return 'bg-blue-100 text-blue-800'
      case 'midfielder':
        return 'bg-green-100 text-green-800'
      case 'forward':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const isUrgent = () => {
    return (player.lineup_status === 'confirmed_bench' && player.is_expected_starter) ||
           (player.lineup_status === 'confirmed_starting' && !player.is_expected_starter)
  }

  return (
    <div className={`player-card status-${player.status_color} ${isUrgent() ? 'ring-2 ring-red-400' : ''}`}>
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
      <h3 className="font-bold text-lg text-gray-900 mb-1">{player.name}</h3>
      
      {/* Team */}
      <div className="flex items-center text-sm text-gray-600 mb-2">
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
        <div className="bg-gray-50 rounded p-2 mb-3 text-sm">
          <div className="font-medium text-gray-700">
            {player.match_info.home_team} vs {player.match_info.away_team}
          </div>
          <div className="text-gray-500">
            Kickoff: {formatKickoffTime(player.match_info.kickoff)}
          </div>
        </div>
      )}

      {/* Fantasy Stats */}
      <div className="border-t pt-3 mt-3">
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <div className="text-gray-500">Avg Points</div>
            <div className="font-semibold text-gray-900">{player.average_points}</div>
          </div>
          <div>
            <div className="text-gray-500">Total Points</div>
            <div className="font-semibold text-gray-900">{player.fantasy_points}</div>
          </div>
        </div>
      </div>

      {/* Expected Status Indicator */}
      <div className="mt-2 flex items-center justify-between text-xs">
        <span className={`px-2 py-1 rounded ${
          player.is_expected_starter 
            ? 'bg-blue-100 text-blue-800' 
            : 'bg-gray-100 text-gray-600'
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
