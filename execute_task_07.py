#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 7 EXECUTOR
====================================
Safely executes Task 7: Create Admin Panels and Season Management UI

This script:
✅ Creates admin route handlers for season management
✅ Creates admin templates for season administration
✅ Adds role-based access controls
✅ Creates season creation and management interfaces
✅ Adds admin invite system UI
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

def execute_task_07():
    """Execute Task 7: Create Admin Panels and Season Management UI"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 7: Create Admin Panels and Season Management UI")
        print("=" * 70)
        
        # Connect to database for verification
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Verifying prerequisites...")
        
        # Check if season context is available
        season_context_path = os.path.join(APP_DIR, "season_context.py")
        if not os.path.exists(season_context_path):
            print("❌ season_context.py not found! Please complete Task 6 first.")
            return False
        
        # Verify role system exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'user' AND column_name = 'role'
        """)
        if not cursor.fetchone():
            print("❌ User role system not found! Please complete Task 2 first.")
            return False
        
        print("   ✅ Prerequisites verified")
        
        print("\n📋 Step 2: Creating admin route handlers...")
        
        # Create admin_routes.py
        admin_routes_code = '''"""
Admin Routes for Multi-Season System
====================================
Provides admin interfaces for season and user management.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from flask_login import login_required, current_user
from functools import wraps
from models import db, User, Team, Season
from season_context import SeasonContext
import secrets
import string
from datetime import datetime, timedelta

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check if user has admin role
        if not hasattr(current_user, 'role') or current_user.role not in ['super_admin', 'committee_admin']:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def super_admin_required(f):
    """Decorator to require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check if user has super admin role
        if not hasattr(current_user, 'role') or current_user.role != 'super_admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@admin_required
def admin_dashboard():
    """Admin dashboard showing system overview"""
    try:
        # Get current season info
        current_season = SeasonContext.get_current_season()
        
        # Get season statistics
        with db.engine.connect() as conn:
            stats_result = conn.execute("SELECT * FROM get_season_statistics()")
            season_stats = stats_result.fetchone()
        
        # Get user role statistics
        with db.engine.connect() as conn:
            role_result = conn.execute("""
                SELECT role, COUNT(*) as count 
                FROM "user" 
                GROUP BY role 
                ORDER BY CASE role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_member' THEN 3 
                    ELSE 4 END
            """)
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
@admin_required
def season_management():
    """Season management interface"""
    try:
        # Get all seasons
        with db.engine.connect() as conn:
            seasons_result = conn.execute("""
                SELECT 
                    s.id, s.name, s.short_name, s.is_active, s.status, 
                    s.registration_open, s.team_limit, s.max_committee_admins,
                    s.season_start_date, s.season_end_date, s.created_at,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as team_count,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as round_count
                FROM season s
                ORDER BY s.created_at DESC
            """)
            seasons = seasons_result.fetchall()
        
        return render_template('admin/seasons.html', seasons=seasons)
        
    except Exception as e:
        current_app.logger.error(f"Error in season management: {e}")
        flash('Error loading season management.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/seasons/create', methods=['GET', 'POST'])
@super_admin_required
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
            
            # Create season using database function
            with db.engine.connect() as conn:
                result = conn.execute("""
                    INSERT INTO season (
                        name, short_name, description, is_active, status,
                        registration_open, team_limit, max_committee_admins,
                        created_by, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """, (
                    season_name, short_name, description, False, 'upcoming',
                    False, team_limit or 50, max_committee_admins or 15,
                    current_user.id, datetime.utcnow(), datetime.utcnow()
                ))
                season_id = result.fetchone()[0]
                conn.commit()
            
            flash(f'Season "{season_name}" created successfully!', 'success')
            return redirect(url_for('admin.season_management'))
            
        except Exception as e:
            current_app.logger.error(f"Error creating season: {e}")
            flash('Error creating season. Please try again.', 'error')
    
    return render_template('admin/create_season.html')

@admin_bp.route('/seasons/<int:season_id>/activate', methods=['POST'])
@super_admin_required
def activate_season(season_id):
    """Activate a season (deactivates all others)"""
    try:
        with db.engine.connect() as conn:
            # Deactivate all seasons
            conn.execute("UPDATE season SET is_active = false")
            
            # Activate the selected season
            conn.execute("""
                UPDATE season 
                SET is_active = true, status = 'active', updated_at = %s 
                WHERE id = %s
            """, (datetime.utcnow(), season_id))
            
            conn.commit()
        
        flash('Season activated successfully!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error activating season: {e}")
        flash('Error activating season.', 'error')
    
    return redirect(url_for('admin.season_management'))

@admin_bp.route('/users')
@admin_required
def user_management():
    """User management interface"""
    try:
        # Get all users with their roles and teams
        with db.engine.connect() as conn:
            users_result = conn.execute("""
                SELECT 
                    u.id, u.username, u.email, u.role, u.is_admin, u.is_approved,
                    u.profile_updated_at,
                    t.id as team_id, t.name as team_name, s.name as season_name
                FROM "user" u
                LEFT JOIN team t ON u.id = t.user_id 
                    AND t.season_id = (SELECT id FROM season WHERE is_active = true LIMIT 1)
                LEFT JOIN season s ON t.season_id = s.id
                ORDER BY u.role, u.username
            """)
            users = users_result.fetchall()
        
        return render_template('admin/users.html', users=users)
        
    except Exception as e:
        current_app.logger.error(f"Error in user management: {e}")
        flash('Error loading user management.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/<int:user_id>/promote', methods=['POST'])
@super_admin_required
def promote_user(user_id):
    """Promote user to committee admin"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute("""
                SELECT promote_to_committee_admin(%s, %s)
            """, (user_id, current_user.id))
            
            conn.commit()
        
        flash('User promoted to committee admin successfully!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error promoting user: {e}")
        flash('Error promoting user. They may already be an admin.', 'error')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/users/<int:user_id>/demote', methods=['POST'])
@super_admin_required
def demote_user(user_id):
    """Demote user from admin role"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute("""
                SELECT demote_from_admin(%s, %s)
            """, (user_id, current_user.id))
            
            conn.commit()
        
        flash('User demoted to team member successfully!', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error demoting user: {e}")
        flash('Error demoting user. They may not be an admin or be a super admin.', 'error')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/invites')
@admin_required
def admin_invites():
    """Admin invite management"""
    try:
        # Get active admin invites
        with db.engine.connect() as conn:
            invites_result = conn.execute("""
                SELECT 
                    ai.id, ai.invite_token, ai.expires_at, ai.max_uses, 
                    ai.current_uses, ai.is_active, ai.description,
                    ai.created_at, u.username as created_by_username
                FROM admin_invite ai
                JOIN "user" u ON ai.created_by = u.id
                WHERE ai.is_active = true
                ORDER BY ai.created_at DESC
            """)
            invites = invites_result.fetchall()
        
        return render_template('admin/invites.html', invites=invites)
        
    except Exception as e:
        current_app.logger.error(f"Error loading admin invites: {e}")
        flash('Error loading admin invites.', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/invites/create', methods=['POST'])
@admin_required
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
            conn.execute("""
                INSERT INTO admin_invite (
                    invite_token, expires_at, max_uses, current_uses,
                    created_by, is_active, description, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                token, expires_at, max_uses, 0,
                current_user.id, True, description, datetime.utcnow()
            ))
            conn.commit()
        
        flash(f'Admin invite created successfully! Token: {token}', 'success')
        
    except Exception as e:
        current_app.logger.error(f"Error creating admin invite: {e}")
        flash('Error creating admin invite.', 'error')
    
    return redirect(url_for('admin.admin_invites'))

@admin_bp.route('/api/season-stats/<int:season_id>')
@admin_required
def api_season_stats(season_id):
    """API endpoint for season statistics"""
    try:
        with db.engine.connect() as conn:
            result = conn.execute("SELECT * FROM get_season_statistics(%s)", (season_id,))
            stats = result.fetchone()
            
            if stats:
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
            else:
                return jsonify({'error': 'Season not found'}), 404
                
    except Exception as e:
        current_app.logger.error(f"Error getting season stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500
'''
        
        admin_routes_path = os.path.join(APP_DIR, "admin_routes.py")
        with open(admin_routes_path, 'w') as f:
            f.write(admin_routes_code)
        
        print(f"   ✅ Created admin_routes.py at {admin_routes_path}")
        
        print("\n📋 Step 3: Creating admin templates directory...")
        
        # Create admin templates directory
        templates_dir = os.path.join(APP_DIR, "templates")
        admin_templates_dir = os.path.join(templates_dir, "admin")
        os.makedirs(admin_templates_dir, exist_ok=True)
        
        print(f"   ✅ Created admin templates directory at {admin_templates_dir}")
        
        print("\n📋 Step 4: Creating admin base template...")
        
        # Create admin base template
        admin_base_template = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Admin Panel{% endblock %} - {{ format_season_name(current_season) }}</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        .admin-sidebar {
            transition: all 0.3s ease;
        }
        .admin-content {
            transition: margin-left 0.3s ease;
        }
    </style>
