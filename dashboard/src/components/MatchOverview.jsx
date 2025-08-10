const MatchOverview = ({ matches }) => {
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
    const pending = players.filter(p => p.lineup_status === 'lineup_pending').length
    
    return { confirmed, pending }
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {matches.map(match => {
        const timeUntil = getTimeUntilKickoff(match.kickoff)
        const { confirmed, pending } = getPlayersByStatus(match.players)
        
        return (
          <div key={match.id} className="bg-white rounded-lg shadow-md p-4 border">
            {/* Match Header */}
            <div className="flex justify-between items-center mb-3">
              <div className="text-lg font-semibold text-gray-900">
                {match.homeTeam} vs {match.awayTeam}
              </div>
              <div className={`px-2 py-1 rounded text-sm font-medium ${
                timeUntil === 'Started' 
                  ? 'bg-red-100 text-red-800'
                  : 'bg-blue-100 text-blue-800'
              }`}>
                {timeUntil === 'Started' ? 'Live' : timeUntil}
              </div>
            </div>

            {/* Kickoff Time */}
            <div className="text-sm text-gray-600 mb-3">
              Kickoff: {formatKickoffTime(match.kickoff)}
            </div>

            {/* Your Players */}
            <div className="border-t pt-3">
              <div className="text-sm font-medium text-gray-700 mb-2">
                Your Players ({match.players.length})
              </div>
              
              {/* Player Names */}
              <div className="space-y-1 mb-3">
                {match.players.map(player => (
                  <div key={player.id} className="flex items-center justify-between text-sm">
                    <span className="text-gray-900">{player.name}</span>
                    <span className={`px-1.5 py-0.5 rounded text-xs ${
                      player.lineup_status === 'confirmed_starting'
                        ? 'bg-green-100 text-green-800'
                        : player.lineup_status === 'confirmed_bench'
                        ? 'bg-red-100 text-red-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {player.lineup_status === 'confirmed_starting' ? 'Starting' :
                       player.lineup_status === 'confirmed_bench' ? 'Bench' : 'TBD'}
                    </span>
                  </div>
                ))}
              </div>

              {/* Status Summary */}
              <div className="flex justify-between text-xs text-gray-500 border-t pt-2">
                <span>Confirmed: {confirmed}</span>
                <span>Pending: {pending}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default MatchOverview
