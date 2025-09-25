"""
Admin Routes for Multi-Season System
====================================
Provides admin interfaces for season and user management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Team, Season
from sqlalchemy import text
from season_context import SeasonContext
from access_control import require_admin, require_super_admin, restrict_committee_admin_from_super_routes, debug_user_access
import secrets
import string
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/debug-access')
@login_required
def debug_access():
    """Debug route to check user access levels"""
    access_info = debug_user_access()
    return jsonify(access_info)

# Old decorators replaced with enhanced access control system
# Using require_admin and require_super_admin from access_control.py

@admin_bp.route('/')
@restrict_committee_admin_from_super_routes
def admin_dashboard():
    """Admin dashboard showing system overview"""
    try:
        # Get current season info
        current_season = SeasonContext.get_current_season()
        
        # Get season statistics manually since get_season_statistics() function may not exist
        season_stats = None
        if current_season:
            try:
                with db.engine.connect() as conn:
                    stats_result = conn.execute(text("""
                        SELECT 
                            :season_id as season_id,
                            :season_name as season_name,
                            (SELECT COUNT(*) FROM team WHERE season_id = :season_id) as total_teams,
                            (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = true) as continuing_teams,
                            (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = false) as new_teams,
                            (SELECT COUNT(*) FROM round WHERE season_id = :season_id) as total_rounds,
                            (SELECT COUNT(*) FROM round WHERE season_id = :season_id AND is_active = true) as active_rounds,
                            (SELECT COUNT(*) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as total_bids
                    """), {'season_id': current_season['id'], 'season_name': current_season['name']})
                    season_stats = stats_result.fetchone()
            except Exception as e:
                current_app.logger.error(f"Error getting season statistics: {e}")
                season_stats = None
        
        # Get user role statistics
        with db.engine.connect() as conn:
            role_result = conn.execute(text("""
                SELECT user_role as role, COUNT(*) as count 
                FROM "user" 
                GROUP BY user_role 
                ORDER BY CASE user_role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_user' THEN 3 
                    ELSE 4 END
            """))
            role_stats = role_result.fetchall()
        
        # Get recent activity (placeholder for now)
        recent_activity = []
        
        return render_template('admin/dashboard.html', 
                             current_season=current_season,
                             season_stats=season_stats,
                             role_stats=role_stats,
                             recent_activity=recent_activity)
        
    except Exception as e:
        current_app.logger.error(f"Error in admin dashboard: {e}")
        flash('Error loading admin dashboard.', 'error')
        return redirect(url_for('dashboard'))

@admin_bp.route('/seasons')
@require_admin
def season_management():
    """Season management interface"""
    try:
        # Get all seasons
        with db.engine.connect() as conn:
            seasons_result = conn.execute(text("""
                SELECT 
                    s.id, s.name, s.short_name, s.is_active, s.status, 
                    s.created_at,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as team_count,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as round_count
                FROM season s
                ORDER BY s.created_at DESC
            """))
            seasons = seasons_result.fetchall()
        
        return render_template('admin/seasons.html', seasons=seasons)
        
    except Exception as e:
        current_app.logger.error(f"Error in season management: {e}")
        flash('Error loading season management.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/seasons/create', methods=['GET', 'POST'])
@require_super_admin
def create_season():
    """Create a new season"""
    if request.method == 'POST':
        try:
            season_name = request.form.get('season_name', '').strip()
            short_name = request.form.get('short_name', '').strip()
            description = request.form.get('description', '').strip()
            team_limit = request.form.get('team_limit', type=int)
            max_committee_admins = request.form.get('max_committee_admins', type=int)
            
            if not season_name or not short_name:
                flash('Season name and short name are required.', 'error')
                return render_template('admin/create_season.html')
            
            # Create season using database query
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO season (
                        name, short_name, is_active, status,
                        created_at, updated_at
                    ) VALUES (:season_name, :short_name, :is_active, :status,
                             :created_at, :updated_at)
                    RETURNING id
                """), {
                    'season_name': season_name, 
                    'short_name': short_name, 
                    'is_active': False, 
                    'status': 'upcoming',
                    'created_at': datetime.utcnow(), 
                    'updated_at': datetime.utcnow()
                })
                season_id = result.fetchone()[0]
                conn.commit()
            
            flash(f'Season "{season_name}" created successfully!', 'success')
            return redirect(url_for('admin.season_management'))
            
        except Exception as e:
            current_app.logger.error(f"Error creating season: {e}")
            flash('Error creating season. Please try again.', 'error')
    
    return render_template('admin/create_season.html')