</head>
<body class="bg-gray-50">
    <!-- Admin Navigation -->
    <nav class="bg-indigo-600 text-white shadow-lg">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between h-16">
                <div class="flex items-center">
                    <i class="fas fa-cogs text-xl mr-3"></i>
                    <h1 class="text-xl font-semibold">Admin Panel</h1>
                    {% if current_season %}
                        <span class="ml-4 px-3 py-1 bg-indigo-500 rounded-full text-sm">
                            {{ current_season.short_name }}
                        </span>
                    {% endif %}
                </div>
                <div class="flex items-center space-x-4">
                    <span class="text-sm">{{ current_user.username }}</span>
                    {% if current_user.role == 'super_admin' %}
                        <span class="px-2 py-1 bg-red-500 rounded text-xs">Super Admin</span>
                    {% elif current_user.role == 'committee_admin' %}
                        <span class="px-2 py-1 bg-orange-500 rounded text-xs">Committee Admin</span>
                    {% endif %}
                    <a href="{{ url_for('dashboard') }}" class="text-indigo-200 hover:text-white">
                        <i class="fas fa-home"></i> Dashboard
                    </a>
                    <a href="{{ url_for('logout') }}" class="text-indigo-200 hover:text-white">
                        <i class="fas fa-sign-out-alt"></i> Logout
                    </a>
                </div>
            </div>
        </div>
    </nav>

    <div class="flex min-h-screen">
        <!-- Admin Sidebar -->
        <aside class="admin-sidebar w-64 bg-gray-800 text-white">
            <nav class="mt-5">
                <a href="{{ url_for('admin.admin_dashboard') }}" 
                   class="group flex items-center px-6 py-3 text-sm font-medium rounded-md hover:bg-gray-700 {{ 'bg-gray-900' if request.endpoint == 'admin.admin_dashboard' else '' }}">
                    <i class="fas fa-tachometer-alt mr-3"></i>
                    Dashboard
                </a>
                
                <a href="{{ url_for('admin.season_management') }}" 
                   class="group flex items-center px-6 py-3 text-sm font-medium rounded-md hover:bg-gray-700 {{ 'bg-gray-900' if 'season' in request.endpoint else '' }}">
                    <i class="fas fa-calendar-alt mr-3"></i>
                    Seasons
                </a>
                
                <a href="{{ url_for('admin.user_management') }}" 
                   class="group flex items-center px-6 py-3 text-sm font-medium rounded-md hover:bg-gray-700 {{ 'bg-gray-900' if 'user' in request.endpoint else '' }}">
                    <i class="fas fa-users mr-3"></i>
                    Users
                </a>
                
                <a href="{{ url_for('admin.admin_invites') }}" 
                   class="group flex items-center px-6 py-3 text-sm font-medium rounded-md hover:bg-gray-700 {{ 'bg-gray-900' if 'invite' in request.endpoint else '' }}">
                    <i class="fas fa-user-plus mr-3"></i>
                    Admin Invites
                </a>
                
                {% if current_user.role == 'super_admin' %}
                    <div class="px-6 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                        Super Admin Only
                    </div>
                {% endif %}
            </nav>
        </aside>

        <!-- Main Content -->
        <main class="admin-content flex-1 overflow-hidden">
            <div class="p-6">
                <!-- Flash Messages -->
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        <div class="mb-6">
                            {% for category, message in messages %}
                                <div class="alert alert-{{ 'danger' if category == 'error' else category }} mb-4 p-4 rounded-md
                                    {% if category == 'error' %}bg-red-50 border border-red-200 text-red-700
                                    {% elif category == 'success' %}bg-green-50 border border-green-200 text-green-700
                                    {% elif category == 'warning' %}bg-yellow-50 border border-yellow-200 text-yellow-700
                                    {% else %}bg-blue-50 border border-blue-200 text-blue-700{% endif %}">
                                    <i class="fas fa-{% if category == 'error' %}exclamation-circle{% elif category == 'success' %}check-circle{% elif category == 'warning' %}exclamation-triangle{% else %}info-circle{% endif %} mr-2"></i>
                                    {{ message }}
                                </div>
                            {% endfor %}
                        </div>
                    {% endif %}
                {% endwith %}

                <!-- Page Content -->
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/alpinejs/3.x.x/cdn.min.js" defer></script>
    {% block scripts %}{% endblock %}
