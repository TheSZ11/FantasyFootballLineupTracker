import { useState } from 'react'
import Header from './Header'
import PlayerCard from './PlayerCard'
import MatchOverview from './MatchOverview'
import FormationView from './FormationView'

const Dashboard = ({ data, onRefresh, refreshing = false }) => {
  const [filterStatus, setFilterStatus] = useState('all')
  
  if (!data || !data.lineup) {
    return <div>No data available</div>
  }

  const { lineup, status, metadata } = data
  const { players, summary } = lineup

  // Filter players based on selected status
  const filteredPlayers = players.filter(player => {
    if (filterStatus === 'all') return true
    if (filterStatus === 'active') return player.is_expected_starter
    if (filterStatus === 'matches_today') return player.match_info !== null
    if (filterStatus === 'lineup_pending') return player.lineup_status === 'lineup_pending'
    return true
  })

  // Get unique matches for today
  const todaysMatches = players
    .filter(p => p.match_info)
    .reduce((matches, player) => {
      const matchId = player.match_info.id
      if (!matches.find(m => m.id === matchId)) {
        matches.push({
          id: matchId,
          homeTeam: player.match_info.home_team,
          awayTeam: player.match_info.away_team,
          kickoff: new Date(player.match_info.kickoff),
          players: players.filter(p => p.match_info?.id === matchId)
        })
      }
      return matches
    }, [])
    .sort((a, b) => a.kickoff - b.kickoff)

  return (
    <div className="min-h-screen bg-gray-900">
      <Header 
        summary={summary}
        status={status}
        metadata={metadata}
        onRefresh={onRefresh}
        refreshing={refreshing}
      />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Matches Overview */}
        {todaysMatches.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-gray-100 mb-4">
              Today's Matches ({todaysMatches.length})
            </h2>
            <MatchOverview matches={todaysMatches} />
          </div>
        )}

        {/* Filter Controls */}
        <div className="mb-6">
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilterStatus('all')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filterStatus === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              All Players ({players.length})
            </button>
            <button
              onClick={() => setFilterStatus('active')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filterStatus === 'active'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              Expected Starters ({players.filter(p => p.is_expected_starter).length})
            </button>
            <button
              onClick={() => setFilterStatus('matches_today')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filterStatus === 'matches_today'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              Playing Today ({summary.players_with_matches_today})
            </button>
            <button
              onClick={() => setFilterStatus('lineup_pending')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filterStatus === 'lineup_pending'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              Lineup Pending ({summary.lineup_pending})
            </button>
            <button
              onClick={() => setFilterStatus('formation')}
              className={`px-4 py-2 rounded-lg transition-colors ${
                filterStatus === 'formation'
                  ? 'bg-green-600 text-white'
                  : 'bg-gray-800 text-gray-200 hover:bg-gray-700'
              }`}
            >
              Formation View
            </button>
          </div>
        </div>

        {/* Conditional View Rendering */}
        {filterStatus === 'formation' ? (
          <FormationView players={players} />
        ) : (
          <>
            {/* Players Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filteredPlayers.map(player => (
                <PlayerCard 
                  key={player.id} 
                  player={player} 
                />
              ))}
            </div>

            {filteredPlayers.length === 0 && (
              <div className="text-center py-12">
                <p className="text-gray-400 text-lg">No players match the current filter</p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default Dashboard
