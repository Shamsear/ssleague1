"""
Template Helper Functions for Season-Aware Operations
"""

from flask import g
from season_context import SeasonContext

def get_current_season():
    """Template helper to get current season"""
    if hasattr(g, 'current_season') and g.current_season:
        return g.current_season
    return SeasonContext.get_current_season()

def get_user_team_in_season(user_id, season_id=None):
    """Template helper to get user's team in specific season"""
    return SeasonContext.get_team_by_user(user_id, season_id)

def format_season_name(season_data):
    """Format season name for display"""
    if not season_data:
        return "No Season"
    return f"{season_data.get('name', 'Unknown Season')} ({season_data.get('short_name', 'N/A')})"

def is_continuing_team(team_data):
    """Check if team is continuing from previous season"""
    return team_data and team_data.get('is_continuing_team', False)

def get_team_lineage_display(team_data):
    """Get display string for team lineage"""
    if not team_data:
        return "No Team"
    
    lineage_id = team_data.get('team_lineage_id')
    if lineage_id:
        return f"{team_data['name']} (Lineage #{lineage_id})"
    return team_data['name']
