"""
Historical Data Routes for Multi-Season System
=============================================
Provides interfaces for viewing historical seasons and team performance.
"""

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from models import db
from season_context import SeasonContext
from datetime import datetime

history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/')
@login_required
def history_home():
    """Main history page showing all seasons"""
    try:
        with db.engine.connect() as conn:
            seasons_result = conn.execute("""
                SELECT 
                    s.id, s.name, s.short_name, s.is_active, s.status,
                    s.season_start_date, s.season_end_date, s.created_at,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as team_count,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as round_count,
                    (SELECT COUNT(*) FROM bid WHERE season_id = s.id) as bid_count
                FROM season s
                ORDER BY s.created_at DESC
            """)
            seasons = seasons_result.fetchall()
        
        # Get user's participation across seasons
        user_teams = []
        if current_user.is_authenticated:
            with db.engine.connect() as conn:
                teams_result = conn.execute("""
                    SELECT t.id, t.name, s.name as season_name, s.short_name,
                           t.is_continuing_team, t.team_lineage_id
                    FROM team t
                    JOIN season s ON t.season_id = s.id
                    WHERE t.user_id = %s
                    ORDER BY s.created_at DESC
                """, (current_user.id,))
                user_teams = teams_result.fetchall()
        
        return render_template('history/home.html', 
                             seasons=seasons, user_teams=user_teams)
        
    except Exception as e:
        current_app.logger.error(f"Error in history home: {e}")
        return render_template('history/home.html', seasons=[], user_teams=[])

@history_bp.route('/season/<int:season_id>')
@login_required
def season_detail(season_id):
    """Detailed view of a specific season"""
    try:
        # Get season details
        with db.engine.connect() as conn:
            season_result = conn.execute("""
                SELECT s.id, s.name, s.short_name, s.description, s.is_active,
                       s.status, s.season_start_date, s.season_end_date,
                       s.team_limit, s.max_committee_admins
                FROM season s WHERE s.id = %s
            """, (season_id,))
            season = season_result.fetchone()
        
        if not season:
            return render_template('404.html'), 404
        
        # Get season statistics
        with db.engine.connect() as conn:
            stats_result = conn.execute("SELECT * FROM get_season_statistics(%s)", (season_id,))
            stats = stats_result.fetchone()
        
        # Get teams in this season
        with db.engine.connect() as conn:
            teams_result = conn.execute("""
                SELECT t.id, t.name, t.balance, t.is_continuing_team,
                       u.username, t.team_lineage_id
                FROM team t
                JOIN "user" u ON t.user_id = u.id
                WHERE t.season_id = %s
                ORDER BY t.name
            """, (season_id,))
            teams = teams_result.fetchall()
        
        return render_template('history/season_detail.html', 
                             season=season, stats=stats, teams=teams)
        
    except Exception as e:
        current_app.logger.error(f"Error in season detail: {e}")
        return render_template('404.html'), 404

@history_bp.route('/lineage/<int:lineage_id>')
@login_required
def team_lineage(lineage_id):
    """Complete team lineage history"""
    try:
        with db.engine.connect() as conn:
            lineage_result = conn.execute("SELECT * FROM get_team_lineage_history(%s)", (lineage_id,))
            lineage_history = lineage_result.fetchall()
        
        if not lineage_history:
            return render_template('404.html'), 404
        
        # Get lineage stats
        with db.engine.connect() as conn:
            stats_result = conn.execute("""
                SELECT 
                    COUNT(*) as seasons_participated,
                    MIN(s.season_start_date) as first_season_start,
                    MAX(s.season_end_date) as last_season_end,
                    STRING_AGG(DISTINCT t.name, ', ') as all_names
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.team_lineage_id = %s
            """, (lineage_id,))
            lineage_stats = stats_result.fetchone()
        
        return render_template('history/team_lineage.html',
                             lineage_history=lineage_history,
                             lineage_stats=lineage_stats,
                             lineage_id=lineage_id)
        
    except Exception as e:
        current_app.logger.error(f"Error in team lineage: {e}")
        return render_template('404.html'), 404

@history_bp.route('/analytics')
@login_required
def system_analytics():
    """System-wide analytics and statistics"""
    try:
        # Overall system stats
        with db.engine.connect() as conn:
            system_stats = conn.execute("""
                SELECT 
                    (SELECT COUNT(*) FROM season) as total_seasons,
                    (SELECT COUNT(*) FROM "user") as total_users,
                    (SELECT COUNT(DISTINCT team_lineage_id) FROM team WHERE team_lineage_id IS NOT NULL) as total_lineages,
                    (SELECT COUNT(*) FROM team) as total_teams,
                    (SELECT COUNT(*) FROM round) as total_rounds,
                    (SELECT COUNT(*) FROM bid) as total_bids
            """).fetchone()
        
        # Season progression stats
        with db.engine.connect() as conn:
            season_progression = conn.execute("""
                SELECT 
                    s.name, s.short_name,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as teams,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as rounds,
                    (SELECT COUNT(*) FROM bid WHERE season_id = s.id) as bids
                FROM season s
                ORDER BY s.created_at
            """).fetchall()
        
        # Team type distribution
        with db.engine.connect() as conn:
            team_types = conn.execute("""
                SELECT 
                    is_continuing_team,
                    COUNT(*) as count,
                    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
                FROM team
                GROUP BY is_continuing_team
            """).fetchall()
        
        return render_template('history/analytics.html',
                             system_stats=system_stats,
                             season_progression=season_progression,
                             team_types=team_types)
        
    except Exception as e:
        current_app.logger.error(f"Error in system analytics: {e}")
        return render_template('history/analytics.html',
                             system_stats=None, season_progression=[],
                             team_types=[])
