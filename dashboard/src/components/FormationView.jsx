import { getTeamLogoConfig } from '../utils/teamLogos'

const FormationView = ({ players }) => {
  // Filter starting and bench players
  const starters = players.filter(player => player.is_expected_starter)
  const benchPlayers = players.filter(player => !player.is_expected_starter)
  
  // Group starters by position
  const playersByPosition = {
    goalkeeper: starters.filter(p => p.position.toLowerCase() === 'goalkeeper'),
    defender: starters.filter(p => p.position.toLowerCase() === 'defender'),
    midfielder: starters.filter(p => p.position.toLowerCase() === 'midfielder'),
    forward: starters.filter(p => p.position.toLowerCase() === 'forward')
  }

  // Formation layout logic
  const getFormationLayout = () => {
    const gk = playersByPosition.goalkeeper.length
    const def = playersByPosition.defender.length
    const mid = playersByPosition.midfielder.length
    const fwd = playersByPosition.forward.length
    
    return {
      goalkeeper: Math.min(gk, 1), // Always 1 GK
      defender: Math.max(3, Math.min(def, 5)), // 3-5 defenders
      midfielder: Math.max(3, Math.min(mid, 5)), // 3-5 midfielders
      forward: Math.max(1, Math.min(fwd, 3)) // 1-3 forwards
    }
  }

  const formation = getFormationLayout()

  // Position players in formation rows
  const positionPlayers = (positionArray, maxCount) => {
    return positionArray.slice(0, maxCount)
  }

  const renderPlayerCard = (player, index, total) => {
    return (
      <PlayerFormationCard 
        key={player.id}
        player={player}
        position={index}
        totalInRow={total}
      />
    )
  }

  const goalkeepers = positionPlayers(playersByPosition.goalkeeper, formation.goalkeeper)
  const defenders = positionPlayers(playersByPosition.defender, formation.defender)
  const midfielders = positionPlayers(playersByPosition.midfielder, formation.midfielder)
  const forwards = positionPlayers(playersByPosition.forward, formation.forward)

  return (
    <div className="formation-view">
      {/* Full Squad Container */}
      <div className="flex justify-center items-start gap-6 max-w-6xl mx-auto">
        
        {/* Bench Players - Left Side */}
        <div className="bench-container flex flex-col items-center">
          <div className="text-white text-sm font-medium mb-4 bg-gray-800 px-3 py-2 rounded">
            Bench ({benchPlayers.length})
          </div>
          <div className="flex flex-col gap-3">
            {benchPlayers.map(player => (
              <BenchPlayerCard key={player.id} player={player} />
            ))}
          </div>
        </div>

        {/* Football Pitch Container */}
        <div className="pitch-container relative bg-green-600 rounded-lg overflow-hidden shadow-2xl">
          {/* Pitch Background */}
          <div className="pitch-field relative w-[500px] h-[700px] bg-gradient-to-b from-green-500 to-green-700">

          {/* Player Positions */}
          <div className="absolute inset-0 flex flex-col justify-between py-8 px-4">
            
            {/* Forwards Row */}
            <div className="flex justify-center items-center gap-10 h-24">
              {forwards.map((player, index) => renderPlayerCard(player, index, forwards.length))}
            </div>

            {/* Midfielders Row */}
            <div className="flex justify-center items-center gap-8 h-24">
              {midfielders.map((player, index) => renderPlayerCard(player, index, midfielders.length))}
            </div>

            {/* Defenders Row */}
            <div className="flex justify-center items-center gap-6 h-24">
              {defenders.map((player, index) => renderPlayerCard(player, index, defenders.length))}
            </div>

            {/* Goalkeeper Row */}
            <div className="flex justify-center items-center h-24">
              {goalkeepers.map((player, index) => renderPlayerCard(player, index, goalkeepers.length))}
            </div>

          </div>
        </div>

        {/* Formation Info */}
        <div className="absolute top-4 right-4 bg-black/50 text-white px-3 py-2 rounded">
          <div className="text-sm font-medium">
            Formation: {formation.defender}-{formation.midfielder}-{formation.forward}
          </div>
        </div>
      </div>
      
      </div>

      {/* Legend */}
      <div className="mt-6 text-center">
        <div className="text-gray-400 text-sm mb-3">
          Starting XI ({starters.length} players) | Bench ({benchPlayers.length} players)
        </div>
        
        {/* Status Indicators Legend */}
        <div className="flex flex-wrap justify-center gap-3 text-xs">
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-green-500 rounded-full flex items-center justify-center text-xs">✅</div>
            <span className="text-gray-300">Confirmed Starter</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-red-500 rounded-full flex items-center justify-center text-xs">🚨</div>
            <span className="text-gray-300">Benched Alert</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-orange-500 rounded-full flex items-center justify-center text-xs">⚡</div>
            <span className="text-gray-300">Surprise Start</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-yellow-500 rounded-full flex items-center justify-center text-xs">⏱️</div>
            <span className="text-gray-300">Lineup Pending</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-4 h-4 bg-gray-500 rounded-full flex items-center justify-center text-xs grayscale">⚽</div>
            <span className="text-gray-300">No Match Today</span>
          </div>
        </div>
      </div>
    </div>
  )
}

