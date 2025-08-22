const MatchOverview = ({ matches }) => {
  const getMatchDisplay = (match) => {
    // Get the team name from the first player in the match
    const playerTeam = match.players[0]?.team || 'Team'
    
    if (match.isAway) {
      return `${playerTeam} @ ${match.opponent}`
    } else {
      return `${match.opponent} vs ${playerTeam}`
    }
  }
  const formatKickoffTime = (kickoff) => {
    return kickoff.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit'
    })
  }

  const getTimeUntilKickoff = (kickoff) => {
    const now = new Date()
    const diffMs = kickoff - now
    const diffMins = Math.floor(diffMs / (1000 * 60))
    const diffHours = Math.floor(diffMins / 60)
    
    if (diffMs < 0) return 'Started'
    if (diffMins < 60) return `${diffMins}m`
    if (diffHours < 24) return `${diffHours}h ${diffMins % 60}m`
    return `${Math.floor(diffHours / 24)}d`
  }

  const getPlayersByStatus = (players) => {
    const confirmed = players.filter(p => 
      p.lineup_status === 'confirmed_starting' || p.lineup_status === 'confirmed_bench'
    ).length
    const predicted = players.filter(p => 
      p.lineup_status === 'predicted_starting' || p.lineup_status === 'predicted_bench'
    ).length
    
    return { confirmed, predicted }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {matches.map(match => {
        const timeUntil = getTimeUntilKickoff(match.kickoff)
        const { confirmed, predicted } = getPlayersByStatus(match.players)
        
        return (
          <div key={match.id} className="bg-gray-800 rounded-lg shadow-md p-4 border border-gray-700">
            {/* Match Header */}
            <div className="flex justify-between items-center mb-3">
              <div className="text-lg font-semibold text-gray-100">
                {getMatchDisplay(match)}
              </div>
              <div className={`px-2 py-1 rounded text-sm font-medium ${
                timeUntil === 'Started' 
                  ? 'bg-red-900/30 text-red-300 border border-red-700'
                  : 'bg-blue-900/30 text-blue-300 border border-blue-700'
              }`}>
                {timeUntil === 'Started' ? 'Live' : timeUntil}
              </div>
            </div>

            {/* Kickoff Time */}
            <div className="text-sm text-gray-300 mb-3">
              Kickoff: {formatKickoffTime(match.kickoff)}
            </div>

            {/* Your Players */}
            <div className="border-t border-gray-600 pt-3">
              <div className="text-sm font-medium text-gray-200 mb-2">
                Your Players ({match.players.length})
              </div>
              
              {/* Player Names */}
              <div className="space-y-1 mb-3">
                {match.players.map(player => (
                  <div key={player.id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-100">{player.name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      player.lineup_status === 'confirmed_starting'
                        ? 'bg-green-900/30 text-green-300 border border-green-700'
                        : player.lineup_status === 'confirmed_bench'
                        ? 'bg-red-900/30 text-red-300 border border-red-700'
                        : 'bg-yellow-900/30 text-yellow-300 border border-yellow-700'
                    }`}>
                      {player.lineup_status === 'confirmed_starting' ? 'Starting' :
                       player.lineup_status === 'confirmed_bench' ? 'Bench' : 'TBD'}
                    </span>
                  </div>
                ))}
              </div>

              {/* Status Summary */}
              <div className="flex justify-between text-xs text-gray-400 border-t border-gray-600 pt-2">
                <span>Confirmed: {confirmed}</span>
                <span>Predicted: {predicted}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default MatchOverview
