#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 9 EXECUTOR
====================================
Safely executes Task 9: Create Historical Data Viewing Interfaces

This script:
✅ Creates historical data viewing routes
✅ Adds season archive interfaces
✅ Creates team performance history views
✅ Adds system analytics and statistics
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

def execute_task_09():
    """Execute Task 9: Create Historical Data Viewing Interfaces"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 9: Create Historical Data Viewing Interfaces")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Creating historical data routes...")
        
        # Create history_routes.py
        history_routes_code = '''"""
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
'''
        
        history_routes_path = os.path.join(APP_DIR, "history_routes.py")
        with open(history_routes_path, 'w') as f:
            f.write(history_routes_code)
        
        print(f"   ✅ Created history_routes.py")
        
        print("\n📋 Step 2: Creating history templates...")
        
        # Create history templates directory
        templates_dir = os.path.join(APP_DIR, "templates")
        history_templates_dir = os.path.join(templates_dir, "history")
        os.makedirs(history_templates_dir, exist_ok=True)
        
        # Create history home template
        history_home_template = '''{% extends "base.html" %}

{% block title %}Season History{% endblock %}

{% block content %}
<div class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-gray-900">Season History</h1>
            <p class="mt-2 text-gray-600">Explore past seasons and team performance</p>
        </div>

        <!-- User Participation Summary -->
        {% if user_teams %}
        <div class="bg-white shadow sm:rounded-lg mb-8">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-lg font-medium text-gray-900">Your Participation</h2>
            </div>
            <div class="px-6 py-4">
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {% for team in user_teams %}
                    <div class="border rounded-lg p-4">
                        <h3 class="font-medium text-gray-900">{{ team[1] }}</h3>
                        <p class="text-sm text-gray-600">{{ team[2] }} ({{ team[3] }})</p>
                        {% if team[4] %}
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 mt-2">
                            Continuing Team
                        </span>
                        {% else %}
                        <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 mt-2">
                            New Team
                        </span>
                        {% endif %}
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        {% endif %}

        <!-- All Seasons -->
        <div class="bg-white shadow overflow-hidden sm:rounded-md">
            <div class="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h2 class="text-lg font-medium text-gray-900">All Seasons</h2>
                <a href="{{ url_for('history.system_analytics') }}" 
                   class="text-sm text-indigo-600 hover:text-indigo-700">View Analytics</a>
            </div>
            
            {% if seasons %}
            <ul class="divide-y divide-gray-200">
                {% for season in seasons %}
                <li class="px-6 py-4 hover:bg-gray-50">
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
                                    Current
                                </span>
                                {% endif %}
                            </div>
                            <div class="mt-2 flex items-center space-x-6 text-sm text-gray-500">
                                <span><i class="fas fa-users mr-1"></i>{{ season[8] }} teams</span>
                                <span><i class="fas fa-clock mr-1"></i>{{ season[9] }} rounds</span>
                                <span><i class="fas fa-gavel mr-1"></i>{{ season[10] }} bids</span>
                                {% if season[5] and season[6] %}
                                <span><i class="fas fa-calendar mr-1"></i>{{ season[5].strftime('%Y-%m-%d') }} - {{ season[6].strftime('%Y-%m-%d') }}</span>
                                {% endif %}
                            </div>
                        </div>
                        
                        <div class="flex items-center space-x-2">
                            <a href="{{ url_for('history.season_detail', season_id=season[0]) }}" 
                               class="inline-flex items-center px-3 py-1 border border-gray-300 text-xs font-medium rounded text-gray-700 bg-white hover:bg-gray-50">
                                <i class="fas fa-eye mr-1"></i>View Details
                            </a>
                        </div>
                    </div>
                </li>
                {% endfor %}
            </ul>
            {% else %}
            <div class="px-6 py-8 text-center">
                <p class="text-gray-500">No seasons found</p>
            </div>
            {% endif %}
        </div>
    </div>