// Simplified Player Card for Formation View
const PlayerFormationCard = ({ player }) => {
  const getTeamLogo = () => {
    const teamName = player.team  // team is a string in the data
    const logoConfig = getTeamLogoConfig(teamName)
    return logoConfig.exists ? logoConfig.src : null
  }

  // Extract last name only for formation view
  const getDisplayName = (fullName) => {
    if (!fullName) return ''
    const nameParts = fullName.trim().split(' ')
    return nameParts.length > 1 ? nameParts[nameParts.length - 1] : nameParts[0]
  }

  // Get status indicators for the player
  const getStatusIndicator = () => {
    // Red flags - expected starter but bad news
    if (player.is_expected_starter && player.lineup_status === 'confirmed_bench') {
      return { emoji: '🚨', color: 'bg-red-500', alert: true, text: 'Benched!' }
    }
    
    // Positive confirmations - expected starter and confirmed starting
    if (player.is_expected_starter && player.lineup_status === 'confirmed_starting') {
      return { emoji: '✅', color: 'bg-green-500', alert: false, text: 'Confirmed' }
    }
    
    // Unexpected starter (not expected but confirmed starting)
    if (!player.is_expected_starter && player.lineup_status === 'confirmed_starting') {
      return { emoji: '⚡', color: 'bg-orange-500', alert: true, text: 'Surprise start!' }
    }
    
    // Lineup pending - neutral but informative
    if (player.lineup_status === 'lineup_pending') {
      return { emoji: '⏱️', color: 'bg-yellow-500', alert: false, text: 'Pending' }
    }
    
    // No indicator for normal cases (no match today, etc.)
    return null
  }

  const teamLogo = getTeamLogo()
  const statusIndicator = getStatusIndicator()

  return (
    <div className="player-formation-card flex flex-col items-center">
      {/* Player Crest/Jersey */}
      <div className="relative w-16 h-16 mb-2">
        {teamLogo ? (
          <div className={`w-full h-full bg-white/90 rounded-full p-1 shadow-lg border-2 ${
            statusIndicator?.alert ? 'border-red-400' : 'border-white'
          }`}>
            <img 
              src={teamLogo}
              alt={`${player.team} logo`}
              className={`w-full h-full object-contain ${
                player.lineup_status === 'no_match_today' ? 'grayscale' : ''
              }`}
            />
          </div>
        ) : (
          <div className={`w-full h-full rounded-full flex items-center justify-center font-bold text-base shadow-lg border-2 ${
            player.lineup_status === 'no_match_today' 
              ? 'bg-gray-500 text-gray-300' 
              : 'bg-gray-600 text-white'
          } ${statusIndicator?.alert ? 'border-red-400' : 'border-white'}`}>
            {player.team_abbreviation || player.team?.charAt(0) || '?'}
          </div>
        )}
        
        {/* Status Indicator Overlay */}
        {statusIndicator && (
          <div className={`absolute -top-1 -right-1 w-6 h-6 ${statusIndicator.color} rounded-full flex items-center justify-center text-xs border-2 border-white shadow-lg`}>
            {statusIndicator.emoji}
          </div>
        )}
      </div>

      {/* Player Name */}
      <div className="text-white text-sm font-medium text-center bg-black/50 px-3 py-1.5 rounded min-w-0">
        <div className="break-words leading-tight">
          {getDisplayName(player.name)}
        </div>
      </div>

      {/* Fantasy Points */}
      <div className="text-white/80 text-sm mt-1 font-medium">
        {player.average_points}
      </div>
    </div>
  )
}