@admin_bp.route('/seasons/<int:season_id>/activate', methods=['POST'])
@require_super_admin
def activate_season(season_id):
    """Activate a season (deactivates all others)"""
    try:
        with db.engine.connect() as conn:
            # Deactivate all seasons
            conn.execute(text("UPDATE season SET is_active = false"))
            
            # Activate the selected season
            conn.execute(text("""
                UPDATE season 
                SET is_active = true, status = 'active', updated_at = :updated_at 
                WHERE id = :season_id
            """), {'updated_at': datetime.utcnow(), 'season_id': season_id})
            
            conn.commit()
        
        flash('Season activated successfully!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error activating season: {e}")
        flash('Error activating season.', 'error')
    
    return redirect(url_for('admin.season_management'))

@admin_bp.route('/users')
@require_admin
def user_management():
    """User management interface"""
    try:
        # Get all users with their roles and teams
        with db.engine.connect() as conn:
            users_result = conn.execute(text("""
                SELECT 
                    u.id, u.username, u.email, u.user_role, u.is_admin, u.is_approved,
                    u.profile_updated_at,
                    t.id as team_id, t.name as team_name, s.name as season_name
                FROM "user" u
                LEFT JOIN team t ON u.id = t.user_id 
                    AND t.season_id = (SELECT id FROM season WHERE is_active = true LIMIT 1)
                LEFT JOIN season s ON t.season_id = s.id
                ORDER BY u.user_role, u.username
            """))
            users = users_result.fetchall()
        
        return render_template('admin/users.html', users=users)
        
    except Exception as e:
        current_app.logger.error(f"Error in user management: {e}")
        flash('Error loading user management.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/<int:user_id>/promote', methods=['POST'])
@require_super_admin
def promote_user(user_id):
    """Promote user to committee admin"""
    try:
        with db.engine.connect() as conn:
            # Simple promotion - update user role directly
            result = conn.execute(text("""
                UPDATE "user" 
                SET user_role = 'committee_admin', updated_at = :updated_at 
                WHERE id = :user_id AND user_role = 'team_user'
            """), {'user_id': user_id, 'updated_at': datetime.utcnow()})
            
            if result.rowcount > 0:
                conn.commit()
                flash('User promoted to committee admin successfully!', 'success')
            else:
                flash('User could not be promoted. They may already be an admin.', 'error')
        
    except Exception as e:
        current_app.logger.error(f"Error promoting user: {e}")
        flash('Error promoting user.', 'error')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/users/<int:user_id>/demote', methods=['POST'])
@require_super_admin
def demote_user(user_id):
    """Demote user from admin role"""
    try:
        with db.engine.connect() as conn:
            # Simple demotion - update user role directly
            result = conn.execute(text("""
                UPDATE "user" 
                SET user_role = 'team_user', updated_at = :updated_at 
                WHERE id = :user_id AND user_role = 'committee_admin'
            """), {'user_id': user_id, 'updated_at': datetime.utcnow()})
            
            if result.rowcount > 0:
                conn.commit()
                flash('User demoted to team member successfully!', 'success')
            else:
                flash('User could not be demoted. They may not be a committee admin.', 'error')
        
    except Exception as e:
        current_app.logger.error(f"Error demoting user: {e}")
        flash('Error demoting user.', 'error')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/invites')
@require_admin
def admin_invites():
    """Admin invite management"""
    try:
        # Get active admin invites - table may not exist yet
        invites = []
        try:
            with db.engine.connect() as conn:
                invites_result = conn.execute(text("""
                    SELECT 
                        ai.id, ai.invite_token, ai.expires_at, ai.max_uses, 
                        ai.current_uses, ai.is_active, ai.description,
                        ai.created_at, u.username as created_by_username
                    FROM admin_invite ai
                    JOIN "user" u ON ai.created_by = u.id
                    WHERE ai.is_active = true
                    ORDER BY ai.created_at DESC
                """))
                invites = invites_result.fetchall()
        except Exception as table_error:
            current_app.logger.warning(f"Admin invite table not found: {table_error}")
            invites = []
        
        return render_template('admin/invites.html', invites=invites)
        
    except Exception as e:
        current_app.logger.error(f"Error loading admin invites: {e}")
        flash('Error loading admin invites.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/invites/create', methods=['POST'])
@require_admin
def create_admin_invite():
    """Create a new admin invite"""
    try:
        description = request.form.get('description', '').strip()
        max_uses = request.form.get('max_uses', 1, type=int)
        expires_hours = request.form.get('expires_hours', 24, type=int)
        
        # Generate random token
        token = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
        
        with db.engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO admin_invite (
                    invite_token, expires_at, max_uses, current_uses,
                    created_by, is_active, description, created_at
                ) VALUES (:token, :expires_at, :max_uses, :current_uses,
                         :created_by, :is_active, :description, :created_at)
            """), {
                'token': token, 
                'expires_at': expires_at, 
                'max_uses': max_uses, 
                'current_uses': 0,
                'created_by': current_user.id, 
                'is_active': True, 
                'description': description, 
                'created_at': datetime.utcnow()
            })
            conn.commit()
        
        # Generate the full registration link
        registration_url = url_for('register', invite=token, _external=True)
        flash(f'Admin invite created successfully! Share this link: {registration_url}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error creating admin invite: {e}")
        flash('Error creating admin invite.', 'error')
    
    return redirect(url_for('admin.admin_invites'))

@admin_bp.route('/seasons/<int:season_id>/details')
@require_admin
def season_details(season_id):
    """Detailed view of a specific season with comprehensive statistics"""
    try:
        with db.engine.connect() as conn:
            # Get season basic info
            season_result = conn.execute(text("""
                SELECT id, name, short_name, is_active, status, created_at, updated_at
                FROM season WHERE id = :season_id
            """), {'season_id': season_id})
            season = season_result.fetchone()
            
            if not season:
                flash('Season not found.', 'error')
                return redirect(url_for('admin.season_management'))
            
            # Get comprehensive season statistics
            stats_result = conn.execute(text("""
                SELECT 
                    -- Team statistics
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id) as total_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = true) as continuing_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = false) as new_teams,
                    
                    -- Round statistics
                    (SELECT COUNT(*) FROM round WHERE season_id = :season_id) as total_rounds,
                    (SELECT COUNT(*) FROM round WHERE season_id = :season_id AND is_active = true) as active_rounds,
                    (SELECT COUNT(*) FROM round WHERE season_id = :season_id AND status = 'completed') as completed_rounds,
                    
                    -- Bid statistics
                    (SELECT COUNT(*) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as total_bids,
                    (SELECT COUNT(DISTINCT b.team_id) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as teams_with_bids,
                    (SELECT COUNT(DISTINCT b.player_id) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as players_bid_on,
                    (SELECT COALESCE(AVG(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as avg_bid_amount,
                    (SELECT COALESCE(MAX(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as max_bid_amount,
                    (SELECT COALESCE(MIN(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as min_bid_amount
            """), {'season_id': season_id})
            season_stats = stats_result.fetchone()
            
            # Get teams with detailed info
            teams_result = conn.execute(text("""
                SELECT 
                    t.id, t.name, t.balance, t.is_continuing_team, 
                    u.username as owner_username,
                    (SELECT COUNT(*) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = t.id AND r.season_id = :season_id) as bid_count,
                    (SELECT COALESCE(SUM(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = t.id AND r.season_id = :season_id) as total_spent
                FROM team t
                JOIN "user" u ON t.user_id = u.id
                WHERE t.season_id = :season_id
                ORDER BY t.name
            """), {'season_id': season_id})
            teams = teams_result.fetchall()
            
            # Get rounds with detailed info
            rounds_result = conn.execute(text("""
                SELECT 
                    r.id, r.position, r.is_active, r.status, r.start_time, r.end_time,
                    (SELECT COUNT(*) FROM bid WHERE round_id = r.id) as bid_count,
                    (SELECT COUNT(DISTINCT team_id) FROM bid WHERE round_id = r.id) as participating_teams,
                    (SELECT COUNT(DISTINCT player_id) FROM bid WHERE round_id = r.id) as players_in_round
                FROM round r
                WHERE r.season_id = :season_id
                ORDER BY r.start_time DESC
            """), {'season_id': season_id})
            rounds = rounds_result.fetchall()
            
            # Get top bids for this season
            top_bids_result = conn.execute(text("""
                SELECT 
                    p.name as player_name, p.position, p.team_name as original_team,
                    b.amount, t.name as bidding_team, r.position as round_position
                FROM bid b
                JOIN player p ON b.player_id = p.id
                JOIN team t ON b.team_id = t.id
                JOIN round r ON b.round_id = r.id
                WHERE r.season_id = :season_id
                ORDER BY b.amount DESC
                LIMIT 10
            """), {'season_id': season_id})
            top_bids = top_bids_result.fetchall()
            
            return render_template('admin/season_details.html',
                                 season=season,
                                 season_stats=season_stats,
                                 teams=teams,
                                 rounds=rounds,
                                 top_bids=top_bids)
            
    except Exception as e:
        current_app.logger.error(f"Error getting season details: {e}")
        flash('Error loading season details.', 'error')
        return redirect(url_for('admin.season_management'))

@admin_bp.route('/seasons/<int:season_id>/rounds/<int:round_id>')
@require_admin
def round_details(season_id, round_id):
    """Detailed view of a specific round with all information"""
    try:
        with db.engine.connect() as conn:
            # Get round basic info with season verification
            round_result = conn.execute(text("""
                SELECT r.id, r.position, r.is_active, r.status, r.start_time, r.end_time, r.duration,
                       r.max_bids_per_team, s.name as season_name, s.short_name as season_short_name
                FROM round r
                JOIN season s ON r.season_id = s.id
                WHERE r.id = :round_id AND r.season_id = :season_id
            """), {'round_id': round_id, 'season_id': season_id})
            round_info = round_result.fetchone()
            
            if not round_info:
                flash('Round not found in this season.', 'error')
                return redirect(url_for('admin.season_details', season_id=season_id))
            
            # Get all bids in this round with player and team details
            bids_result = conn.execute(text("""
                SELECT 
                    b.id, b.amount, b.is_hidden, b.timestamp,
                    p.name as player_name, p.position, p.team_name as original_team,
                    p.overall_rating, p.nationality,
                    t.name as bidding_team, u.username as team_owner,
                    CASE 
                        WHEN EXISTS (SELECT 1 FROM tiebreaker tb WHERE tb.round_id = b.round_id AND tb.player_id = b.player_id) 
                        THEN 'Tiebreaker'
                        WHEN p.team_id = b.team_id 
                        THEN 'Won'
                        ELSE 'Lost'
                    END as bid_status
                FROM bid b
                JOIN player p ON b.player_id = p.id
                JOIN team t ON b.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE b.round_id = :round_id
                ORDER BY b.amount DESC, b.timestamp ASC
            """), {'round_id': round_id})
            bids = bids_result.fetchall()
            
            # Get tiebreakers for this round
            tiebreakers_result = conn.execute(text("""
                SELECT 
                    tb.id, tb.original_amount, tb.resolved, tb.timestamp,
                    p.name as player_name, p.position,
                    COUNT(ttb.team_id) as teams_count,
                    STRING_AGG(t.name, ', ') as team_names
                FROM tiebreaker tb
                JOIN player p ON tb.player_id = p.id
                LEFT JOIN team_tiebreaker ttb ON tb.id = ttb.tiebreaker_id
                LEFT JOIN team t ON ttb.team_id = t.id
                WHERE tb.round_id = :round_id
                GROUP BY tb.id, tb.original_amount, tb.resolved, tb.timestamp, p.name, p.position
                ORDER BY tb.timestamp
            """), {'round_id': round_id})
            tiebreakers = tiebreakers_result.fetchall()
            
            # Get players acquired in this round (final winners)
            acquisitions_result = conn.execute(text("""
                SELECT DISTINCT
                    p.name as player_name, p.position, p.team_name as original_team,
                    p.overall_rating, p.nationality, p.acquisition_value,
                    t.name as new_team, u.username as team_owner
                FROM player p
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE p.round_id = :round_id
                ORDER BY p.acquisition_value DESC
            """), {'round_id': round_id})
            acquisitions = acquisitions_result.fetchall()
            
            # Get round statistics
            stats_result = conn.execute(text("""
                SELECT 
                    (SELECT COUNT(*) FROM bid WHERE round_id = :round_id) as total_bids,
                    (SELECT COUNT(DISTINCT team_id) FROM bid WHERE round_id = :round_id) as participating_teams,
                    (SELECT COUNT(DISTINCT player_id) FROM bid WHERE round_id = :round_id) as players_bid_on,
                    (SELECT COALESCE(AVG(amount), 0) FROM bid WHERE round_id = :round_id) as avg_bid,
                    (SELECT COALESCE(MAX(amount), 0) FROM bid WHERE round_id = :round_id) as max_bid,
                    (SELECT COALESCE(MIN(amount), 0) FROM bid WHERE round_id = :round_id) as min_bid,
                    (SELECT COUNT(*) FROM tiebreaker WHERE round_id = :round_id) as tiebreaker_count,
                    (SELECT COUNT(*) FROM player WHERE round_id = :round_id) as players_acquired,
                    (SELECT COALESCE(SUM(acquisition_value), 0) FROM player WHERE round_id = :round_id) as total_spent
            """), {'round_id': round_id})
            round_stats = stats_result.fetchone()
            
            # Get bid distribution by team
            team_bids_result = conn.execute(text("""
                SELECT 
                    t.name as team_name, 
                    COUNT(b.id) as bid_count,
                    COALESCE(AVG(b.amount), 0) as avg_bid,
                    COALESCE(SUM(CASE WHEN p.team_id = t.id THEN 1 ELSE 0 END), 0) as players_won,
                    COALESCE(SUM(CASE WHEN p.team_id = t.id THEN p.acquisition_value ELSE 0 END), 0) as total_spent
                FROM team t
                LEFT JOIN bid b ON t.id = b.team_id AND b.round_id = :round_id
                LEFT JOIN player p ON b.player_id = p.id AND p.round_id = :round_id
                WHERE t.season_id = :season_id
                GROUP BY t.id, t.name
                HAVING COUNT(b.id) > 0
                ORDER BY bid_count DESC, total_spent DESC
            """), {'round_id': round_id, 'season_id': season_id})
            team_bids = team_bids_result.fetchall()
            
            return render_template('admin/round_details.html',
                                 round_info=round_info,
                                 bids=bids,
                                 tiebreakers=tiebreakers,
                                 acquisitions=acquisitions,
                                 round_stats=round_stats,
                                 team_bids=team_bids,
                                 season_id=season_id)
            
    except Exception as e:
        current_app.logger.error(f"Error getting round details: {e}")
        flash('Error loading round details.', 'error')
        return redirect(url_for('admin.season_details', season_id=season_id))

@admin_bp.route('/seasons/<int:season_id>/teams/<int:team_id>')
@require_admin
def team_details(season_id, team_id):
    """Comprehensive team details with all statistics and player information"""
    try:
        with db.engine.connect() as conn:
            # Get team basic info with season verification
            team_result = conn.execute(text("""
                SELECT t.id, t.name, t.balance, t.is_continuing_team, t.team_lineage_id,
                       t.logo_url, t.logo_storage_type,
                       u.username as owner_username, u.email as owner_email,
                       s.name as season_name, s.short_name as season_short_name
                FROM team t
                JOIN "user" u ON t.user_id = u.id
                JOIN season s ON t.season_id = s.id
                WHERE t.id = :team_id AND t.season_id = :season_id
            """), {'team_id': team_id, 'season_id': season_id})
            team_info = team_result.fetchone()
            
            if not team_info:
                flash('Team not found in this season.', 'error')
                return redirect(url_for('admin.season_details', season_id=season_id))
            
            # Get team statistics
            stats_result = conn.execute(text("""
                SELECT 
                    -- Bidding statistics
                    (SELECT COUNT(*) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = :team_id AND r.season_id = :season_id) as total_bids,
                    (SELECT COUNT(DISTINCT b.round_id) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = :team_id AND r.season_id = :season_id) as rounds_participated,
                    (SELECT COALESCE(AVG(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = :team_id AND r.season_id = :season_id) as avg_bid,
                    (SELECT COALESCE(MAX(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = :team_id AND r.season_id = :season_id) as max_bid,
                    (SELECT COALESCE(MIN(b.amount), 0) FROM bid b JOIN round r ON b.round_id = r.id WHERE b.team_id = :team_id AND r.season_id = :season_id) as min_bid,
                    
                    -- Player acquisition statistics
                    (SELECT COUNT(*) FROM player p JOIN round r ON p.round_id = r.id WHERE p.team_id = :team_id AND r.season_id = :season_id) as players_acquired,
                    (SELECT COALESCE(SUM(p.acquisition_value), 0) FROM player p JOIN round r ON p.round_id = r.id WHERE p.team_id = :team_id AND r.season_id = :season_id) as total_spent,
                    (SELECT COALESCE(AVG(p.acquisition_value), 0) FROM player p JOIN round r ON p.round_id = r.id WHERE p.team_id = :team_id AND r.season_id = :season_id) as avg_player_cost,
                    
                    -- Tiebreaker statistics
                    (SELECT COUNT(*) FROM team_tiebreaker tt JOIN tiebreaker tb ON tt.tiebreaker_id = tb.id JOIN round r ON tb.round_id = r.id WHERE tt.team_id = :team_id AND r.season_id = :season_id) as tiebreakers_involved,
                    
                    -- Current balance (already calculated)
                    :current_balance as remaining_balance
            """), {'team_id': team_id, 'season_id': season_id, 'current_balance': team_info[2]})
            team_stats = stats_result.fetchone()
            
            # Get all players acquired by this team
            players_result = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.playing_style,
                    r.position as round_position, r.start_time,
                    p.offensive_awareness, p.ball_control, p.dribbling, p.finishing,
                    p.speed, p.physical_contact, p.defensive_awareness, p.tackling
                FROM player p
                JOIN round r ON p.round_id = r.id
                WHERE p.team_id = :team_id AND r.season_id = :season_id
                ORDER BY r.start_time ASC, p.acquisition_value DESC
            """), {'team_id': team_id, 'season_id': season_id})
            players = players_result.fetchall()
            
            # Get bidding history by round
            bidding_history = conn.execute(text("""
                SELECT 
                    r.id as round_id, r.position as round_position, r.start_time,
                    COUNT(b.id) as bids_placed,
                    COALESCE(AVG(b.amount), 0) as avg_bid_amount,
                    COALESCE(MAX(b.amount), 0) as max_bid_amount,
                    COUNT(CASE WHEN p.team_id = :team_id THEN 1 END) as players_won,
                    COALESCE(SUM(CASE WHEN p.team_id = :team_id THEN p.acquisition_value ELSE 0 END), 0) as amount_spent
                FROM round r
                LEFT JOIN bid b ON r.id = b.round_id AND b.team_id = :team_id
                LEFT JOIN player p ON b.player_id = p.id AND p.round_id = r.id
                WHERE r.season_id = :season_id
                GROUP BY r.id, r.position, r.start_time
                HAVING COUNT(b.id) > 0
                ORDER BY r.start_time ASC
            """), {'team_id': team_id, 'season_id': season_id})
            rounds_activity = bidding_history.fetchall()
            
            # Get specific bids for detailed analysis
            all_bids_result = conn.execute(text("""
                SELECT 
                    b.id, b.amount, b.is_hidden, b.timestamp,
                    p.name as player_name, p.position, p.overall_rating,
                    r.position as round_position,
                    CASE 
                        WHEN p.team_id = :team_id THEN 'Won'
                        WHEN EXISTS (SELECT 1 FROM tiebreaker tb WHERE tb.round_id = b.round_id AND tb.player_id = b.player_id) THEN 'Tiebreaker'
                        ELSE 'Lost'
                    END as bid_result
                FROM bid b
                JOIN player p ON b.player_id = p.id
                JOIN round r ON b.round_id = r.id
                WHERE b.team_id = :team_id AND r.season_id = :season_id
                ORDER BY b.timestamp DESC
            """), {'team_id': team_id, 'season_id': season_id})
            all_bids = all_bids_result.fetchall()
            
            # Get players by position for squad analysis
            squad_analysis = conn.execute(text("""
                SELECT 
                    p.position,
                    COUNT(*) as player_count,
                    COALESCE(AVG(p.overall_rating), 0) as avg_rating,
                    COALESCE(SUM(p.acquisition_value), 0) as total_spent_position,
                    COALESCE(AVG(p.acquisition_value), 0) as avg_cost_position
                FROM player p
                JOIN round r ON p.round_id = r.id
                WHERE p.team_id = :team_id AND r.season_id = :season_id
                GROUP BY p.position
                ORDER BY total_spent_position DESC
            """), {'team_id': team_id, 'season_id': season_id})
            position_breakdown = squad_analysis.fetchall()
            
            # Get tiebreaker history
            tiebreaker_history = conn.execute(text("""
                SELECT 
                    tb.id, tb.original_amount, tb.resolved,
                    p.name as player_name, p.position,
                    r.position as round_position,
                    tt.new_amount, tt.timestamp
                FROM team_tiebreaker tt
                JOIN tiebreaker tb ON tt.tiebreaker_id = tb.id
                JOIN player p ON tb.player_id = p.id
                JOIN round r ON tb.round_id = r.id
                WHERE tt.team_id = :team_id AND r.season_id = :season_id
                ORDER BY tt.timestamp DESC
            """), {'team_id': team_id, 'season_id': season_id})
            tiebreakers = tiebreaker_history.fetchall()
            
            return render_template('admin/team_details.html',
                                 team_info=team_info,
                                 team_stats=team_stats,
                                 players=players,
                                 rounds_activity=rounds_activity,
                                 all_bids=all_bids,
                                 position_breakdown=position_breakdown,
                                 tiebreakers=tiebreakers,
                                 season_id=season_id)
            
    except Exception as e:
        current_app.logger.error(f"Error getting team details: {e}")
        flash('Error loading team details.', 'error')
        return redirect(url_for('admin.season_details', season_id=season_id))

@admin_bp.route('/seasons/<int:season_id>/player-stats')
@require_admin
def season_player_stats(season_id):
    """Display comprehensive player statistics and awards for a season"""
    try:
        with db.engine.connect() as conn:
            # Get season info
            season_result = conn.execute(text("""
                SELECT id, name, short_name, created_at, updated_at
                FROM season WHERE id = :season_id
            """), {'season_id': season_id})
            season = season_result.fetchone()
            
            if not season:
                flash('Season not found.', 'error')
                return redirect(url_for('admin.seasons'))
            
            # Top goalscorers (Golden Boot)
            top_scorers = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.finishing, p.offensive_awareness,
                    t.name as current_team, u.username as owner
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE r.season_id = :season_id AND p.finishing IS NOT NULL
                ORDER BY p.finishing DESC, p.offensive_awareness DESC
                LIMIT 20
            """), {'season_id': season_id})
            golden_boot_candidates = top_scorers.fetchall()
            
            # Best goalkeepers (Golden Glove)
            top_keepers = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.defensive_awareness, p.physical_contact,
                    t.name as current_team, u.username as owner
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE r.season_id = :season_id AND p.position = 'GK'
                ORDER BY p.overall_rating DESC, p.defensive_awareness DESC
                LIMIT 10
            """), {'season_id': season_id})
            golden_glove_candidates = top_keepers.fetchall()
            
            # Best overall players (Golden Ball)
            top_players = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.playing_style,
                    t.name as current_team, u.username as owner,
                    p.offensive_awareness, p.ball_control, p.dribbling, p.finishing,
                    p.speed, p.physical_contact, p.defensive_awareness, p.tackling
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE r.season_id = :season_id
                ORDER BY p.overall_rating DESC, p.acquisition_value DESC
                LIMIT 50
            """), {'season_id': season_id})
            golden_ball_candidates = top_players.fetchall()
            
            # Most expensive signings
            most_expensive = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.playing_style,
                    t.name as current_team, u.username as owner,
                    r.position as round_position
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE r.season_id = :season_id
                ORDER BY p.acquisition_value DESC
                LIMIT 20
            """), {'season_id': season_id})
            expensive_signings = most_expensive.fetchall()
            
            # Best value signings (high rating, low cost)
            best_value = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.team_name as original_team, p.overall_rating,
                    p.nationality, p.acquisition_value, p.playing_style,
                    t.name as current_team, u.username as owner,
                    CASE WHEN p.acquisition_value > 0 THEN p.overall_rating::float / p.acquisition_value ELSE 0 END as value_ratio
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                JOIN "user" u ON t.user_id = u.id
                WHERE r.season_id = :season_id AND p.acquisition_value > 0 AND p.overall_rating > 70
                ORDER BY (p.overall_rating::float / p.acquisition_value) DESC, p.overall_rating DESC
                LIMIT 20
            """), {'season_id': season_id})
            value_signings = best_value.fetchall()
            
            # Position-wise statistics
            position_stats = conn.execute(text("""
                SELECT 
                    p.position,
                    COUNT(*) as player_count,
                    AVG(p.overall_rating) as avg_rating,
                    MAX(p.overall_rating) as max_rating,
                    MIN(p.overall_rating) as min_rating,
                    AVG(p.acquisition_value) as avg_cost,
                    MAX(p.acquisition_value) as max_cost,
                    SUM(p.acquisition_value) as total_spent
                FROM player p
                JOIN round r ON p.round_id = r.id
                WHERE r.season_id = :season_id AND p.position IS NOT NULL
                GROUP BY p.position
                ORDER BY total_spent DESC
            """), {'season_id': season_id})
            position_breakdown = position_stats.fetchall()
            
            # Nationality statistics
            nationality_stats = conn.execute(text("""
                SELECT 
                    COALESCE(p.nationality, 'Unknown') as nationality,
                    COUNT(*) as player_count,
                    AVG(p.overall_rating) as avg_rating,
                    SUM(p.acquisition_value) as total_spent,
                    AVG(p.acquisition_value) as avg_cost
                FROM player p
                JOIN round r ON p.round_id = r.id
                WHERE r.season_id = :season_id
                GROUP BY p.nationality
                HAVING COUNT(*) >= 3  -- Only show nationalities with 3+ players
                ORDER BY player_count DESC, total_spent DESC
                LIMIT 20
            """), {'season_id': season_id})
            nationality_breakdown = nationality_stats.fetchall()
            
            # Technical vs Physical players
            player_styles = conn.execute(text("""
                SELECT 
                    p.id, p.name, p.position, p.overall_rating,
                    p.offensive_awareness, p.ball_control, p.dribbling, p.finishing,
                    p.speed, p.physical_contact, p.defensive_awareness, p.tackling,
                    t.name as current_team,
                    -- Technical score (average of technical attributes)
                    (COALESCE(p.offensive_awareness, 0) + COALESCE(p.ball_control, 0) + 
                     COALESCE(p.dribbling, 0) + COALESCE(p.finishing, 0)) / 4.0 as technical_score,
                    -- Physical score (average of physical attributes)
                    (COALESCE(p.speed, 0) + COALESCE(p.physical_contact, 0) + 
                     COALESCE(p.defensive_awareness, 0) + COALESCE(p.tackling, 0)) / 4.0 as physical_score
                FROM player p
                JOIN round r ON p.round_id = r.id
                JOIN team t ON p.team_id = t.id
                WHERE r.season_id = :season_id AND p.overall_rating > 75
                ORDER BY p.overall_rating DESC
                LIMIT 30
            """), {'season_id': season_id})
            player_attributes = player_styles.fetchall()
            
            return render_template('admin/season_player_stats.html',
                                 season=season,
                                 golden_boot_candidates=golden_boot_candidates,
                                 golden_glove_candidates=golden_glove_candidates,
                                 golden_ball_candidates=golden_ball_candidates,
                                 expensive_signings=expensive_signings,
                                 value_signings=value_signings,
                                 position_breakdown=position_breakdown,
                                 nationality_breakdown=nationality_breakdown,
                                 player_attributes=player_attributes)
            
    except Exception as e:
        current_app.logger.error(f"Error getting season player stats: {e}")
        flash('Error loading season player statistics.', 'error')
        return redirect(url_for('admin.season_details', season_id=season_id))

@admin_bp.route('/api/season-stats/<int:season_id>')
@require_admin
def api_season_stats(season_id):
    """API endpoint for season statistics"""
    try:
        with db.engine.connect() as conn:
            # Get season info first
            season_result = conn.execute(text("""
                SELECT id, name FROM season WHERE id = :season_id
            """), {'season_id': season_id})
            season = season_result.fetchone()
            
            if not season:
                return jsonify({'error': 'Season not found'}), 404
            
            # Get statistics manually
            stats_result = conn.execute(text("""
                SELECT 
                    :season_id as season_id,
                    :season_name as season_name,
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id) as total_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = true) as continuing_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = :season_id AND is_continuing_team = false) as new_teams,
                    (SELECT COUNT(*) FROM round WHERE season_id = :season_id) as total_rounds,
                    (SELECT COUNT(*) FROM round WHERE season_id = :season_id AND is_active = true) as active_rounds,
                    (SELECT COUNT(*) FROM bid b JOIN round r ON b.round_id = r.id WHERE r.season_id = :season_id) as total_bids
            """), {'season_id': season_id, 'season_name': season[1]})
            stats = stats_result.fetchone()
            
            return jsonify({
                'season_id': stats[0],
                'season_name': stats[1],
                'total_teams': stats[2],
                'continuing_teams': stats[3],
                'new_teams': stats[4],
                'total_rounds': stats[5],
                'active_rounds': stats[6],
                'total_bids': stats[7]
            })
                
    except Exception as e:
        current_app.logger.error(f"Error getting season stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500
