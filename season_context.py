"""
Season Context Helper Module
============================
Provides season-aware functionality for the multi-season system.
"""

from functools import wraps
from flask import g, request, session
from models import db, Season
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class SeasonContext:
    """Context manager for season-aware operations"""
    
    @staticmethod
    def get_current_season():
        """Get the current active season"""
        try:
            # Try to get from Flask g first (cached for request)
            if hasattr(g, 'current_season') and g.current_season:
                return g.current_season
            
            # Query from database
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, short_name, is_active, status 
                    FROM season 
                    WHERE is_active = true 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """))
                row = result.fetchone()
                
                if row:
                    season_data = {
                        'id': row[0],
                        'name': row[1], 
                        'short_name': row[2],
                        'is_active': row[3],
                        'status': row[4]
                    }
                    
                    # Cache in Flask g for this request
                    g.current_season = season_data
                    return season_data
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting current season: {e}")
            return None
    
    @staticmethod
    def get_season_teams(season_id=None):
        """Get teams for a specific season (or current season if None)"""
        if season_id is None:
            current_season = SeasonContext.get_current_season()
            if not current_season:
                return []
            season_id = current_season['id']
        
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, balance, user_id, logo_url, 
                           team_lineage_id, is_continuing_team 
                    FROM team 
                    WHERE season_id = :season_id 
                    ORDER BY name
                """), {'season_id': season_id})
                
                teams = []
                for row in result:
                    teams.append({
                        'id': row[0],
                        'name': row[1],
                        'balance': row[2],
                        'user_id': row[3],
                        'logo_url': row[4],
                        'team_lineage_id': row[5],
                        'is_continuing_team': row[6]
                    })
                
                return teams
                
        except Exception as e:
            logger.error(f"Error getting season teams: {e}")
            return []
    
    @staticmethod
    def get_season_rounds(season_id=None):
        """Get rounds for a specific season"""
        if season_id is None:
            current_season = SeasonContext.get_current_season()
            if not current_season:
                return []
            season_id = current_season['id']
        
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, position, is_active, start_time, end_time, status 
                    FROM round 
                    WHERE season_id = :season_id 
                    ORDER BY start_time DESC
                """), {'season_id': season_id})
                
                rounds = []
                for row in result:
                    rounds.append({
                        'id': row[0],
                        'position': row[1],
                        'is_active': row[2],
                        'start_time': row[3],
                        'end_time': row[4],
                        'status': row[5]
                    })
                
                return rounds
                
        except Exception as e:
            logger.error(f"Error getting season rounds: {e}")
            return []
    
    @staticmethod
    def get_team_by_user(user_id, season_id=None):
        """Get user's team in a specific season"""
        if season_id is None:
            current_season = SeasonContext.get_current_season()
            if not current_season:
                return None
            season_id = current_season['id']
        
        try:
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, balance, logo_url, 
                           team_lineage_id, is_continuing_team 
                    FROM team 
                    WHERE user_id = :user_id AND season_id = :season_id
                """), {'user_id': user_id, 'season_id': season_id})
                
                row = result.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'balance': row[2],
                        'logo_url': row[3],
                        'team_lineage_id': row[4],
                        'is_continuing_team': row[5]
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting user team: {e}")
            return None

def season_aware(f):
    """Decorator to make routes season-aware"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Ensure current season is available in template context
        current_season = SeasonContext.get_current_season()
        g.current_season = current_season
        
        # Add season context to kwargs if requested
        if 'season_context' in f.__code__.co_varnames:
            kwargs['season_context'] = SeasonContext
        
        return f(*args, **kwargs)
    return decorated_function

def get_current_season_id():
    """Helper function to get current season ID"""
    season = SeasonContext.get_current_season()
    return season['id'] if season else None

def get_user_current_team(user_id):
    """Helper function to get user's team in current season"""
    return SeasonContext.get_team_by_user(user_id)
