import { getTeamLogoConfig } from '../utils/teamLogos';
import { useState, useEffect } from 'react';
import { parseMatchTime, parseStructuredMatchTime } from '../utils/matchUtils';

const PlayerCard = ({ player }) => {
  
  // Calculate countdown
  const calculateCountdown = (matchDate) => {
    if (!matchDate) return null;
    
    const now = new Date();
    const timeDiff = matchDate.getTime() - now.getTime();
    
    if (timeDiff <= 0) {
      return { expired: true, text: 'Match Started' };
    }
    
    const days = Math.floor(timeDiff / (1000 * 60 * 60 * 24));
    const hours = Math.floor((timeDiff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
    const minutes = Math.floor((timeDiff % (1000 * 60 * 60)) / (1000 * 60));
    const seconds = Math.floor((timeDiff % (1000 * 60)) / 1000);
    
    // Format countdown text
    if (days > 0) {
      return { expired: false, text: `${days}d ${hours}h ${minutes}m`, urgent: false };
    } else if (hours > 0) {
      return { expired: false, text: `${hours}h ${minutes}m ${seconds}s`, urgent: hours < 2 };
    } else if (minutes > 0) {
      return { expired: false, text: `${minutes}m ${seconds}s`, urgent: true };
    } else {
      return { expired: false, text: `${seconds}s`, urgent: true };
    }
  };

  // State for countdown
  const [countdown, setCountdown] = useState(null);
  
  // Try structured format first, then fallback to legacy format
  let matchInfo = null;
  if (player.match_info) {
    matchInfo = parseStructuredMatchTime(player.match_info, player.team, player.opponent);
  }
  
  if (!matchInfo) {
    matchInfo = parseMatchTime(player.opponent);
  }

  // Update countdown every second
  useEffect(() => {
    if (!matchInfo?.matchDate) return;

    const updateCountdown = () => {
      setCountdown(calculateCountdown(matchInfo.matchDate));
    };

    updateCountdown(); // Initial update
    const interval = setInterval(updateCountdown, 1000);

    return () => clearInterval(interval);
  }, [matchInfo?.matchDate]);


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
      case 'predicted_starting':
        return player.is_expected_starter ? 'Predicted Starting 🔮' : 'Predicted Starting 🔮'
      case 'predicted_bench':
        return player.is_expected_starter ? 'Predicted Bench 😰' : 'Predicted Sub'
      case 'predicted_unavailable':
        return 'Predicted Unavailable ⚠️'
      case 'no_match_today':
        return 'No Match Today'
      case 'no_prediction':
        return 'No Prediction Available'
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
      case 'predicted_starting':
        return player.is_expected_starter ? '🔮' : '💫'
      case 'predicted_bench':
        return player.is_expected_starter ? '😰' : '🔮'
      case 'predicted_unavailable':
        return '⚠️'
      case 'no_match_today':
        return '😴'
      case 'no_prediction':
        return '❔'
      default:
        return '❓'
    }
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
    <div className={`player-card bg-gray-800 border border-gray-700 rounded-lg p-4 ${isUrgent() ? 'ring-2 ring-red-400' : ''} relative overflow-hidden`}>
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
        </div>

        {/* Status */}
        <div className={`text-sm font-medium mb-3 ${
          player.lineup_status === 'confirmed_starting' 
            ? player.is_expected_starter ? 'text-green-600' : 'text-orange-600'
            : player.lineup_status === 'confirmed_bench'
            ? player.is_expected_starter ? 'text-red-600' : 'text-gray-600'
            : player.lineup_status === 'predicted_starting'
            ? player.is_expected_starter ? 'text-blue-500' : 'text-purple-500'
            : player.lineup_status === 'predicted_bench'
            ? player.is_expected_starter ? 'text-orange-500' : 'text-gray-500'
            : player.lineup_status === 'predicted_unavailable'
            ? 'text-red-400'
            : 'text-gray-500'
        }`}>
          {getStatusText()}
        </div>

        {/* Countdown Timer */}
        {matchInfo && countdown ? (
          <div className={`rounded-lg p-3 mb-3 text-center ${
            countdown.expired 
              ? 'bg-red-900/40 border border-red-600'
              : countdown.urgent 
              ? 'bg-orange-900/40 border border-orange-600 animate-pulse'
              : 'bg-blue-900/40 border border-blue-600'
          }`}>
            <div className="text-xs text-gray-300 mb-1">
              {matchInfo.isAway ? 'Away vs' : 'Home vs'} {matchInfo.opponent}
            </div>
            <div className="text-sm text-gray-400 mb-1">
              {matchInfo.dayOfWeek} {matchInfo.timeStr}
            </div>
            <div className={`text-lg font-bold ${
              countdown.expired 
                ? 'text-red-400'
                : countdown.urgent 
                ? 'text-orange-400'
                : 'text-blue-400'
            }`}>
              {countdown.expired ? '⚠️' : '⏰'} {countdown.text}
            </div>
            {countdown.urgent && !countdown.expired && (
              <div className="text-xs text-orange-300 mt-1 font-medium">
                🚨 TIME CRITICAL
              </div>
            )}
          </div>
        ) : player.opponent && !matchInfo ? (
          <div className="bg-gray-700/40 border border-gray-600 rounded-lg p-3 mb-3 text-center">
            <div className="text-sm text-gray-400 mb-1">Match Info</div>
            <div className="text-gray-300">{player.opponent}</div>
            <div className="text-xs text-gray-500 mt-1">Unable to parse match time</div>
          </div>
        ) : !player.opponent ? (
          <div className="bg-gray-700/40 border border-gray-600 rounded-lg p-3 mb-3 text-center">
            <div className="text-sm text-gray-400">😴 No Match Scheduled</div>
          </div>
        ) : null}
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
