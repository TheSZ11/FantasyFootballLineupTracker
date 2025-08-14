import { useState, useEffect } from 'react'
import Dashboard from './components/Dashboard'
import './App.css'

function App() {
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const loadDashboardData = async (isRefresh = false) => {
    if (isRefresh) {
      setRefreshing(true)
    } else {
      setLoading(true)
    }
    setError(null)
    
    try {
      // Add cache busting for refresh
      const timestamp = isRefresh ? `?t=${Date.now()}` : ''
      
      // Load all the JSON data files
      const [lineupResponse, statusResponse, metaResponse] = await Promise.all([
        fetch(`./data/lineup_status.json${timestamp}`),
        fetch(`./data/status.json${timestamp}`),
        fetch(`./data/metadata.json${timestamp}`)
      ])
      
      if (!lineupResponse.ok) {
        throw new Error(`Failed to load lineup data: ${lineupResponse.status}`)
      }
      
      const [lineupData, statusData, metaData] = await Promise.all([
        lineupResponse.json(),
        statusResponse.ok ? statusResponse.json() : {},
        metaResponse.ok ? metaResponse.json() : {}
      ])
      
      setDashboardData({
        lineup: lineupData,
        status: statusData,
        metadata: metaData
      })
    } catch (err) {
      console.error('Failed to load dashboard data:', err)
      setError(err.message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleRefresh = () => {
    loadDashboardData(true)
  }

  useEffect(() => {
    loadDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-400 mx-auto"></div>
          <p className="mt-4 text-lg text-gray-300">Loading lineup data...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <div className="bg-red-900/20 border border-red-800 rounded-lg p-6 max-w-md">
          <h2 className="text-lg font-semibold text-red-400 mb-2">Failed to Load Data</h2>
          <p className="text-red-300 mb-4">{error}</p>
          <button 
            onClick={loadDashboardData}
            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900">
      <Dashboard 
        data={dashboardData} 
        onRefresh={handleRefresh}
        refreshing={refreshing}
      />
    </div>
  )
}

export default App