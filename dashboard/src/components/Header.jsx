const Header = ({ summary, status, metadata, onRefresh }) => {
  const formatLastUpdate = (timestamp) => {
    if (!timestamp) return 'Unknown'
    const date = new Date(timestamp)
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getSystemStatus = () => {
    if (status?.monitoring?.is_running) return 'active'
    return 'stopped'
  }

  const getStatusDisplay = () => {
    const systemStatus = getSystemStatus()
    if (systemStatus === 'active') {
      return (
        <span className="flex items-center text-green-400">
          <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
          Monitoring Active
        </span>
      )
    }
    return (
      <span className="flex items-center text-gray-400">
        <span className="w-2 h-2 bg-gray-400 rounded-full mr-2"></span>
        Stopped
      </span>
    )
  }

  return (
    <header className="bg-gray-800 shadow-sm border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          {/* Title and Status */}
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-100">
              ⚽ Lineup Tracker
            </h1>
            <div className="hidden sm:flex items-center space-x-4 text-sm text-gray-300">
              <div>{getStatusDisplay()}</div>
              <div>
                Last Update: {formatLastUpdate(metadata?.generated_at)}
              </div>
            </div>
          </div>

          {/* Quick Stats */}
          <div className="flex items-center space-x-6">
            {/* Status Indicators */}
            <div className="hidden md:flex items-center space-x-4 text-sm">
              {summary?.confirmed_starting > 0 && (
                <div className="flex items-center">
                  <span className="status-indicator green"></span>
                  <span className="text-green-400 font-medium">{summary.confirmed_starting} Starting</span>
                </div>
              )}
              {summary?.confirmed_bench > 0 && (
                <div className="flex items-center">
                  <span className="status-indicator red"></span>
                  <span className="text-red-400 font-medium">{summary.confirmed_bench} Benched</span>
                </div>
              )}
              {summary?.lineup_pending > 0 && (
                <div className="flex items-center">
                  <span className="status-indicator yellow"></span>
                  <span className="text-yellow-400 font-medium">{summary.lineup_pending} Pending</span>
                </div>
              )}
            </div>

            {/* Refresh Button */}
            <button
              onClick={onRefresh}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
          </div>
        </div>

        {/* Mobile Status */}
        <div className="sm:hidden pb-4 flex justify-between items-center text-sm text-gray-300">
          <div>{getStatusDisplay()}</div>
          <div>Updated: {formatLastUpdate(metadata?.generated_at)}</div>
        </div>

        {/* Summary Stats */}
        {summary && (
          <div className="pb-4 border-t border-gray-700 pt-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="bg-gray-700 rounded-lg p-3">
                <div className="text-2xl font-bold text-gray-100">{summary.total_players}</div>
                <div className="text-xs text-gray-400">Total Players</div>
              </div>
              <div className="bg-blue-900/30 rounded-lg p-3">
                <div className="text-2xl font-bold text-blue-400">{summary.players_with_matches_today}</div>
                <div className="text-xs text-gray-400">Playing Today</div>
              </div>
              <div className="bg-yellow-900/30 rounded-lg p-3">
                <div className="text-2xl font-bold text-yellow-400">{summary.lineup_pending}</div>
                <div className="text-xs text-gray-400">Lineups Pending</div>
              </div>
              <div className="bg-green-900/30 rounded-lg p-3">
                <div className="text-2xl font-bold text-green-400">
                  {summary.confirmed_starting + summary.confirmed_bench}
                </div>
                <div className="text-xs text-gray-400">Lineups Confirmed</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}

export default Header