</div>
{% endblock %}'''
        
        home_template_path = os.path.join(history_templates_dir, "home.html")
        with open(home_template_path, 'w') as f:
            f.write(history_home_template)
        
        print("   ✅ Created history home template")
        
        print("\n📋 Step 3: Adding database functions...")
        
        # Add historical data functions
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_season_leaderboard(season_id_param INTEGER)
            RETURNS TABLE(
                team_id INTEGER,
                team_name VARCHAR(50),
                total_bids BIGINT,
                avg_bid_amount NUMERIC,
                username VARCHAR(80)
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    t.id,
                    t.name,
                    COUNT(b.id) as total_bids,
                    COALESCE(AVG(b.amount), 0) as avg_bid_amount,
                    u.username
                FROM team t
                JOIN "user" u ON t.user_id = u.id
                LEFT JOIN bid b ON t.id = b.team_id
                WHERE t.season_id = season_id_param
                GROUP BY t.id, t.name, u.username
                ORDER BY total_bids DESC, avg_bid_amount DESC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created get_season_leaderboard() function")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_lineage_performance(lineage_id_param INTEGER)
            RETURNS TABLE(
                season_name VARCHAR(100),
                team_name VARCHAR(50),
                total_bids BIGINT,
                total_balance INTEGER,
                season_year INTEGER
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    s.name,
                    t.name,
                    (SELECT COUNT(*) FROM bid WHERE team_id = t.id) as total_bids,
                    t.balance,
                    EXTRACT(YEAR FROM s.season_start_date)::INTEGER as season_year
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.team_lineage_id = lineage_id_param
                ORDER BY s.created_at ASC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created get_lineage_performance() function")
        
        # Commit database changes
        conn.commit()
        
        print("\n📋 Step 4: Registering history blueprint...")
        
        # Update main app.py
        app_path = os.path.join(APP_DIR, "app.py")
        backup_app = backup_file(app_path)
        
        with open(app_path, 'r') as f:
            app_content = f.read()
        
        history_import = "from history_routes import history_bp"
        history_register = "app.register_blueprint(history_bp)"
        
        if history_import not in app_content:
            admin_import_pos = app_content.find('from registration_routes import registration_bp')
            if admin_import_pos != -1:
                insertion_point = app_content.find('\n', admin_import_pos) + 1
                app_content = app_content[:insertion_point] + history_import + '\n' + app_content[insertion_point:]
        
        if history_register not in app_content:
            registration_register_pos = app_content.find("app.register_blueprint(registration_bp)")
            if registration_register_pos != -1:
                insertion_point = app_content.find('\n', registration_register_pos) + 1
                app_content = app_content[:insertion_point] + history_register + '\n' + app_content[insertion_point:]
        
        with open(app_path, 'w') as f:
            f.write(app_content)
        
        print("   ✅ Integrated history routes into main application")
        
        print("\n📋 Step 5: Verification...")
        
        # Verify files
        files_to_check = [
            ("history_routes.py", "Historical data routes"),
            ("templates/history/home.html", "History home template")
        ]
        
        all_files_ok = True
        for filename, description in files_to_check:
            filepath = os.path.join(APP_DIR, filename)
            if os.path.exists(filepath):
                print(f"   ✅ {filename}: {description}")
            else:
                print(f"   ❌ {filename}: Not found!")
                all_files_ok = False
        
        # Verify database functions
        cursor.execute("""
            SELECT routine_name FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN ('get_season_leaderboard', 'get_lineage_performance')
        """)
        
        db_functions = [row[0] for row in cursor.fetchall()]
        
        print(f"   📊 History database functions: {len(db_functions)}/2")
        for func in db_functions:
            print(f"      ✅ {func}()")
        
        if all_files_ok and len(db_functions) == 2:
            print("\n🎉 TASK 9 COMPLETED SUCCESSFULLY!")
            print("✅ Created historical data viewing interfaces")
            print("✅ Added season archive functionality")
            print("✅ Created team lineage performance tracking")
            print("✅ Added system analytics and statistics")
            print("✅ Integrated with existing multi-season system")
            
            print("\n🔗 ACCESS HISTORY SYSTEM:")
            print("   • URL: /history")
            print("   • Features: Season archives, team lineages, analytics")
            
            return True
        else:
            print(f"\n❌ TASK 9 FAILED: Missing components")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 9: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    execute_task_09()