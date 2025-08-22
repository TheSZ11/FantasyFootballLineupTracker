"""
Team name mappings for converting between abbreviations and full names.

This module maps team abbreviations from CSV files to the full team names
used by APIs and provides utilities for team name standardization.
"""

import unicodedata
from typing import Dict, List

# Team abbreviation to full name mapping
TEAM_ABBREVIATIONS = {
    'ARS': 'Arsenal',
    'AVL': 'Aston Villa', 
    'BOU': 'Bournemouth',
    'BRF': 'Brentford',
    'BHA': 'Brighton',
    'BUR': 'Burnley',
    'CHE': 'Chelsea',
    'CRY': 'Crystal Palace',
    'EVE': 'Everton',
    'FUL': 'Fulham',
    'IPS': 'Ipswich Town',
    'LEE': 'Leeds United',
    'LEI': 'Leicester City',
    'LIV': 'Liverpool',
    'MCI': 'Manchester City',
    'MUN': 'Manchester United',
    'NEW': 'Newcastle United',
    'NOT': 'Nottingham Forest',
    'SOU': 'Southampton',
    'SUN': 'Sunderland',
    'TOT': 'Tottenham',
    'WHU': 'West Ham United',
    'WOL': 'Wolverhampton Wanderers'
}

# Alternative team names that might appear in different data sources
TEAM_NAME_VARIANTS = {
    'Brighton & Hove Albion': 'Brighton',
    'Brighton and Hove Albion': 'Brighton',
    'Tottenham Hotspur': 'Tottenham',
    'Spurs': 'Tottenham',
    'Manchester United': 'Manchester United',
    'Man United': 'Manchester United',
    'Man Utd': 'Manchester United',
    'Man City': 'Manchester City',
    'Newcastle': 'Newcastle United',
    'West Ham': 'West Ham United',
    'Wolverhampton': 'Wolverhampton Wanderers',
    'Wolves': 'Wolverhampton Wanderers',
    'Nottm Forest': 'Nottingham Forest',
    'Forest': 'Nottingham Forest',
    'Crystal Palace': 'Crystal Palace'
}


def get_full_team_name(abbreviation: str) -> str:
    """
    Convert team abbreviation to full team name.
    
    Args:
        abbreviation: Team abbreviation (e.g., 'LIV')
        
    Returns:
        Full team name (e.g., 'Liverpool') or original if not found
    """
    if not abbreviation:
        return abbreviation
    
    return TEAM_ABBREVIATIONS.get(abbreviation.upper(), abbreviation)


def get_team_abbreviation(full_name: str) -> str:
    """
    Get team abbreviation from full name.
    
    Args:
        full_name: Full team name
        
    Returns:
        Team abbreviation or original if not found
    """
    if not full_name:
        return full_name
    
    # First check exact matches
    for abbrev, name in TEAM_ABBREVIATIONS.items():
        if name.lower() == full_name.lower():
            return abbrev
    
    # Check variants
    normalized_name = TEAM_NAME_VARIANTS.get(full_name, full_name)
    for abbrev, name in TEAM_ABBREVIATIONS.items():
        if name.lower() == normalized_name.lower():
            return abbrev
    
    return full_name


def normalize_team_name(team_name: str) -> str:
    """
    Normalize team name to standard format.
    
    Args:
        team_name: Team name to normalize
        
    Returns:
        Standardized team name
    """
    if not team_name:
        return team_name
    
    # Check if it's a known variant
    if team_name in TEAM_NAME_VARIANTS:
        return TEAM_NAME_VARIANTS[team_name]
    
    # Check if it's an abbreviation
    full_name = get_full_team_name(team_name)
    if full_name != team_name:
        return full_name
    
    return team_name


def get_all_teams() -> List[str]:
    """Get list of all team names."""
    return list(TEAM_ABBREVIATIONS.values())


def get_all_abbreviations() -> List[str]:
    """Get list of all team abbreviations."""
    return list(TEAM_ABBREVIATIONS.keys())


def is_valid_team(team_name: str) -> bool:
    """
    Check if a team name is valid (known team).
    
    Args:
        team_name: Team name to check
        
    Returns:
        True if team is known, False otherwise
    """
    if not team_name:
        return False
    
    # Check full names
    if team_name in TEAM_ABBREVIATIONS.values():
        return True
    
    # Check abbreviations
    if team_name.upper() in TEAM_ABBREVIATIONS:
        return True
    
    # Check variants
    if team_name in TEAM_NAME_VARIANTS:
        return True
    
    return False


def get_team_mapping_info() -> Dict[str, Dict[str, str]]:
    """
    Get complete team mapping information for debugging.
    
    Returns:
        Dictionary with team mapping details
    """
    return {
        'abbreviations': TEAM_ABBREVIATIONS,
        'variants': TEAM_NAME_VARIANTS,
        'total_teams': len(TEAM_ABBREVIATIONS),
        'total_variants': len(TEAM_NAME_VARIANTS)
    }


def normalize_player_name(player_name: str) -> str:
    """
    Normalize player name for matching across different data sources.
    
    This function handles:
    - Unicode character normalization (ø -> o, ä -> a, etc.)
    - Case normalization
    - Whitespace normalization
    
    Args:
        player_name: Player name to normalize
        
    Returns:
        Normalized player name for consistent matching
    """
    if not player_name:
        return player_name
    
    # Manual character replacements for common football names
    # This approach is more reliable than unicodedata for our use case
    char_map = {
        'ø': 'o', 'Ø': 'o',
        'ä': 'a', 'Ä': 'a', 'à': 'a', 'À': 'a', 'á': 'a', 'Á': 'a', 'â': 'a', 'Â': 'a', 'ã': 'a', 'Ã': 'a',
        'é': 'e', 'É': 'e', 'è': 'e', 'È': 'e', 'ê': 'e', 'Ê': 'e', 'ë': 'e', 'Ë': 'e',
        'í': 'i', 'Í': 'i', 'ì': 'i', 'Ì': 'i', 'î': 'i', 'Î': 'i', 'ï': 'i', 'Ï': 'i',
        'ó': 'o', 'Ó': 'o', 'ò': 'o', 'Ò': 'o', 'ô': 'o', 'Ô': 'o', 'õ': 'o', 'Õ': 'o', 'ö': 'o', 'Ö': 'o',
        'ú': 'u', 'Ú': 'u', 'ù': 'u', 'Ù': 'u', 'û': 'u', 'Û': 'u', 'ü': 'u', 'Ü': 'u',
        'ñ': 'n', 'Ñ': 'n',
        'ç': 'c', 'Ç': 'c',
        'ß': 'ss',
        # Add more as needed for specific players
    }
    
    # Apply character replacements
    normalized = player_name
    for old_char, new_char in char_map.items():
        normalized = normalized.replace(old_char, new_char)
    
    # Convert to lowercase and normalize whitespace
    return ' '.join(normalized.lower().split())


def names_match(name1: str, name2: str) -> bool:
    """
    Check if two player names match after normalization.
    
    Args:
        name1: First player name
        name2: Second player name
        
    Returns:
        True if names match after normalization
    """
    if not name1 or not name2:
        return name1 == name2
    
    return normalize_player_name(name1) == normalize_player_name(name2)
