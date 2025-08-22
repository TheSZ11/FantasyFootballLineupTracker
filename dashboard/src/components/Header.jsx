const Header = ({ summary, status, metadata }) => {
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
                  <span className="text-green-400 font-medium">{summary.confirmed_starting} Confirmed</span>
                </div>
              )}
              {summary?.predicted_starting > 0 && (
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-blue-400 rounded-full mr-2"></span>
                  <span className="text-blue-400 font-medium">{summary.predicted_starting} Predicted</span>
                </div>
              )}
              {summary?.confirmed_bench > 0 && (
                <div className="flex items-center">
                  <span className="status-indicator red"></span>
                  <span className="text-red-400 font-medium">{summary.confirmed_bench} Benched</span>
                </div>
              )}
              {summary?.predicted_bench > 0 && (
                <div className="flex items-center">
                  <span className="w-2 h-2 bg-orange-400 rounded-full mr-2"></span>
                  <span className="text-orange-400 font-medium">{summary.predicted_bench} Pred. Bench</span>
                </div>
              )}
            </div>
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
                <div className="text-2xl font-bold text-blue-400">
                  {(summary.predicted_starting || 0) + (summary.confirmed_starting || 0)}
                </div>
                <div className="text-xs text-gray-400">Predicted Starting</div>
              </div>
              <div className="bg-purple-900/30 rounded-lg p-3">
                <div className="text-2xl font-bold text-purple-400">{summary.players_with_predictions || 0}</div>
                <div className="text-xs text-gray-400">With Predictions</div>
              </div>
              <div className="bg-green-900/30 rounded-lg p-3">
                <div className="text-2xl font-bold text-green-400">
                  {(summary.confirmed_starting || 0) + (summary.confirmed_bench || 0)}
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