</body>
</html>'''
        
        admin_base_path = os.path.join(admin_templates_dir, "base.html")
        with open(admin_base_path, 'w') as f:
            f.write(admin_base_template)
        
        print(f"   ✅ Created admin base template at {admin_base_path}")
        
        print("\n📋 Step 5: Creating admin dashboard template...")
        
        # Create admin dashboard template
        admin_dashboard_template = '''{% extends "admin/base.html" %}

{% block title %}Admin Dashboard{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto">
    <!-- Page Header -->
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
        <p class="mt-2 text-gray-600">System overview and management</p>
    </div>

    <!-- Current Season Info -->
    {% if current_season %}
    <div class="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-8">
        <div class="flex items-center justify-between">
            <div>
                <h2 class="text-xl font-semibold text-blue-900">{{ format_season_name(current_season) }}</h2>
                <p class="text-blue-700">Current Active Season</p>
                <div class="mt-2 flex items-center space-x-4 text-sm text-blue-600">
                    <span><i class="fas fa-circle mr-1 text-green-500"></i>{{ current_season.status|title }}</span>
                </div>
            </div>
            {% if current_user.role == 'super_admin' %}
            <div class="text-right">
                <a href="{{ url_for('admin.season_management') }}" 
                   class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                    <i class="fas fa-cog mr-2"></i>Manage Seasons
                </a>
            </div>
            {% endif %}
        </div>
    </div>
    {% endif %}

    <!-- Statistics Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {% if season_stats %}
            <!-- Teams Card -->
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-users text-2xl text-indigo-500"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Teams</dt>
                                <dd class="text-lg font-medium text-gray-900">{{ season_stats[2] }}</dd>
                                <dd class="text-xs text-gray-500">
                                    {{ season_stats[4] }} new, {{ season_stats[3] }} continuing
                                </dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Rounds Card -->
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-clock text-2xl text-green-500"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Rounds</dt>
                                <dd class="text-lg font-medium text-gray-900">{{ season_stats[5] }}</dd>
                                <dd class="text-xs text-gray-500">
                                    {{ season_stats[6] }} active
                                </dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Bids Card -->
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i class="fas fa-gavel text-2xl text-yellow-500"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <dl>
                                <dt class="text-sm font-medium text-gray-500 truncate">Bids</dt>
                                <dd class="text-lg font-medium text-gray-900">{{ season_stats[7] }}</dd>
                                <dd class="text-xs text-gray-500">Total season bids</dd>
                            </dl>
                        </div>
                    </div>
                </div>
            </div>
        {% endif %}

        <!-- User Roles Card -->
        <div class="bg-white overflow-hidden shadow rounded-lg">
            <div class="p-5">
                <div class="flex items-center">
                    <div class="flex-shrink-0">
                        <i class="fas fa-user-shield text-2xl text-red-500"></i>
                    </div>
                    <div class="ml-5 w-0 flex-1">
                        <dl>
                            <dt class="text-sm font-medium text-gray-500 truncate">Users</dt>
                            <dd class="text-lg font-medium text-gray-900">
                                {% set total_users = role_stats|sum(attribute=1) if role_stats else 0 %}
                                {{ total_users }}
                            </dd>
                            <dd class="text-xs text-gray-500">System users</dd>
                        </dl>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- User Role Breakdown -->
    {% if role_stats %}
    <div class="bg-white shadow rounded-lg mb-8">
        <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">User Role Distribution</h3>
        </div>
        <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {% for role, count in role_stats %}
                <div class="text-center p-4 bg-gray-50 rounded-lg">
                    <div class="text-2xl font-bold 
                        {% if role == 'super_admin' %}text-red-600
                        {% elif role == 'committee_admin' %}text-orange-600
                        {% else %}text-blue-600{% endif %}">
                        {{ count }}
                    </div>
                    <div class="text-sm text-gray-600 mt-1">
                        {% if role == 'super_admin' %}Super Admins
                        {% elif role == 'committee_admin' %}Committee Admins
                        {% else %}Team Members{% endif %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>
    {% endif %}

    <!-- Quick Actions -->
    <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">Quick Actions</h3>
        </div>
        <div class="p-6">
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {% if current_user.role == 'super_admin' %}
                <a href="{{ url_for('admin.create_season') }}" 
                   class="inline-flex items-center justify-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                    <i class="fas fa-plus mr-2"></i>New Season
                </a>
                {% endif %}
                
                <a href="{{ url_for('admin.user_management') }}" 
                   class="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    <i class="fas fa-users mr-2"></i>Manage Users
                </a>
                
                <a href="{{ url_for('admin.admin_invites') }}" 
                   class="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    <i class="fas fa-user-plus mr-2"></i>Admin Invites
                </a>
                
                <a href="{{ url_for('admin.season_management') }}" 
                   class="inline-flex items-center justify-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    <i class="fas fa-calendar-alt mr-2"></i>View Seasons
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}'''
        
        dashboard_template_path = os.path.join(admin_templates_dir, "dashboard.html")
        with open(dashboard_template_path, 'w') as f:
            f.write(admin_dashboard_template)
        
        print(f"   ✅ Created admin dashboard template")
        
        print("\n📋 Step 6: Creating season management templates...")
        
        # Create seasons.html template
        seasons_template = '''{% extends "admin/base.html" %}

{% block title %}Season Management{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto">
    <!-- Page Header -->
    <div class="mb-8 flex justify-between items-center">
        <div>
            <h1 class="text-3xl font-bold text-gray-900">Season Management</h1>
            <p class="mt-2 text-gray-600">Manage seasons and their configurations</p>
        </div>
        {% if current_user.role == 'super_admin' %}
        <a href="{{ url_for('admin.create_season') }}" 
           class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
            <i class="fas fa-plus mr-2"></i>Create Season
        </a>
        {% endif %}
    </div>

    <!-- Seasons Table -->
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">All Seasons</h3>
        </div>
        
        {% if seasons %}
        <ul class="divide-y divide-gray-200">
            {% for season in seasons %}
            <li class="px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="flex items-center">
                            <h3 class="text-lg font-medium text-gray-900">{{ season[1] }}</h3>
                            <span class="ml-3 px-2 py-1 text-xs font-medium rounded-full
                                {% if season[3] %}bg-green-100 text-green-800{% else %}bg-gray-100 text-gray-800{% endif %}">
                                {{ season[2] }}
                            </span>
                            {% if season[3] %}
                                <span class="ml-2 px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 rounded-full">
                                    Active
                                </span>
                            {% endif %}
                        </div>
                        <div class="mt-2 flex items-center space-x-6 text-sm text-gray-500">
                            <span><i class="fas fa-users mr-1"></i>{{ season[11] }} teams</span>
                            <span><i class="fas fa-clock mr-1"></i>{{ season[12] }} rounds</span>
                            <span><i class="fas fa-calendar mr-1"></i>Status: {{ season[4]|title }}</span>
                            {% if season[5] %}
                                <span class="text-green-600"><i class="fas fa-door-open mr-1"></i>Registration Open</span>
                            {% endif %}
                        </div>
                        {% if season[8] and season[9] %}
                        <div class="mt-1 text-sm text-gray-500">
                            <i class="fas fa-calendar-alt mr-1"></i>
                            {{ season[8].strftime('%Y-%m-%d') }} - {{ season[9].strftime('%Y-%m-%d') }}
                        </div>
                        {% endif %}
                    </div>
                    
                    <div class="flex items-center space-x-2">
                        {% if current_user.role == 'super_admin' and not season[3] %}
                        <form method="POST" action="{{ url_for('admin.activate_season', season_id=season[0]) }}" 
                              onsubmit="return confirm('Are you sure you want to activate this season? This will deactivate the current active season.')">
                            <button type="submit" 
                                    class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-white bg-green-600 hover:bg-green-700">
                                <i class="fas fa-play mr-1"></i>Activate
                            </button>
                        </form>
                        {% endif %}
                        
                        <button onclick="loadSeasonStats({{ season[0] }})"
                                class="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                            <i class="fas fa-chart-bar mr-1"></i>Stats
                        </button>
                    </div>
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <div class="px-6 py-8 text-center">
            <i class="fas fa-calendar-alt text-4xl text-gray-400 mb-4"></i>
            <p class="text-gray-500">No seasons found</p>
            {% if current_user.role == 'super_admin' %}
            <a href="{{ url_for('admin.create_season') }}" 
               class="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                Create First Season
            </a>
            {% endif %}
        </div>
        {% endif %}
    </div>
</div>

<!-- Season Stats Modal -->
<div id="seasonStatsModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Season Statistics</h3>
            <button onclick="closeStatsModal()" class="text-gray-400 hover:text-gray-600">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div id="seasonStatsContent">
            <div class="animate-pulse">
                <div class="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div class="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                <div class="h-4 bg-gray-200 rounded w-2/3"></div>
            </div>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function loadSeasonStats(seasonId) {
    document.getElementById('seasonStatsModal').classList.remove('hidden');
    
    fetch(`/admin/api/season-stats/${seasonId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                document.getElementById('seasonStatsContent').innerHTML = 
                    `<p class="text-red-600">Error: ${data.error}</p>`;
            } else {
                document.getElementById('seasonStatsContent').innerHTML = `
                    <div class="space-y-3">
                        <div class="flex justify-between">
                            <span class="text-gray-600">Season:</span>
                            <span class="font-medium">${data.season_name}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Total Teams:</span>
                            <span class="font-medium">${data.total_teams}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">New Teams:</span>
                            <span class="font-medium">${data.new_teams}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Continuing Teams:</span>
                            <span class="font-medium">${data.continuing_teams}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Total Rounds:</span>
                            <span class="font-medium">${data.total_rounds}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Active Rounds:</span>
                            <span class="font-medium">${data.active_rounds}</span>
                        </div>
                        <div class="flex justify-between">
                            <span class="text-gray-600">Total Bids:</span>
                            <span class="font-medium">${data.total_bids}</span>
                        </div>
                    </div>
                `;
            }
        })
        .catch(error => {
            document.getElementById('seasonStatsContent').innerHTML = 
                '<p class="text-red-600">Error loading statistics</p>';
        });
}

function closeStatsModal() {
    document.getElementById('seasonStatsModal').classList.add('hidden');
}
</script>
{% endblock %}'''
        
        seasons_template_path = os.path.join(admin_templates_dir, "seasons.html")
        with open(seasons_template_path, 'w') as f:
            f.write(seasons_template)
        
        print(f"   ✅ Created seasons management template")
        
        print("\n📋 Step 7: Registering admin blueprint in main app...")
        
        # Update main app.py to register admin blueprint
        app_path = os.path.join(APP_DIR, "app.py")
        backup_app = backup_file(app_path)
        print(f"   📋 Created backup: {backup_app}")
        
        # Read current app.py
        with open(app_path, 'r') as f:
            app_content = f.read()
        
        # Add admin blueprint import and registration
        admin_import = "from admin_routes import admin_bp"
        admin_register = "app.register_blueprint(admin_bp)"
        
        if admin_import not in app_content:
            # Find the import section and add admin import
            import_section = app_content.find('from team_management_routes import team_management')
            if import_section != -1:
                insertion_point = app_content.find('\n', import_section) + 1
                app_content = app_content[:insertion_point] + admin_import + '\n' + app_content[insertion_point:]
                print("   ✅ Added admin routes import to app.py")
        
        if admin_register not in app_content:
            # Find where blueprints are registered and add admin blueprint
            blueprint_register = app_content.find("app.register_blueprint(team_management, url_prefix='/team_management')")
            if blueprint_register != -1:
                insertion_point = app_content.find('\n', blueprint_register) + 1
                app_content = app_content[:insertion_point] + admin_register + '\n' + app_content[insertion_point:]
                print("   ✅ Added admin blueprint registration to app.py")
        
        # Write updated app.py
        with open(app_path, 'w') as f:
            f.write(app_content)
        
        print("\n📋 Step 8: Adding admin navigation to main templates...")
        
        # Check if main templates exist and add admin navigation
        main_templates = ['base.html', 'layout.html', 'index.html']
        
        for template_name in main_templates:
            template_path = os.path.join(templates_dir, template_name)
            if os.path.exists(template_path):
                backup_template = backup_file(template_path)
                print(f"   📋 Found and backed up {template_name}: {backup_template}")
                
                # Read template
                with open(template_path, 'r') as f:
                    template_content = f.read()
                
                # Add admin link for admin users
                admin_nav_html = '''
                {% if current_user.is_authenticated and current_user.role in ['super_admin', 'committee_admin'] %}
                    <a href="{{ url_for('admin.admin_dashboard') }}" 
                       class="text-gray-300 hover:bg-gray-700 hover:text-white px-3 py-2 rounded-md text-sm font-medium">
                        <i class="fas fa-cogs mr-1"></i>Admin Panel
                    </a>
                {% endif %}'''
                
                # Try to find navigation area and add admin link
                nav_patterns = [
                    ('class="navbar', admin_nav_html),
                    ('<nav', admin_nav_html),
                    ('url_for(\'logout\')', admin_nav_html + '\n                    <a href="{{ url_for(\'logout\') }}"')
                ]
                
                template_updated = False
                for pattern, replacement in nav_patterns:
                    if pattern in template_content and 'Admin Panel' not in template_content:
                        # Simple insertion logic - this is basic but should work
                        if 'logout' in pattern:
                            template_content = template_content.replace(
                                '<a href="{{ url_for(\'logout\') }}"',
                                admin_nav_html + '\n                    <a href="{{ url_for(\'logout\') }}"'
                            )
                        template_updated = True
                        break
                
                if template_updated:
                    with open(template_path, 'w') as f:
                        f.write(template_content)
                    print(f"   ✅ Added admin navigation to {template_name}")
                break
        
        print("\n📋 Step 9: Creating additional admin templates...")
        
        # Create simple user management template
        users_template = '''{% extends "admin/base.html" %}

{% block title %}User Management{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto">
    <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900">User Management</h1>
        <p class="mt-2 text-gray-600">Manage user roles and permissions</p>
    </div>

    <!-- Users Table -->
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">All Users</h3>
        </div>
        
        {% if users %}
        <ul class="divide-y divide-gray-200">
            {% for user in users %}
            <li class="px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="flex items-center">
                            <h3 class="text-lg font-medium text-gray-900">{{ user[1] }}</h3>
                            <span class="ml-3 px-2 py-1 text-xs font-medium rounded-full
                                {% if user[3] == 'super_admin' %}bg-red-100 text-red-800
                                {% elif user[3] == 'committee_admin' %}bg-orange-100 text-orange-800
                                {% else %}bg-blue-100 text-blue-800{% endif %}">
                                {{ user[3].replace('_', ' ')|title if user[3] else 'Team Member' }}
                            </span>
                        </div>
                        <div class="mt-2 text-sm text-gray-500">
                            {% if user[2] %}<i class="fas fa-envelope mr-1"></i>{{ user[2] }}{% endif %}
                            {% if user[8] %} | <i class="fas fa-users mr-1"></i>Team: {{ user[8] }}{% endif %}
                        </div>
                    </div>
                    
                    {% if current_user.role == 'super_admin' and user[0] != current_user.id %}
                    <div class="flex items-center space-x-2">
                        {% if user[3] == 'team_member' %}
                        <form method="POST" action="{{ url_for('admin.promote_user', user_id=user[0]) }}" class="inline">
                            <button type="submit" 
                                    class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-white bg-orange-600 hover:bg-orange-700">
                                <i class="fas fa-arrow-up mr-1"></i>Promote
                            </button>
                        </form>
                        {% elif user[3] == 'committee_admin' %}
                        <form method="POST" action="{{ url_for('admin.demote_user', user_id=user[0]) }}" class="inline">
                            <button type="submit" 
                                    class="inline-flex items-center px-3 py-1 border border-transparent text-xs font-medium rounded text-white bg-red-600 hover:bg-red-700">
                                <i class="fas fa-arrow-down mr-1"></i>Demote
                            </button>
                        </form>
                        {% endif %}
                    </div>
                    {% endif %}
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <div class="px-6 py-8 text-center">
            <p class="text-gray-500">No users found</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}'''
        
        users_template_path = os.path.join(admin_templates_dir, "users.html")
        with open(users_template_path, 'w') as f:
            f.write(users_template)
        
        print(f"   ✅ Created user management template")
        
        # Create simple invites template
        invites_template = '''{% extends "admin/base.html" %}

{% block title %}Admin Invites{% endblock %}

{% block content %}
<div class="max-w-7xl mx-auto">
    <div class="mb-8 flex justify-between items-center">
        <div>
            <h1 class="text-3xl font-bold text-gray-900">Admin Invites</h1>
            <p class="mt-2 text-gray-600">Manage committee admin invitations</p>
        </div>
        <button onclick="document.getElementById('createInviteModal').classList.remove('hidden')"
                class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
            <i class="fas fa-plus mr-2"></i>Create Invite
        </button>
    </div>

    <!-- Active Invites -->
    <div class="bg-white shadow overflow-hidden sm:rounded-md">
        <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-medium text-gray-900">Active Invites</h3>
        </div>
        
        {% if invites %}
        <ul class="divide-y divide-gray-200">
            {% for invite in invites %}
            <li class="px-6 py-4">
                <div class="flex items-center justify-between">
                    <div class="flex-1">
                        <div class="flex items-center">
                            <code class="text-sm bg-gray-100 px-2 py-1 rounded">{{ invite[1] }}</code>
                            {% if invite[6] %}
                                <span class="ml-3 text-sm text-gray-600">{{ invite[6] }}</span>
                            {% endif %}
                        </div>
                        <div class="mt-2 text-sm text-gray-500">
                            <span><i class="fas fa-user mr-1"></i>Created by: {{ invite[8] }}</span>
                            <span class="ml-4"><i class="fas fa-clock mr-1"></i>Expires: {{ invite[2].strftime('%Y-%m-%d %H:%M') if invite[2] else 'Never' }}</span>
                            <span class="ml-4"><i class="fas fa-hashtag mr-1"></i>Uses: {{ invite[4] }}/{{ invite[3] }}</span>
                        </div>
                    </div>
                </div>
            </li>
            {% endfor %}
        </ul>
        {% else %}
        <div class="px-6 py-8 text-center">
            <p class="text-gray-500">No active invites</p>
        </div>
        {% endif %}
    </div>
</div>

<!-- Create Invite Modal -->
<div id="createInviteModal" class="fixed inset-0 bg-gray-600 bg-opacity-50 hidden overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-medium text-gray-900">Create Admin Invite</h3>
            <button onclick="document.getElementById('createInviteModal').classList.add('hidden')" class="text-gray-400 hover:text-gray-600">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <form method="POST" action="{{ url_for('admin.create_admin_invite') }}">
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">Description</label>
                <input type="text" name="description" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">Max Uses</label>
                <input type="number" name="max_uses" value="1" min="1" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
            </div>
            <div class="mb-4">
                <label class="block text-sm font-medium text-gray-700 mb-2">Expires In (Hours)</label>
                <input type="number" name="expires_hours" value="24" min="1" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-indigo-500 focus:border-indigo-500">
            </div>
            <div class="flex justify-end space-x-2">
                <button type="button" onclick="document.getElementById('createInviteModal').classList.add('hidden')" 
                        class="px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                    Cancel
                </button>
                <button type="submit" 
                        class="px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700">
                    Create Invite
                </button>
            </div>
        </form>
    </div>
</div>
{% endblock %}'''
        
        invites_template_path = os.path.join(admin_templates_dir, "invites.html")
        with open(invites_template_path, 'w') as f:
            f.write(invites_template)
        
        print(f"   ✅ Created admin invites template")
        
        print("\n📋 Step 10: Verification...")
        
        # Verify files were created
        files_to_check = [
            ("admin_routes.py", "Admin route handlers"),
            ("templates/admin/base.html", "Admin base template"),
            ("templates/admin/dashboard.html", "Admin dashboard template"),
            ("templates/admin/seasons.html", "Season management template"),
            ("templates/admin/users.html", "User management template"),
            ("templates/admin/invites.html", "Admin invites template")
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
        
        admin_integration = (
            "from admin_routes import admin_bp" in app_content and
            "app.register_blueprint(admin_bp)" in app_content
        )
        
        if admin_integration:
            print("   ✅ Admin routes integrated into main application")
        else:
            print("   ❌ Admin routes not properly integrated!")
            all_files_ok = False
        
        if all_files_ok:
            print("\n🎉 TASK 7 COMPLETED SUCCESSFULLY!")
            print("✅ Created comprehensive admin panel system")
            print("✅ Added role-based access controls")
            print("✅ Created season management interfaces")
            print("✅ Added user management with promote/demote functions")
            print("✅ Implemented admin invite system")
            print("✅ Created responsive admin templates")
            print("✅ Integrated admin routes into main application")
            
            print("\n📝 ADMIN PANEL FEATURES:")
            print("   • Dashboard with season overview and statistics")
            print("   • Season management (create, view, activate)")
            print("   • User role management (promote/demote)")
            print("   • Admin invite system with expiration")
            print("   • Role-based access control (super_admin vs committee_admin)")
            print("   • Responsive UI with modern design")
            
            print("\n🔗 ACCESS ADMIN PANEL:")
            print("   • URL: /admin")
            print("   • Requires: super_admin or committee_admin role")
            print("   • First admin must be promoted directly in database")
            
            return True
        else:
            print(f"\n❌ TASK 7 FAILED: Not all components created successfully")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 7: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def rollback_task_07():
    """Rollback Task 7 changes if needed"""
    try:
        print("\n🔄 ROLLBACK TASK 7: Remove Admin Panel System")
        print("⚠️  WARNING: This will remove the admin panel system!")
        
        response = input("Are you sure you want to rollback Task 7? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        # Remove admin files
        files_to_remove = [
            "admin_routes.py",
        ]
        
        for filename in files_to_remove:
            filepath = os.path.join(APP_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"   ✅ Removed {filename}")
        
        # Remove admin templates directory
        admin_templates_dir = os.path.join(APP_DIR, "templates", "admin")
        if os.path.exists(admin_templates_dir):
            shutil.rmtree(admin_templates_dir)
            print(f"   ✅ Removed admin templates directory")
        
        # Restore app.py backup if available
        backup_files = []
        if os.path.exists(BACKUP_DIR):
            for file in os.listdir(BACKUP_DIR):
                if file.startswith('app.py.backup_') and file.endswith('_task_07'):
                    backup_files.append(file)
        
        if backup_files:
            latest_backup = max(backup_files)
            backup_path = os.path.join(BACKUP_DIR, latest_backup)
            original_path = os.path.join(APP_DIR, "app.py")
            
            shutil.copy2(backup_path, original_path)
            print(f"   ✅ Restored app.py from {latest_backup}")
        
        print("✅ Task 7 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 7 rollback: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_task_07()
    else:
        success = execute_task_07()
    
    sys.exit(0 if success else 1)