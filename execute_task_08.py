#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 8 EXECUTOR
====================================
Safely executes Task 8: Create Team Registration System for New Seasons

This script:
✅ Creates team registration routes for new seasons
✅ Handles continuing vs new team registration
✅ Creates registration templates and forms
✅ Integrates with team lineage system
✅ Adds registration status management
✅ Can be run multiple times safely
✅ Includes rollback functionality
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime
import shutil

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')
APP_DIR = r"C:\Drive d\SS\test"
BACKUP_DIR = r"C:\Drive d\SS\test"

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    if not os.path.exists(file_path):
        return None
    
    backup_dir = BACKUP_DIR
    os.makedirs(backup_dir, exist_ok=True)
    
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(backup_dir, f"{filename}.backup_{timestamp}")
    
    shutil.copy2(file_path, backup_path)
    return backup_path

def execute_task_08():
    """Execute Task 8: Create Team Registration System for New Seasons"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 8: Create Team Registration System for New Seasons")
        print("=" * 70)
        
        # Connect to database for verification
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Verifying prerequisites...")
        
        # Check if admin routes and season context exist
        admin_routes_path = os.path.join(APP_DIR, "admin_routes.py")
        season_context_path = os.path.join(APP_DIR, "season_context.py")
        
        if not os.path.exists(admin_routes_path):
            print("❌ admin_routes.py not found! Please complete Task 7 first.")
            return False
            
        if not os.path.exists(season_context_path):
            print("❌ season_context.py not found! Please complete Task 6 first.")
            return False
        
        # Verify team lineage system exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'team' AND column_name = 'team_lineage_id'
        """)
        if not cursor.fetchone():
            print("❌ Team lineage system not found! Please complete Task 5 first.")
            return False
        
        print("   ✅ Prerequisites verified")
        
        print("\n📋 Step 2: Creating team registration routes...")
        
        # Create registration_routes.py
        registration_routes_code = '''"""
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
'''
        
        registration_routes_path = os.path.join(APP_DIR, "registration_routes.py")
        with open(registration_routes_path, 'w') as f:
            f.write(registration_routes_code)
        
        print(f"   ✅ Created registration_routes.py at {registration_routes_path}")
        
        print("\n📋 Step 3: Creating registration templates directory...")
        
        # Create registration templates directory
        templates_dir = os.path.join(APP_DIR, "templates")
        registration_templates_dir = os.path.join(templates_dir, "registration")
        os.makedirs(registration_templates_dir, exist_ok=True)
        
        print(f"   ✅ Created registration templates directory at {registration_templates_dir}")
        
        print("\n📋 Step 4: Creating registration home template...")
        
        # Create registration home template
        registration_home_template = '''{% extends "base.html" %}

{% block title %}Team Registration{% endblock %}

{% block content %}
<div class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <!-- Page Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Team Registration</h1>
            <p class="mt-2 text-gray-600">Register your team for upcoming seasons</p>
        </div>

        <!-- Current Season Info -->
        {% if current_season %}
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
            <div class="flex items-center justify-between">
                <div>
                    <h2 class="text-xl font-semibold text-blue-900">{{ format_season_name(current_season) }}</h2>
                    <p class="text-blue-700">Current Active Season</p>
                    {% if user_current_team %}
                        <div class="mt-2 text-sm text-blue-600">
                            <i class="fas fa-users mr-1"></i>Your team: {{ get_team_lineage_display(user_current_team) }}
                        </div>
                    {% endif %}
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Available Seasons for Registration -->
        {% if open_seasons %}
        <div class="bg-white shadow overflow-hidden sm:rounded-md mb-8">
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">Available Seasons</h3>
                <p class="text-sm text-gray-600">Choose a season to register your team</p>
            </div>
            
            <ul class="divide-y divide-gray-200">
                {% for season in open_seasons %}
                <li class="px-6 py-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="flex items-center">
                                <h3 class="text-lg font-medium text-gray-900">{{ season[1] }}</h3>
                                <span class="ml-3 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                                    {{ season[2] }}
                                </span>
                                <span class="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                    Registration Open
                                </span>
                            </div>
                            {% if season[3] %}
                            <p class="mt-2 text-sm text-gray-600">{{ season[3] }}</p>
                            {% endif %}
                            <div class="mt-2 flex items-center space-x-6 text-sm text-gray-500">
                                {% if season[4] %}
                                    <span><i class="fas fa-users mr-1"></i>{{ season[8] }}/{{ season[4] }} teams</span>
                                {% else %}
                                    <span><i class="fas fa-users mr-1"></i>{{ season[8] }} teams registered</span>
                                {% endif %}
                                {% if season[5] %}
                                    <span><i class="fas fa-calendar mr-1"></i>Deadline: {{ season[5].strftime('%Y-%m-%d') }}</span>
                                {% endif %}
                                {% if season[6] and season[7] %}
                                    <span><i class="fas fa-play mr-1"></i>{{ season[6].strftime('%Y-%m-%d') }} - {{ season[7].strftime('%Y-%m-%d') }}</span>
                                {% endif %}
                            </div>
                        </div>
                        
                        <div class="flex items-center space-x-2">
                            {% if season[4] and season[8] >= season[4] %}
                                <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                    <i class="fas fa-ban mr-1"></i>Full
                                </span>
                            {% else %}
                                <a href="{{ url_for('registration.season_registration', season_id=season[0]) }}" 
                                   class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                                    <i class="fas fa-plus mr-2"></i>Register Team
                                </a>
                            {% endif %}
                        </div>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% else %}
        <div class="bg-white shadow sm:rounded-lg">
            <div class="px-6 py-8 text-center">
                <i class="fas fa-calendar-times text-4xl text-gray-400 mb-4"></i>
                <h3 class="text-lg font-medium text-gray-900 mb-2">No Open Registration</h3>
                <p class="text-gray-500">There are currently no seasons open for team registration.</p>
                <p class="text-gray-500 mt-2">Check back later or contact an administrator.</p>
            </div>
        </div>
        {% endif %}

        <!-- User's Existing Registrations -->
        {% if user_registrations %}
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">Your Registered Teams</h3>
            </div>
            
            <ul class="divide-y divide-gray-200">
                {% for reg in user_registrations %}
                <li class="px-6 py-4">
                    <div class="flex items-center justify-between">
                        <div>
                            <div class="flex items-center">
                                <h4 class="text-md font-medium text-gray-900">{{ reg[2] }}</h4>
                                {% if reg[3] %}
                                    <span class="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                                        <i class="fas fa-arrow-right mr-1"></i>Continuing
                                    </span>
                                {% else %}
                                    <span class="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                        <i class="fas fa-star mr-1"></i>New
                                    </span>
                                {% endif %}
                            </div>
                            <p class="text-sm text-gray-600">{{ reg[1] }}</p>
                        </div>
                        <div class="flex items-center space-x-2">
                            <a href="{{ url_for('registration.my_teams') }}" 
                               class="text-indigo-600 hover:text-indigo-700 text-sm">
                                View Details
                            </a>
                        </div>
                    </div>
                </li>
                {% endfor %}
            </ul>
            
            <div class="px-6 py-3 bg-gray-50 border-t border-gray-200">
                <a href="{{ url_for('registration.my_teams') }}" 
                   class="text-indigo-600 hover:text-indigo-700 text-sm font-medium">
                    View All Teams <i class="fas fa-arrow-right ml-1"></i>
                </a>
            </div>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}'''
        
        registration_home_path = os.path.join(registration_templates_dir, "home.html")
        with open(registration_home_path, 'w') as f:
            f.write(registration_home_template)
        
        print(f"   ✅ Created registration home template")
        
        print("\n📋 Step 5: Creating season registration form template...")
        
        # Create season registration form template
        season_form_template = '''{% extends "base.html" %}

{% block title %}Register for {{ season[1] }}{% endblock %}

{% block content %}
<div class="min-h-screen bg-gray-50">
    <div class="max-w-3xl mx-auto py-6 sm:px-6 lg:px-8">
        <!-- Back Link -->
        <div class="mb-4">
            <a href="{{ url_for('registration.registration_home') }}" 
               class="text-indigo-600 hover:text-indigo-700 text-sm font-medium">
                <i class="fas fa-arrow-left mr-1"></i>Back to Registration
            </a>
        </div>

        <!-- Page Header -->
        <div class="bg-white shadow sm:rounded-lg mb-6">
            <div class="px-6 py-4">
                <h1 class="text-2xl font-bold text-gray-900">Register for {{ season[1] }}</h1>
                <div class="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                    <span><i class="fas fa-calendar mr-1"></i>{{ season[2] }}</span>
                    {% if season[4] %}
                        <span><i class="fas fa-users mr-1"></i>{{ season[8] }}/{{ season[4] }} teams</span>
                    {% endif %}
                    {% if season[5] %}
                        <span><i class="fas fa-clock mr-1"></i>Deadline: {{ season[5].strftime('%B %d, %Y') }}</span>
                    {% endif %}
                </div>
                {% if season[3] %}
                <p class="mt-3 text-gray-700">{{ season[3] }}</p>
                {% endif %}
            </div>
        </div>

        <!-- Registration Form -->
        <form method="POST" action="{{ url_for('registration.submit_registration', season_id=season[0]) }}" 
              class="bg-white shadow sm:rounded-lg">
            <div class="px-6 py-4">
                <h2 class="text-lg font-medium text-gray-900 mb-4">Team Registration Details</h2>

                <!-- Registration Type Selection -->
                <div class="mb-6">
                    <fieldset>
                        <legend class="text-base font-medium text-gray-900 mb-4">Registration Type</legend>
                        <div class="space-y-4">
                            <!-- New Team Option -->
                            <div class="flex items-start">
                                <div class="flex items-center h-5">
                                    <input id="new_team" name="registration_type" type="radio" value="new" 
                                           class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300" 
                                           checked>
                                </div>
                                <div class="ml-3 text-sm">
                                    <label for="new_team" class="font-medium text-gray-700">
                                        <i class="fas fa-star mr-1 text-blue-500"></i>Register New Team
                                    </label>
                                    <p class="text-gray-500">Create a completely new team for this season</p>
                                </div>
                            </div>

                            <!-- Continue Team Option -->
                            {% if can_continue %}
                            <div class="flex items-start">
                                <div class="flex items-center h-5">
                                    <input id="continue_team" name="registration_type" type="radio" value="continue" 
                                           class="focus:ring-indigo-500 h-4 w-4 text-indigo-600 border-gray-300">
                                </div>
                                <div class="ml-3 text-sm">
                                    <label for="continue_team" class="font-medium text-gray-700">
                                        <i class="fas fa-arrow-right mr-1 text-green-500"></i>Continue Existing Team
                                    </label>
                                    <p class="text-gray-500">
                                        Continue your current team: <strong>{{ user_current_team.name }}</strong>
                                        {% if user_current_team.team_lineage_id %}
                                            (Lineage #{{ user_current_team.team_lineage_id }})
                                        {% endif %}
                                    </p>
                                </div>
                            </div>
                            {% else %}
                            <div class="flex items-start opacity-50">
                                <div class="flex items-center h-5">
                                    <input type="radio" disabled class="h-4 w-4 text-gray-400 border-gray-300">
                                </div>
                                <div class="ml-3 text-sm">
                                    <label class="font-medium text-gray-500">
                                        <i class="fas fa-arrow-right mr-1"></i>Continue Existing Team
                                    </label>
                                    <p class="text-gray-400">You don't have a team in the current season to continue</p>
                                </div>
                            </div>
                            {% endif %}
                        </div>
                    </fieldset>
                </div>

                <!-- Team Name Input -->
                <div class="mb-6">
                    <label for="team_name" class="block text-sm font-medium text-gray-700 mb-2">
                        Team Name <span class="text-red-500">*</span>
                    </label>
                    <input type="text" id="team_name" name="team_name" required maxlength="50"
                           {% if can_continue %}value="{{ user_current_team.name if user_current_team else '' }}"{% endif %}
                           class="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                           placeholder="Enter your team name">
                    <p class="mt-1 text-xs text-gray-500">
                        Choose a unique name for your team in this season (max 50 characters)
                    </p>
                </div>

                <!-- Team Continuation Info -->
                {% if can_continue %}
                <div id="continue_info" class="mb-6 p-4 bg-green-50 border border-green-200 rounded-md" style="display: none;">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <i class="fas fa-info-circle text-green-400"></i>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-green-800">Team Continuation</h3>
                            <div class="mt-2 text-sm text-green-700">
                                <p>By continuing your team:</p>
                                <ul class="list-disc list-inside mt-1 space-y-1">
                                    <li>Your team will maintain its lineage history</li>
                                    <li>Previous season performance will be tracked</li>
                                    <li>You can change the team name for the new season</li>
                                    <li>Your team balance will start fresh at 15,000</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>
                {% endif %}

                <!-- Season Information -->
                <div class="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <i class="fas fa-info-circle text-blue-400"></i>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-sm font-medium text-blue-800">Season Information</h3>
                            <div class="mt-2 text-sm text-blue-700">
                                {% if season[6] and season[7] %}
                                <p><strong>Season Duration:</strong> {{ season[6].strftime('%B %d, %Y') }} - {{ season[7].strftime('%B %d, %Y') }}</p>
                                {% endif %}
                                {% if season[5] %}
                                <p><strong>Registration Deadline:</strong> {{ season[5].strftime('%B %d, %Y at %I:%M %p') }}</p>
                                {% endif %}
                                <p><strong>Starting Balance:</strong> 15,000 credits</p>
                                {% if season[4] %}
                                <p><strong>Team Limit:</strong> {{ season[4] }} teams ({{ season[8] }} currently registered)</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Form Actions -->
            <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 flex justify-end space-x-3">
                <a href="{{ url_for('registration.registration_home') }}" 
                   class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    Cancel
                </a>
                <button type="submit" 
                        class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                    <i class="fas fa-check mr-2"></i>Register Team
                </button>
            </div>
        </form>
    </div>
</div>

<script>
// Show/hide continuation info based on registration type
document.addEventListener('DOMContentLoaded', function() {
    const newTeamRadio = document.getElementById('new_team');
    const continueTeamRadio = document.getElementById('continue_team');
    const continueInfo = document.getElementById('continue_info');
    const teamNameInput = document.getElementById('team_name');
    
    {% if can_continue %}
    const originalTeamName = "{{ user_current_team.name if user_current_team else '' }}";
    
    function toggleContinueInfo() {
        if (continueTeamRadio && continueTeamRadio.checked) {
            if (continueInfo) continueInfo.style.display = 'block';
            if (teamNameInput) teamNameInput.value = originalTeamName;
        } else {
            if (continueInfo) continueInfo.style.display = 'none';
            if (teamNameInput && teamNameInput.value === originalTeamName) {
                teamNameInput.value = '';
            }
        }
    }
    
    if (newTeamRadio) newTeamRadio.addEventListener('change', toggleContinueInfo);
    if (continueTeamRadio) continueTeamRadio.addEventListener('change', toggleContinueInfo);
    
    // Initial state
    toggleContinueInfo();
    {% endif %}
});
</script>
{% endblock %}'''
        
        season_form_path = os.path.join(registration_templates_dir, "season_form.html")
        with open(season_form_path, 'w') as f:
            f.write(season_form_template)
        
        print(f"   ✅ Created season registration form template")
        
        print("\n📋 Step 6: Creating registration success and user teams templates...")
        
        # Create registration success template
        success_template = '''{% extends "base.html" %}

{% block title %}Registration Successful{% endblock %}

{% block content %}
<div class="min-h-screen bg-gray-50">
    <div class="max-w-3xl mx-auto py-6 sm:px-6 lg:px-8">
        <!-- Success Header -->
        <div class="bg-white shadow sm:rounded-lg mb-6">
            <div class="px-6 py-8 text-center">
                <div class="mx-auto flex items-center justify-center h-12 w-12 rounded-full bg-green-100 mb-4">
                    <i class="fas fa-check text-green-600 text-xl"></i>
                </div>
                <h1 class="text-2xl font-bold text-gray-900 mb-2">Registration Successful!</h1>
                <p class="text-gray-600">Your team has been successfully registered for the season.</p>
            </div>
        </div>

        <!-- Team Details -->
        <div class="bg-white shadow sm:rounded-lg mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-medium text-gray-900">Team Details</h2>
            </div>
            <div class="px-6 py-4">
                <dl class="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2">
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Team Name</dt>
                        <dd class="mt-1 text-sm text-gray-900 font-semibold">{{ team[1] }}</dd>
                    </div>
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Season</dt>
                        <dd class="mt-1 text-sm text-gray-900">{{ team[4] }} ({{ team[5] }})</dd>
                    </div>
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Registration Type</dt>
                        <dd class="mt-1">
                            {% if team[2] %}
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                    <i class="fas fa-arrow-right mr-1"></i>Continuing Team
                                </span>
                            {% else %}
                                <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                    <i class="fas fa-star mr-1"></i>New Team
                                </span>
                            {% endif %}
                        </dd>
                    </div>
                    {% if team[3] %}
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Team Lineage</dt>
                        <dd class="mt-1 text-sm text-gray-900">Lineage #{{ team[3] }}</dd>
                    </div>
                    {% endif %}
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Starting Balance</dt>
                        <dd class="mt-1 text-sm text-gray-900">15,000 credits</dd>
                    </div>
                    {% if team[6] %}
                    <div>
                        <dt class="text-sm font-medium text-gray-500">Season Start</dt>
                        <dd class="mt-1 text-sm text-gray-900">{{ team[6].strftime('%B %d, %Y') }}</dd>
                    </div>
                    {% endif %}
                </dl>
            </div>
        </div>

        <!-- Team History (for continuing teams) -->
        {% if lineage_history and lineage_history|length > 1 %}
        <div class="bg-white shadow sm:rounded-lg mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-medium text-gray-900">Team Lineage History</h2>
                <p class="text-sm text-gray-600">Your team's journey across seasons</p>
            </div>
            <div class="px-6 py-4">
                <div class="flow-root">
                    <ul class="-mb-8">
                        {% for history in lineage_history %}
                        <li>
                            <div class="relative pb-8">
                                {% if not loop.last %}
                                <span class="absolute top-4 left-4 -ml-px h-full w-0.5 bg-gray-200" aria-hidden="true"></span>
                                {% endif %}
                                <div class="relative flex space-x-3">
                                    <div>
                                        <span class="h-8 w-8 rounded-full 
                                            {% if history[0] == team[0] %}bg-green-500{% else %}bg-gray-400{% endif %} 
                                            flex items-center justify-center ring-8 ring-white">
                                            {% if history[5] %}
                                                <i class="fas fa-arrow-right text-white text-xs"></i>
                                            {% else %}
                                                <i class="fas fa-star text-white text-xs"></i>
                                            {% endif %}
                                        </span>
                                    </div>
                                    <div class="min-w-0 flex-1 pt-1.5 flex justify-between space-x-4">
                                        <div>
                                            <p class="text-sm text-gray-900">
                                                <strong>{{ history[1] }}</strong> in {{ history[3] }}
                                                {% if history[0] == team[0] %}
                                                    <span class="text-green-600 font-medium">(Current)</span>
                                                {% endif %}
                                            </p>
                                        </div>
                                        <div class="text-right text-sm whitespace-nowrap text-gray-500">
                                            {{ history[6].strftime('%Y') if history[6] else 'Unknown' }}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Next Steps -->
        <div class="bg-white shadow sm:rounded-lg mb-6">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-medium text-gray-900">What's Next?</h2>
            </div>
            <div class="px-6 py-4">
                <div class="space-y-3">
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <i class="fas fa-clock text-indigo-500 mt-0.5"></i>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-gray-900">
                                <strong>Wait for Season Start:</strong> 
                                {% if team[6] %}
                                    Your season begins on {{ team[6].strftime('%B %d, %Y') }}
                                {% else %}
                                    Season start date will be announced
                                {% endif %}
                            </p>
                        </div>
                    </div>
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <i class="fas fa-users text-indigo-500 mt-0.5"></i>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-gray-900">
                                <strong>Team Management:</strong> You can view and manage your team details from your dashboard
                            </p>
                        </div>
                    </div>
                    <div class="flex items-start">
                        <div class="flex-shrink-0">
                            <i class="fas fa-gavel text-indigo-500 mt-0.5"></i>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm text-gray-900">
                                <strong>Player Auctions:</strong> Participate in player auctions when rounds begin
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="flex justify-center space-x-4">
            <a href="{{ url_for('dashboard') }}" 
               class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                <i class="fas fa-home mr-2"></i>Go to Dashboard
            </a>
            <a href="{{ url_for('registration.my_teams') }}" 
               class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                <i class="fas fa-users mr-2"></i>View My Teams
            </a>
            <a href="{{ url_for('registration.registration_home') }}" 
               class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                <i class="fas fa-plus mr-2"></i>Register Another Team
            </a>
        </div>
    </div>
</div>
{% endblock %}'''
        
        success_path = os.path.join(registration_templates_dir, "success.html")
        with open(success_path, 'w') as f:
            f.write(success_template)
        
        print(f"   ✅ Created registration success template")
        
        # Create my teams template (simplified for brevity)
        my_teams_template = '''{% extends "base.html" %}

{% block title %}My Teams{% endblock %}

{% block content %}
<div class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <!-- Page Header -->
        <div class="mb-8 flex justify-between items-center">
            <div>
                <h1 class="text-3xl font-bold text-gray-900">My Teams</h1>
                <p class="mt-2 text-gray-600">All your registered teams across seasons</p>
            </div>
            <a href="{{ url_for('registration.registration_home') }}" 
               class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                <i class="fas fa-plus mr-2"></i>Register New Team
            </a>
        </div>

        <!-- Teams List -->
        {% if user_teams %}
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <ul class="divide-y divide-gray-200">
                {% for team in user_teams %}
                <li class="px-6 py-4">
                    <div class="flex items-center justify-between">
                        <div class="flex-1">
                            <div class="flex items-center">
                                <h3 class="text-lg font-medium text-gray-900">{{ team[1] }}</h3>
                                {% if team[3] %}
                                    <span class="ml-3 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                                        <i class="fas fa-arrow-right mr-1"></i>Continuing
                                    </span>
                                {% else %}
                                    <span class="ml-3 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                        <i class="fas fa-star mr-1"></i>New
                                    </span>
                                {% endif %}
                                {% if team[7] %}
                                    <span class="ml-2 px-2 py-1 text-xs font-medium bg-green-100 text-green-800 rounded-full">
                                        Active Season
                                    </span>
                                {% endif %}
                            </div>
                            <div class="mt-2 text-sm text-gray-600">
                                <span><i class="fas fa-calendar mr-1"></i>{{ team[5] }} ({{ team[6] }})</span>
                                <span class="ml-4"><i class="fas fa-coins mr-1"></i>Balance: {{ team[2] }}</span>
                                {% if team[4] %}
                                    <span class="ml-4"><i class="fas fa-sitemap mr-1"></i>Lineage #{{ team[4] }}</span>
                                    {% if team[11] > 1 %}
                                        <span class="text-gray-500">({{ team[11] }} seasons)</span>
                                    {% endif %}
                                {% endif %}
                            </div>
                            {% if team[9] and team[10] %}
                            <div class="mt-1 text-xs text-gray-500">
                                Season: {{ team[9].strftime('%Y-%m-%d') }} - {{ team[10].strftime('%Y-%m-%d') }}
                            </div>
                            {% endif %}
                        </div>
                        
                        <div class="flex items-center space-x-2">
                            {% if team[4] %}
                            <a href="{{ url_for('registration.team_history', team_id=team[0]) }}" 
                               class="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                                <i class="fas fa-history mr-1"></i>History
                            </a>
                            {% endif %}
                        </div>
                    </div>
                </li>
                {% endfor %}
            </ul>
        </div>
        {% else %}
        <div class="bg-white shadow sm:rounded-lg">
            <div class="px-6 py-8 text-center">
                <i class="fas fa-users text-4xl text-gray-400 mb-4"></i>
                <h3 class="text-lg font-medium text-gray-900 mb-2">No Teams Registered</h3>
                <p class="text-gray-500">You haven't registered any teams yet.</p>
                <a href="{{ url_for('registration.registration_home') }}" 
                   class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                    Register Your First Team
                </a>
            </div>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}'''
        
        my_teams_path = os.path.join(registration_templates_dir, "my_teams.html")
        with open(my_teams_path, 'w') as f:
            f.write(my_teams_template)
        
        print(f"   ✅ Created my teams template")
        
        print("\n📋 Step 7: Registering registration blueprint in main app...")
        
        # Update main app.py to register registration blueprint
        app_path = os.path.join(APP_DIR, "app.py")
        backup_app = backup_file(app_path)
        print(f"   📋 Created backup: {backup_app}")
        
        # Read current app.py
        with open(app_path, 'r') as f:
            app_content = f.read()
        
        # Add registration blueprint import and registration
        registration_import = "from registration_routes import registration_bp"
        registration_register = "app.register_blueprint(registration_bp)"
        
        if registration_import not in app_content:
            # Find the admin import and add registration import after it
            admin_import_pos = app_content.find('from admin_routes import admin_bp')
            if admin_import_pos != -1:
                insertion_point = app_content.find('\n', admin_import_pos) + 1
                app_content = app_content[:insertion_point] + registration_import + '\n' + app_content[insertion_point:]
                print("   ✅ Added registration routes import to app.py")
        
        if registration_register not in app_content:
            # Find where admin blueprint is registered and add registration blueprint
            admin_register_pos = app_content.find("app.register_blueprint(admin_bp)")
            if admin_register_pos != -1:
                insertion_point = app_content.find('\n', admin_register_pos) + 1
                app_content = app_content[:insertion_point] + registration_register + '\n' + app_content[insertion_point:]
                print("   ✅ Added registration blueprint registration to app.py")
        
        # Write updated app.py
        with open(app_path, 'w') as f:
            f.write(app_content)
        
        print("\n📋 Step 8: Adding registration navigation to main templates...")
        
        # Check main templates and add registration navigation
        templates_dir = os.path.join(APP_DIR, "templates")
        main_templates = ['base.html', 'index.html']
        
        for template_name in main_templates:
            template_path = os.path.join(templates_dir, template_name)
            if os.path.exists(template_path):
                backup_template = backup_file(template_path)
                print(f"   📋 Found and backed up {template_name}: {backup_template}")
                
                # Read template
                with open(template_path, 'r') as f:
                    template_content = f.read()
                
                # Add registration navigation
                registration_nav_html = '''
                {% if current_user.is_authenticated %}
                    <a href="{{ url_for('registration.registration_home') }}" 
                       class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                        <i class="fas fa-user-plus mr-1"></i>Team Registration
                    </a>
                {% endif %}'''
                
                # Find navigation area and add registration link
                if 'Team Registration' not in template_content:
                    # Look for existing navigation patterns
                    nav_patterns = [
                        'Admin Panel',
                        'class="navbar',
                        '<nav'
                    ]
                    
                    for pattern in nav_patterns:
                        if pattern in template_content:
                            # Simple insertion - add before admin panel if it exists
                            if 'Admin Panel' in template_content:
                                template_content = template_content.replace(
                                    '{% if current_user.is_authenticated and current_user.role in [\'super_admin\', \'committee_admin\'] %}',
                                    registration_nav_html + '\n                {% if current_user.is_authenticated and current_user.role in [\'super_admin\', \'committee_admin\'] %}'
                                )
                                print(f"   ✅ Added registration navigation to {template_name}")
                                break
                
                # Write updated template
                with open(template_path, 'w') as f:
                    f.write(template_content)
                break
        
        print("\n📋 Step 9: Adding registration database functions...")
        
        # Add registration status functions
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_registration_status()
            RETURNS TABLE(
                season_id INTEGER,
                season_name VARCHAR(100),
                registration_open BOOLEAN,
                team_limit INTEGER,
                current_teams BIGINT,
                registration_deadline DATE
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    s.id,
                    s.name,
                    s.registration_open,
                    s.team_limit,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id),
                    s.registration_deadline
                FROM season s
                WHERE s.registration_open = true 
                  AND s.status IN ('upcoming', 'active')
                ORDER BY s.season_start_date ASC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created get_registration_status() database function")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION can_user_register(user_id_param INTEGER, season_id_param INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                -- Check if user already has a team in this season
                IF EXISTS(SELECT 1 FROM team WHERE user_id = user_id_param AND season_id = season_id_param) THEN
                    RETURN false;
                END IF;
                
                -- Check if season registration is open
                IF NOT EXISTS(SELECT 1 FROM season WHERE id = season_id_param AND registration_open = true) THEN
                    RETURN false;
                END IF;
                
                -- Check team limit
                DECLARE
                    team_count INTEGER;
                    team_limit INTEGER;
                BEGIN
                    SELECT COUNT(*), s.team_limit INTO team_count, team_limit
                    FROM team t
                    JOIN season s ON t.season_id = s.id
                    WHERE s.id = season_id_param
                    GROUP BY s.team_limit;
                    
                    IF team_limit IS NOT NULL AND team_count >= team_limit THEN
                        RETURN false;
                    END IF;
                END;
                
                RETURN true;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created can_user_register() database function")
        
        # Commit database changes
        conn.commit()
        
        print("\n📋 Step 10: Verification...")
        
        # Verify files were created
        files_to_check = [
            ("registration_routes.py", "Registration route handlers"),
            ("templates/registration/home.html", "Registration home template"),
            ("templates/registration/season_form.html", "Season registration form"),
            ("templates/registration/success.html", "Registration success page"),
            ("templates/registration/my_teams.html", "User teams overview")
        ]
        
        all_files_ok = True
        for filename, description in files_to_check:
            filepath = os.path.join(APP_DIR, filename)
            if os.path.exists(filepath):
                print(f"   ✅ {filename}: {description}")
            else:
                print(f"   ❌ {filename}: Not found!")
                all_files_ok = False
        
        # Verify app.py was updated
        with open(os.path.join(APP_DIR, "app.py"), 'r') as f:
            app_content = f.read()
        
        registration_integration = (
            "from registration_routes import registration_bp" in app_content and
            "app.register_blueprint(registration_bp)" in app_content
        )
        
        if registration_integration:
            print("   ✅ Registration routes integrated into main application")
        else:
            print("   ❌ Registration routes not properly integrated!")
            all_files_ok = False
        
        # Verify database functions
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN ('get_registration_status', 'can_user_register')
            ORDER BY routine_name
        """)
        
        db_functions = [row[0] for row in cursor.fetchall()]
        expected_functions = ['can_user_register', 'get_registration_status']
        
        print(f"   📊 Registration database functions: {len(db_functions)}/{len(expected_functions)}")
        for func in db_functions:
            print(f"      ✅ {func}()")
        
        if all_files_ok and len(db_functions) == len(expected_functions):
            print("\n🎉 TASK 8 COMPLETED SUCCESSFULLY!")
            print("✅ Created comprehensive team registration system")
            print("✅ Added continuing vs new team registration options")
            print("✅ Created registration templates with modern UI")
            print("✅ Integrated with team lineage system")
            print("✅ Added registration status management")
            print("✅ Created user team overview pages")
            print("✅ Integrated registration routes into main application")
            
            print("\n📝 REGISTRATION SYSTEM FEATURES:")
            print("   • Season-based registration with deadlines and limits")
            print("   • New team registration with unique names")
            print("   • Continuing team registration maintaining lineage")
            print("   • Registration status checking and validation")
            print("   • User team history and management")
            print("   • Professional UI with step-by-step forms")
            
            print("\n🔗 ACCESS REGISTRATION SYSTEM:")
            print("   • URL: /registration")
            print("   • Requires: User authentication")
            print("   • Admin: Enable registration in season settings")
            
            return True
        else:
            print(f"\n❌ TASK 8 FAILED:")
            print(f"   • Files created: {'✅' if all_files_ok else '❌'}")
            print(f"   • Database functions: {len(db_functions)}/{len(expected_functions)}")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 8: {e}")
        if conn:
            conn.rollback()
            print("🔄 Database changes rolled back")
        
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def rollback_task_08():
    """Rollback Task 8 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 8: Remove Team Registration System")
        print("⚠️  WARNING: This will remove the team registration system!")
        
        response = input("Are you sure you want to rollback Task 8? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        # Remove registration files
        files_to_remove = [
            "registration_routes.py",
        ]
        
        for filename in files_to_remove:
            filepath = os.path.join(APP_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"   ✅ Removed {filename}")
        
        # Remove registration templates directory
        registration_templates_dir = os.path.join(APP_DIR, "templates", "registration")
        if os.path.exists(registration_templates_dir):
            shutil.rmtree(registration_templates_dir)
            print(f"   ✅ Removed registration templates directory")
        
        # Remove database functions
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        functions_to_drop = ['get_registration_status', 'can_user_register']
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER) CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER, INTEGER) CASCADE")
        
        conn.commit()
        
        print("✅ Task 8 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 8 rollback: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_task_08()
    else:
        success = execute_task_08()
    
    sys.exit(0 if success else 1)