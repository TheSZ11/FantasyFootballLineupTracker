// Utility functions for match data parsing and analysis

/**
 * Parse structured match info to get match date and time
 * @param {Object} matchInfo - Match info object with kickoff, home_team, away_team
 * @param {string} playerTeam - Player's team abbreviation
 * @param {string} opponent - Opponent team name
 * @returns {Object|null} - Match info object or null if invalid
 */
export const parseStructuredMatchTime = (matchInfo, playerTeam, opponent) => {
  if (!matchInfo || !matchInfo.kickoff) return null;
  
  try {
    // Parse ISO datetime string
    const matchDate = new Date(matchInfo.kickoff);
    if (isNaN(matchDate.getTime())) return null;
    
    // Determine if away game (player's team is away team)
    // If opponent is home team, then player is away
    const isAway = matchInfo.home_team === opponent;
    
    // Get day of week and time string
    const dayOfWeek = matchDate.toLocaleDateString('en-US', { weekday: 'short' });
    const timeStr = matchDate.toLocaleTimeString('en-US', { 
      hour: 'numeric', 
      minute: '2-digit',
      hour12: true 
    });
    
    // Calculate days until match
    const now = new Date();
    const timeDiff = matchDate.getTime() - now.getTime();
    const daysUntil = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
    
    return {
      matchDate,
      opponent,
      isAway,
      dayOfWeek,
      timeStr,
      daysUntil
    };
  } catch (error) {
    console.error('Error parsing structured match time:', error);
    return null;
  }
};

/**
 * Parse opponent string to get match date and time (legacy format)
 * @param {string} opponentString - Format: "@LEE Mon 3:00PM" or "BOU Fri 3:00PM"
 * @returns {Object|null} - Match info object or null if invalid
 */
export const parseMatchTime = (opponentString) => {
  if (!opponentString || opponentString.toLowerCase().includes('no match')) return null;
  
  // Format: "@LEE Mon 3:00PM" or "BOU Fri 3:00PM"
  const match = opponentString.match(/^(@)?(\w+)\s+(\w+)\s+(\d{1,2}:\d{2}(AM|PM))$/);
  if (!match) return null;
  
  const [, isAway, opponent, dayOfWeek, timeStr] = match;
  
  // Map day names to numbers (0 = Sunday, 1 = Monday, etc.)
  const dayMap = {
    'Sun': 0, 'Mon': 1, 'Tue': 2, 'Wed': 3, 'Thu': 4, 'Fri': 5, 'Sat': 6
  };
  
  const targetDay = dayMap[dayOfWeek];
  if (targetDay === undefined) return null;
  
  // Get current date and calculate target date
  const now = new Date();
  const currentDay = now.getDay();
  
  // Calculate days until target day (this week or next week)
  let daysUntil = targetDay - currentDay;
  if (daysUntil < 0) {
    daysUntil += 7; // Next week
  } else if (daysUntil === 0) {
    // Same day - check if time has passed
    const [time, period] = timeStr.split(/(?=[AP]M)/);
    const [hours, minutes] = time.split(':').map(Number);
    const hour24 = period === 'PM' && hours !== 12 ? hours + 12 : (period === 'AM' && hours === 12 ? 0 : hours);
    
    const targetTime = new Date(now);
    targetTime.setHours(hour24, minutes, 0, 0);
    
    if (targetTime <= now) {
      daysUntil = 7; // Next week same day
    }
  }
  
  // Create target date
  const targetDate = new Date(now);
  targetDate.setDate(now.getDate() + daysUntil);
  
  // Parse time
  const [time, period] = timeStr.split(/(?=[AP]M)/);
  const [hours, minutes] = time.split(':').map(Number);
  const hour24 = period === 'PM' && hours !== 12 ? hours + 12 : (period === 'AM' && hours === 12 ? 0 : hours);
  
  targetDate.setHours(hour24, minutes, 0, 0);
  
  return {
    matchDate: targetDate,
    opponent,
    isAway,
    dayOfWeek,
    timeStr,
    daysUntil
  };
};

/**
 * Check if a player is playing today
 * @param {Object} player - Player object with opponent field and match_info
 * @returns {boolean} - True if playing today
 */
export const isPlayingToday = (player) => {
  if (!player.opponent) return false;
  
  // Try structured format first, then fallback to legacy format
  let matchInfo = null;
  if (player.match_info) {
    matchInfo = parseStructuredMatchTime(player.match_info, player.team, player.opponent);
  }
  
  if (!matchInfo) {
    matchInfo = parseMatchTime(player.opponent);
  }
  
  if (!matchInfo) return false;
  
  return matchInfo.daysUntil === 0;
};

/**
 * Check if a player has a match (any day)
 * @param {Object} player - Player object with opponent field
 * @returns {boolean} - True if has a match
 */
export const hasMatch = (player) => {
  return player.opponent && !player.opponent.toLowerCase().includes('no match');
};

/**
 * Get players with matches from a list of players
 * @param {Array} players - Array of player objects
 * @returns {Array} - Players with matches
 */
export const getPlayersWithMatches = (players) => {
  return players.filter(hasMatch);
};

/**
 * Get players playing today from a list of players
 * @param {Array} players - Array of player objects
 * @returns {Array} - Players playing today
 */
export const getPlayersPlayingToday = (players) => {
  return players.filter(isPlayingToday);
};

/**
 * Get unique matches happening today from players
 * @param {Array} players - Array of player objects
 * @returns {Array} - Array of match objects
 */
export const getTodaysMatches = (players) => {
  const playersPlayingToday = getPlayersPlayingToday(players);
  
  // Group players by opponent to create unique matches
  const matchMap = new Map();
  
  playersPlayingToday.forEach(player => {
    // Try structured format first, then fallback to legacy format
    let matchInfo = null;
    if (player.match_info) {
      matchInfo = parseStructuredMatchTime(player.match_info, player.team, player.opponent);
    }
    
    if (!matchInfo) {
      matchInfo = parseMatchTime(player.opponent);
    }
    
    if (!matchInfo) return;
    
    const matchKey = `${matchInfo.opponent}-${matchInfo.dayOfWeek}-${matchInfo.timeStr}`;
    
    if (!matchMap.has(matchKey)) {
      matchMap.set(matchKey, {
        id: matchKey,
        opponent: matchInfo.opponent,
        isAway: matchInfo.isAway,
        dayOfWeek: matchInfo.dayOfWeek,
        timeStr: matchInfo.timeStr,
        kickoff: matchInfo.matchDate,
        players: []
      });
    }
    
    matchMap.get(matchKey).players.push(player);
  });
  
  return Array.from(matchMap.values()).sort((a, b) => a.kickoff - b.kickoff);
};