// Bench Player Card - Smaller version for bench display
const BenchPlayerCard = ({ player }) => {
  const getTeamLogo = () => {
    const teamName = player.team
    const logoConfig = getTeamLogoConfig(teamName)
    return logoConfig.exists ? logoConfig.src : null
  }

  // Extract last name only for formation view consistency
  const getDisplayName = (fullName) => {
    if (!fullName) return ''
    const nameParts = fullName.trim().split(' ')
    return nameParts.length > 1 ? nameParts[nameParts.length - 1] : nameParts[0]
  }

  // Get status indicators for bench players
  const getStatusIndicator = () => {
    // Bench player confirmed starting (unexpected!)
    if (!player.is_expected_starter && player.lineup_status === 'confirmed_starting') {
      return { emoji: '⚡', color: 'bg-orange-500', alert: true }
    }
    
    // Bench player confirmed on bench (expected)
    if (!player.is_expected_starter && player.lineup_status === 'confirmed_bench') {
      return { emoji: '⏸️', color: 'bg-gray-500', alert: false }
    }
    
    // Lineup pending
    if (player.lineup_status === 'lineup_pending') {
      return { emoji: '⏱️', color: 'bg-yellow-500', alert: false }
    }
    
    return null
  }

  const teamLogo = getTeamLogo()
  const statusIndicator = getStatusIndicator()

  return (
    <div className="bench-player-card flex items-center gap-3 bg-gray-800/50 rounded-lg p-2 min-w-[200px]">
      {/* Small Player Badge */}
      <div className="relative w-10 h-10">
        {teamLogo ? (
          <div className={`w-full h-full bg-white/90 rounded-full p-1 shadow-md border ${
            statusIndicator?.alert ? 'border-red-400' : 'border-gray-400'
          }`}>
            <img 
              src={teamLogo}
              alt={`${player.team} logo`}
              className={`w-full h-full object-contain ${
                player.lineup_status === 'no_match_today' ? 'grayscale' : ''
              }`}
            />
          </div>
        ) : (
          <div className={`w-full h-full rounded-full flex items-center justify-center text-xs font-bold shadow-md border ${
            player.lineup_status === 'no_match_today' 
              ? 'bg-gray-500 text-gray-300' 
              : 'bg-gray-600 text-white'
          } ${statusIndicator?.alert ? 'border-red-400' : 'border-gray-400'}`}>
            {player.team_abbreviation || player.team?.charAt(0) || '?'}
          </div>
        )}
        
        {/* Status Indicator Overlay */}
        {statusIndicator && (
          <div className={`absolute -top-1 -right-1 w-4 h-4 ${statusIndicator.color} rounded-full flex items-center justify-center text-xs border border-white shadow-md`}>
            {statusIndicator.emoji}
          </div>
        )}
      </div>

      {/* Player Info */}
      <div className="flex-1 min-w-0">
        <div className="text-white text-xs font-medium truncate">
          {getDisplayName(player.name)}
        </div>
        <div className="text-gray-400 text-xs">
          {player.position}
        </div>
        <div className="text-gray-300 text-xs">
          {player.average_points}
        </div>
      </div>
    </div>
  )
}

export default FormationView
