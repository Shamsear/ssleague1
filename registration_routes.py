"""
Team Registration Routes for Multi-Season System
================================================
Handles team registration for new seasons, including continuing teams.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Team, Season
from season_context import SeasonContext
from datetime import datetime

registration_bp = Blueprint('registration', __name__, url_prefix='/registration')

def registration_open_required(f):
    """Decorator to check if registration is open for any season"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to register a team.', 'error')
            return redirect(url_for('login'))
        
        # Check if any season has registration open
        try:
            with db.engine.connect() as conn:
                result = conn.execute("""
                    SELECT COUNT(*) FROM season 
                    WHERE registration_open = true AND status IN ('upcoming', 'active')
                """)
                open_seasons = result.fetchone()[0]
                
                if open_seasons == 0:
                    flash('Team registration is not currently open for any season.', 'error')
                    return redirect(url_for('dashboard'))
                    
        except Exception as e:
            current_app.logger.error(f"Error checking registration status: {e}")
            flash('Error checking registration status.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@registration_bp.route('/')
@login_required
@registration_open_required
def registration_home():
    """Main registration page showing available seasons"""
    try:
        # Get seasons with open registration
        with db.engine.connect() as conn:
            seasons_result = conn.execute("""
                SELECT 
                    s.id, s.name, s.short_name, s.description,
                    s.team_limit, s.registration_deadline,
                    s.season_start_date, s.season_end_date,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as current_teams
                FROM season s
                WHERE s.registration_open = true 
                  AND s.status IN ('upcoming', 'active')
                ORDER BY s.season_start_date ASC
            """)
            open_seasons = seasons_result.fetchall()
        
        # Get user's current team info for continuing team options
        current_season = SeasonContext.get_current_season()
        user_current_team = None
        if current_season:
            user_current_team = SeasonContext.get_team_by_user(current_user.id, current_season['id'])
        
        # Get user's existing registrations
        with db.engine.connect() as conn:
            existing_regs = conn.execute("""
                SELECT t.season_id, s.name, t.name as team_name, t.is_continuing_team
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.user_id = %s
                ORDER BY s.created_at DESC
            """, (current_user.id,))
            user_registrations = existing_regs.fetchall()
        
        return render_template('registration/home.html',
                             open_seasons=open_seasons,
                             user_current_team=user_current_team,
                             user_registrations=user_registrations)
        
    except Exception as e:
        current_app.logger.error(f"Error in registration home: {e}")
        flash('Error loading registration page.', 'error')
        return redirect(url_for('dashboard'))

@registration_bp.route('/season/<int:season_id>')
@login_required 
@registration_open_required
def season_registration(season_id):
    """Registration form for a specific season"""
    try:
        # Get season details
        with db.engine.connect() as conn:
            season_result = conn.execute("""
                SELECT 
                    s.id, s.name, s.short_name, s.description,
                    s.team_limit, s.registration_deadline, s.registration_open,
                    s.season_start_date, s.season_end_date,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as current_teams
                FROM season s
                WHERE s.id = %s
            """, (season_id,))
            season_data = season_result.fetchone()
        
        if not season_data:
            flash('Season not found.', 'error')
            return redirect(url_for('registration.registration_home'))
        
        if not season_data[6]:  # registration_open
            flash('Registration is not open for this season.', 'error')
            return redirect(url_for('registration.registration_home'))
        
        # Check if user already registered for this season
        with db.engine.connect() as conn:
            existing_reg = conn.execute("""
                SELECT id, name FROM team 
                WHERE user_id = %s AND season_id = %s
            """, (current_user.id, season_id))
            existing_team = existing_reg.fetchone()
        
        if existing_team:
            flash(f'You have already registered team "{existing_team[1]}" for this season.', 'warning')
            return redirect(url_for('registration.registration_home'))
        
        # Get user's current team for continuing option
        current_season = SeasonContext.get_current_season()
        user_current_team = None
        can_continue = False
        
        if current_season and current_season['id'] != season_id:
            user_current_team = SeasonContext.get_team_by_user(current_user.id, current_season['id'])
            can_continue = user_current_team is not None
        
        return render_template('registration/season_form.html',
                             season=season_data,
                             user_current_team=user_current_team,
                             can_continue=can_continue)
        
    except Exception as e:
        current_app.logger.error(f"Error in season registration: {e}")
        flash('Error loading season registration.', 'error')
        return redirect(url_for('registration.registration_home'))

@registration_bp.route('/season/<int:season_id>/submit', methods=['POST'])
@login_required
@registration_open_required
def submit_registration(season_id):
    """Process team registration submission"""
    try:
        # Get season details
        with db.engine.connect() as conn:
            season_result = conn.execute("""
                SELECT s.id, s.name, s.registration_open, s.team_limit,
                       (SELECT COUNT(*) FROM team WHERE season_id = s.id) as current_teams
                FROM season s WHERE s.id = %s
            """, (season_id,))
            season_data = season_result.fetchone()
        
        if not season_data or not season_data[2]:  # registration_open
            flash('Registration is not open for this season.', 'error')
            return redirect(url_for('registration.registration_home'))
        
        # Check team limit
        if season_data[3] and season_data[4] >= season_data[3]:  # team_limit and current_teams
            flash('This season has reached its team limit.', 'error')
            return redirect(url_for('registration.season_registration', season_id=season_id))
        
        # Check if user already registered
        with db.engine.connect() as conn:
            existing_check = conn.execute("""
                SELECT id FROM team WHERE user_id = %s AND season_id = %s
            """, (current_user.id, season_id))
            if existing_check.fetchone():
                flash('You have already registered for this season.', 'error')
                return redirect(url_for('registration.registration_home'))
        
        # Get form data
        registration_type = request.form.get('registration_type', 'new')
        team_name = request.form.get('team_name', '').strip()
        
        if not team_name:
            flash('Team name is required.', 'error')
            return redirect(url_for('registration.season_registration', season_id=season_id))
        
        # Check for duplicate team name in this season
        with db.engine.connect() as conn:
            name_check = conn.execute("""
                SELECT id FROM team WHERE season_id = %s AND LOWER(name) = LOWER(%s)
            """, (season_id, team_name))
            if name_check.fetchone():
                flash('A team with this name already exists in this season.', 'error')
                return redirect(url_for('registration.season_registration', season_id=season_id))
        
        new_team_id = None
        
        if registration_type == 'continue':
            # Continuing team registration
            current_season = SeasonContext.get_current_season()
            if not current_season:
                flash('No current season found for team continuation.', 'error')
                return redirect(url_for('registration.season_registration', season_id=season_id))
            
            user_current_team = SeasonContext.get_team_by_user(current_user.id, current_season['id'])
            if not user_current_team:
                flash('You do not have a team in the current season to continue.', 'error')
                return redirect(url_for('registration.season_registration', season_id=season_id))
            
            # Use database function to create continuing team
            with db.engine.connect() as conn:
                result = conn.execute("""
                    SELECT create_continuing_team(%s, %s, %s, %s)
                """, (user_current_team['id'], season_id, team_name, current_user.id))
                new_team_id = result.fetchone()[0]
                conn.commit()
            
            flash(f'Successfully registered continuing team "{team_name}" for {season_data[1]}!', 'success')
            
        else:
            # New team registration
            with db.engine.connect() as conn:
                result = conn.execute("""
                    SELECT create_new_team(%s, %s, %s)
                """, (team_name, current_user.id, season_id))
                new_team_id = result.fetchone()[0]
                conn.commit()
            
            flash(f'Successfully registered new team "{team_name}" for {season_data[1]}!', 'success')
        
        # Log the registration
        current_app.logger.info(f"Team registration: User {current_user.id} registered team '{team_name}' (ID: {new_team_id}) for season {season_id}")
        
        return redirect(url_for('registration.registration_success', team_id=new_team_id))
        
    except Exception as e:
        current_app.logger.error(f"Error in registration submission: {e}")
        flash('Error processing registration. Please try again.', 'error')
        return redirect(url_for('registration.season_registration', season_id=season_id))

@registration_bp.route('/success/<int:team_id>')
@login_required
def registration_success(team_id):
    """Registration success page"""
    try:
        # Get team and season details
        with db.engine.connect() as conn:
            team_result = conn.execute("""
                SELECT 
                    t.id, t.name, t.is_continuing_team, t.team_lineage_id,
                    s.name as season_name, s.short_name,
                    s.season_start_date, s.registration_deadline
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.id = %s AND t.user_id = %s
            """, (team_id, current_user.id))
            team_data = team_result.fetchone()
        
        if not team_data:
            flash('Team not found.', 'error')
            return redirect(url_for('registration.registration_home'))
        
        # Get lineage history if continuing team
        lineage_history = []
        if team_data[2] and team_data[3]:  # is_continuing_team and team_lineage_id
            with db.engine.connect() as conn:
                history_result = conn.execute("""
                    SELECT * FROM get_team_lineage_history(%s)
                """, (team_data[3],))
                lineage_history = history_result.fetchall()
        
        return render_template('registration/success.html',
                             team=team_data,
                             lineage_history=lineage_history)
        
    except Exception as e:
        current_app.logger.error(f"Error in registration success: {e}")
        flash('Error loading registration confirmation.', 'error')
        return redirect(url_for('registration.registration_home'))

@registration_bp.route('/my-teams')
@login_required
def my_teams():
    """Show user's registered teams across all seasons"""
    try:
        # Get all user's teams
        with db.engine.connect() as conn:
            teams_result = conn.execute("""
                SELECT 
                    t.id, t.name, t.balance, t.is_continuing_team, t.team_lineage_id,
                    s.name as season_name, s.short_name, s.is_active, s.status,
                    s.season_start_date, s.season_end_date,
                    (SELECT COUNT(*) FROM team WHERE team_lineage_id = t.team_lineage_id) as lineage_count
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.user_id = %s
                ORDER BY s.created_at DESC, t.created_at DESC
            """, (current_user.id,))
            user_teams = teams_result.fetchall()
        
        return render_template('registration/my_teams.html', user_teams=user_teams)
        
    except Exception as e:
        current_app.logger.error(f"Error loading user teams: {e}")
        flash('Error loading your teams.', 'error')
        return redirect(url_for('dashboard'))

@registration_bp.route('/team/<int:team_id>/history')
@login_required
def team_history(team_id):
    """Show team lineage history"""
    try:
        # Verify team belongs to user
        with db.engine.connect() as conn:
            team_check = conn.execute("""
                SELECT t.id, t.name, t.team_lineage_id, t.is_continuing_team,
                       s.name as season_name
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.id = %s AND t.user_id = %s
            """, (team_id, current_user.id))
            team_data = team_check.fetchone()
        
        if not team_data:
            flash('Team not found.', 'error')
            return redirect(url_for('registration.my_teams'))
        
        lineage_history = []
        if team_data[2]:  # team_lineage_id
            with db.engine.connect() as conn:
                history_result = conn.execute("""
                    SELECT * FROM get_team_lineage_history(%s)
                """, (team_data[2],))
                lineage_history = history_result.fetchall()
        
        return render_template('registration/team_history.html',
                             team=team_data,
                             lineage_history=lineage_history)
        
    except Exception as e:
        current_app.logger.error(f"Error loading team history: {e}")
        flash('Error loading team history.', 'error')
        return redirect(url_for('registration.my_teams'))
