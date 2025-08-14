/**
 * Team Logo Utilities for 2025-26 Premier League Season
 * 
 * Handles mapping team names to logo files and provides utility functions
 * for displaying team logos in the dashboard.
 * 
 * The 20 teams for 2025-26 season are:
 * Arsenal, Aston Villa, Bournemouth, Brentford, Brighton, Burnley, Chelsea,
 * Crystal Palace, Everton, Fulham, Leeds United, Liverpool, Manchester City,
 * Manchester United, Newcastle United, Nottingham Forest, Sunderland,
 * Tottenham, West Ham United, Wolverhampton Wanderers
 */

// Team logo mapping for 2025-26 Premier League season (embedded to avoid import issues)
const teamLogoMapping = {
  // Arsenal
  "Arsenal": "Arsenal FC.png",
  "Arsenal FC": "Arsenal FC.png",
  
  // Aston Villa
  "Aston Villa": "Aston Villa.png",
  "Aston Villa FC": "Aston Villa.png",
  
  // Bournemouth
  "Bournemouth": "AFC Bournemouth.png",
  "AFC Bournemouth": "AFC Bournemouth.png",
  "Bournemouth FC": "AFC Bournemouth.png",
  
  // Brentford
  "Brentford": "Brentford FC.png",
  "Brentford FC": "Brentford FC.png",
  
  // Brighton
  "Brighton": "Brighton & Hove Albion.png",
  "Brighton & Hove Albion": "Brighton & Hove Albion.png",
  "Brighton & Hove Albion FC": "Brighton & Hove Albion.png",
  "Brighton and Hove Albion": "Brighton & Hove Albion.png",
  
  // Burnley
  "Burnley": "Burnley FC.png",
  "Burnley FC": "Burnley FC.png",
  
  // Chelsea
  "Chelsea": "Chelsea FC.png",
  "Chelsea FC": "Chelsea FC.png",
  
  // Crystal Palace
  "Crystal Palace": "Crystal Palace.png",
  "Crystal Palace FC": "Crystal Palace.png",
  
  // Everton
  "Everton": "Everton FC.png",
  "Everton FC": "Everton FC.png",
  
  // Fulham
  "Fulham": "Fulham FC.png",
  "Fulham FC": "Fulham FC.png",
  
  // Leeds United (promoted)
  "Leeds": "Leeds United.png",
  "Leeds United": "Leeds United.png",
  "Leeds United FC": "Leeds United.png",
  
  // Liverpool
  "Liverpool": "Liverpool FC.png",
  "Liverpool FC": "Liverpool FC.png",
  
  // Manchester City
  "Manchester City": "Manchester City.png",
  "Manchester City FC": "Manchester City.png",
  "Man City": "Manchester City.png",
  
  // Manchester United
  "Manchester United": "Manchester United.png",
  "Manchester United FC": "Manchester United.png",
  "Man United": "Manchester United.png",
  "Man Utd": "Manchester United.png",
  
  // Newcastle United
  "Newcastle": "Newcastle United.png",
  "Newcastle United": "Newcastle United.png",
  "Newcastle United FC": "Newcastle United.png",
  
  // Nottingham Forest
  "Nottingham Forest": "Nottingham Forest.png",
  "Nottingham Forest FC": "Nottingham Forest.png",
  "Nott'm Forest": "Nottingham Forest.png",
  
  // Sunderland (promoted)
  "Sunderland": "Sunderland AFC.png",
  "Sunderland AFC": "Sunderland AFC.png",
  "Sunderland FC": "Sunderland AFC.png",
  
  // Tottenham
  "Tottenham": "Tottenham Hotspur.png",
  "Tottenham Hotspur": "Tottenham Hotspur.png",
  "Tottenham Hotspur FC": "Tottenham Hotspur.png",
  "Spurs": "Tottenham Hotspur.png",
  
  // West Ham
  "West Ham": "West Ham United.png",
  "West Ham United": "West Ham United.png",
  "West Ham United FC": "West Ham United.png",
  
  // Wolverhampton Wanderers
  "Wolves": "Wolverhampton Wanderers.png",
  "Wolverhampton": "Wolverhampton Wanderers.png",
  "Wolverhampton Wanderers": "Wolverhampton Wanderers.png",
  "Wolverhampton Wanderers FC": "Wolverhampton Wanderers.png"
};

/**
 * Get the logo filename for a given team name
 * @param {string} teamName - The team name to get logo for
 * @returns {string|null} - The logo filename or null if not found
 */
export const getTeamLogoFilename = (teamName) => {
  if (!teamName) return null;
  
  // Try exact match first
  if (teamLogoMapping[teamName]) {
    return teamLogoMapping[teamName];
  }
  
  // Try case-insensitive match
  const lowerTeamName = teamName.toLowerCase();
  const mappingKeys = Object.keys(teamLogoMapping);
  
  for (const key of mappingKeys) {
    if (key.toLowerCase() === lowerTeamName) {
      return teamLogoMapping[key];
    }
  }
  
  // Try partial match (useful for abbreviations)
  for (const key of mappingKeys) {
    if (key.toLowerCase().includes(lowerTeamName) || lowerTeamName.includes(key.toLowerCase())) {
      return teamLogoMapping[key];
    }
  }
  
  return null;
};

/**
 * Get the full path to a team logo
 * @param {string} teamName - The team name to get logo path for
 * @returns {string|null} - The full logo path or null if not found
 */
export const getTeamLogoPath = (teamName) => {
  const filename = getTeamLogoFilename(teamName);
  if (!filename) return null;
  
  // Bulletproof path resolution that works everywhere:
  // - Local dev: http://localhost:5175/FantasyFootballLineupTracker/
  // - GitHub Pages: https://username.github.io/FantasyFootballLineupTracker/
  // - Any other deployment
  
  // Get the base URL from Vite environment (set in vite.config.js)
  let basePath = import.meta.env.BASE_URL || '/';
  
  // Ensure base path ends with '/' but doesn't double up
  if (!basePath.endsWith('/')) {
    basePath += '/';
  }
  
  return `${basePath}team-logos/${filename}`;
};

/**
 * Check if a team logo exists
 * @param {string} teamName - The team name to check
 * @returns {boolean} - True if logo exists, false otherwise
 */
export const hasTeamLogo = (teamName) => {
  return getTeamLogoFilename(teamName) !== null;
};

/**
 * Get team logo with fallback options
 * @param {string} teamName - The team name
 * @param {object} options - Configuration options
 * @param {string} options.fallback - Fallback image path
 * @param {string} options.size - Size class for styling
 * @returns {object} - Logo configuration object
 */
export const getTeamLogoConfig = (teamName, options = {}) => {
  const logoPath = getTeamLogoPath(teamName);
  const basePath = import.meta.env.BASE_URL || '/';
  
  return {
    src: logoPath || options.fallback || `${basePath}team-logos/default-team.svg`,
    alt: `${teamName} logo`,
    exists: logoPath !== null,
    teamName: teamName,
    size: options.size || 'w-8 h-8'
  };
};

/**
 * Get all available team names for 2025-26 season
 * @returns {Array} - Array of Premier League team names
 */
export const getPremierLeagueTeams202526 = () => {
  return [
    'Arsenal',
    'Aston Villa', 
    'Bournemouth',
    'Brentford',
    'Brighton & Hove Albion',
    'Burnley',
    'Chelsea',
    'Crystal Palace',
    'Everton',
    'Fulham',
    'Leeds United',
    'Liverpool',
    'Manchester City',
    'Manchester United',
    'Newcastle United',
    'Nottingham Forest',
    'Sunderland',
    'Tottenham Hotspur',
    'West Ham United',
    'Wolverhampton Wanderers'
  ];
};

/**
 * Get all available team logos
 * @returns {Array} - Array of available team names
 */
export const getAvailableTeams = () => {
  return Object.keys(teamLogoMapping);
};

/**
 * Validate and normalize team name for logo lookup
 * @param {string} teamName - The team name to normalize
 * @returns {string} - Normalized team name
 */
export const normalizeTeamName = (teamName) => {
  if (!teamName) return '';
  
  // Common normalizations for 2025-26 season
  const normalizations = {
    'Man City': 'Manchester City',
    'Man United': 'Manchester United',
    'Man Utd': 'Manchester United',
    'Spurs': 'Tottenham Hotspur',
    'Wolves': 'Wolverhampton Wanderers',
    'Nott\'m Forest': 'Nottingham Forest',
    'Leeds': 'Leeds United'
  };
  
  return normalizations[teamName] || teamName;
};

/**
 * Check if a team is in the 2025-26 Premier League
 * @param {string} teamName - The team name to check
 * @returns {boolean} - True if team is in Premier League, false otherwise
 */
export const isPremierLeagueTeam = (teamName) => {
  const normalizedName = normalizeTeamName(teamName);
  const plTeams = getPremierLeagueTeams202526();
  
  return plTeams.some(team => 
    team.toLowerCase() === normalizedName.toLowerCase() ||
    team.toLowerCase().includes(normalizedName.toLowerCase())
  );
};