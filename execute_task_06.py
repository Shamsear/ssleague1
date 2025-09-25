#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 6 EXECUTOR
====================================
Safely executes Task 6: Update Application Code for Season-Awareness

This script:
✅ Updates models to be season-aware
✅ Adds helper functions for season-based queries
✅ Updates the main app to use current season context
✅ Creates season context helpers
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

def execute_task_06():
    """Execute Task 6: Update Application Code for Season-Awareness"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 6: Update Application Code for Season-Awareness")
        print("=" * 70)
        
        # Connect to database for verification
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Verifying multi-season database structure...")
        
        # Verify that previous tasks are complete
        cursor.execute("SELECT id, name, is_active FROM season WHERE is_active = true")
        active_season = cursor.fetchone()
        
        if not active_season:
            print("❌ No active season found! Please complete Tasks 1-5 first.")
            return False
        
        season_id, season_name, is_active = active_season
        print(f"   ✅ Active season found: {season_name} (ID: {season_id})")
        
        # Check if season_id columns exist
        tables_to_check = ['team', 'round', 'bid', 'match']
        for table in tables_to_check:
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s AND column_name = 'season_id'
            """, (table,))
            if not cursor.fetchone():
                print(f"❌ Table {table} missing season_id column! Please complete Task 3.")
                return False
        
        print("   ✅ All required season columns found")
        
        print("\n📋 Step 2: Creating season context helper module...")
        
        # Create season_context.py helper module
        season_context_code = '''"""
Season Context Helper Module
============================
Provides season-aware functionality for the multi-season system.
"""

from functools import wraps
from flask import g, request, session
from models import db, Season
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
                result = conn.execute("""
                    SELECT id, name, short_name, is_active, status 
                    FROM season 
                    WHERE is_active = true 
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
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
                result = conn.execute("""
                    SELECT id, name, balance, user_id, logo_url, 
                           team_lineage_id, is_continuing_team 
                    FROM team 
                    WHERE season_id = %s 
                    ORDER BY name
                """, (season_id,))
                
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
                result = conn.execute("""
                    SELECT id, position, is_active, start_time, end_time, status 
                    FROM round 
                    WHERE season_id = %s 
                    ORDER BY start_time DESC
                """, (season_id,))
                
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
                result = conn.execute("""
                    SELECT id, name, balance, logo_url, 
                           team_lineage_id, is_continuing_team 
                    FROM team 
                    WHERE user_id = %s AND season_id = %s
                """, (user_id, season_id))
                
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
'''
        
        season_context_path = os.path.join(APP_DIR, "season_context.py")
        with open(season_context_path, 'w') as f:
            f.write(season_context_code)
        
        print(f"   ✅ Created season_context.py at {season_context_path}")
        
        print("\n📋 Step 3: Updating models.py for season awareness...")
        
        models_path = os.path.join(APP_DIR, "models.py")
        backup_models = backup_file(models_path)
        print(f"   📋 Created backup: {backup_models}")
        
        # Read current models.py
        with open(models_path, 'r') as f:
            models_content = f.read()
        
        # Add season-aware method to Player model
        if 'def has_bid_from_team(self, team_id, round_id=None):' not in models_content:
            # Find the Player class and update has_bid_from_team method
            player_method_old = """def has_bid_from_team(self, team_id):
        return any(bid.team_id == team_id for bid in self.bids)"""
            
            player_method_new = """def has_bid_from_team(self, team_id, round_id=None):
        \"\"\"Check if team has bid on this player, optionally filtered by round\"\"\"
        if round_id:
            return any(bid.team_id == team_id and bid.round_id == round_id for bid in self.bids)
        return any(bid.team_id == team_id for bid in self.bids)"""
            
            if player_method_old in models_content:
                models_content = models_content.replace(player_method_old, player_method_new)
                print("   ✅ Updated Player.has_bid_from_team() method")
        
        # Add season-aware methods to User model
        user_season_methods = '''
    def get_current_team(self):
        """Get user's team in the current season"""
        from season_context import SeasonContext
        return SeasonContext.get_team_by_user(self.id)
    
    def has_team_in_season(self, season_id):
        """Check if user has a team in a specific season"""
        return self.team is not None and hasattr(self.team, 'season_id') and self.team.season_id == season_id
    
    @property
    def current_season_team(self):
        """Property to get current season team"""
        return self.get_current_team()'''
        
        # Find User class and add methods before the Team class
        if 'def get_current_team(self):' not in models_content:
            user_class_end = models_content.find('class Team(db.Model):')
            if user_class_end != -1:
                models_content = models_content[:user_class_end] + user_season_methods + '\n\n' + models_content[user_class_end:]
                print("   ✅ Added season-aware methods to User model")
        
        # Add season-aware methods to Team model
        team_season_methods = '''
    @property
    def season(self):
        """Get the season this team belongs to"""
        if hasattr(self, 'season_id') and self.season_id:
            # Import here to avoid circular imports
            try:
                from season_context import SeasonContext
                with db.engine.connect() as conn:
                    result = conn.execute("""
                        SELECT id, name, short_name FROM season WHERE id = %s
                    """, (self.season_id,))
                    row = result.fetchone()
                    if row:
                        return {'id': row[0], 'name': row[1], 'short_name': row[2]}
            except Exception:
                pass
        return None
    
    def get_lineage_history(self):
        """Get the complete lineage history of this team"""
        if hasattr(self, 'team_lineage_id') and self.team_lineage_id:
            try:
                with db.engine.connect() as conn:
                    result = conn.execute("""
                        SELECT t.id, t.name, s.name as season_name, t.is_continuing_team
                        FROM team t
                        JOIN season s ON t.season_id = s.id
                        WHERE t.team_lineage_id = %s
                        ORDER BY s.created_at ASC
                    """, (self.team_lineage_id,))
                    
                    history = []
                    for row in result:
                        history.append({
                            'id': row[0],
                            'name': row[1],
                            'season_name': row[2],
                            'is_continuing_team': row[3]
                        })
                    return history
            except Exception:
                pass
        return []'''
        
        if '@property' not in models_content[models_content.find('class Team(db.Model):'):models_content.find('class Category(db.Model):')]:
            # Find end of Team class (before Category class)
            team_class_end = models_content.find('class Category(db.Model):')
            if team_class_end != -1:
                # Find the last method/property in Team class
                team_section = models_content[models_content.find('class Team(db.Model):'):team_class_end]
                last_method_end = team_section.rfind('return None')
                if last_method_end != -1:
                    last_method_end += len('return None')
                    insertion_point = models_content.find('class Team(db.Model):') + last_method_end
                    models_content = models_content[:insertion_point] + team_season_methods + '\n' + models_content[insertion_point:]
                    print("   ✅ Added season-aware methods to Team model")
        
        # Write updated models.py
        with open(models_path, 'w') as f:
            f.write(models_content)
        
        print("\n📋 Step 4: Creating season-aware template helpers...")
        
        template_helpers_code = '''"""
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
'''
        
        template_helpers_path = os.path.join(APP_DIR, "template_helpers.py")
        with open(template_helpers_path, 'w') as f:
            f.write(template_helpers_code)
        
        print(f"   ✅ Created template_helpers.py at {template_helpers_path}")
        
        print("\n📋 Step 5: Updating main app.py for season awareness...")
        
        app_path = os.path.join(APP_DIR, "app.py")
        backup_app = backup_file(app_path)
        print(f"   📋 Created backup: {backup_app}")
        
        # Read current app.py
        with open(app_path, 'r') as f:
            app_content = f.read()
        
        # Add season context imports
        import_addition = """from season_context import SeasonContext, season_aware, get_current_season_id, get_user_current_team
from template_helpers import get_current_season, get_user_team_in_season, format_season_name, is_continuing_team, get_team_lineage_display"""
        
        if 'from season_context import' not in app_content:
            # Find the import section and add our imports
            import_section_end = app_content.find('# Import performance optimizations')
            if import_section_end != -1:
                app_content = app_content[:import_section_end] + import_addition + '\n\n' + app_content[import_section_end:]
                print("   ✅ Added season context imports to app.py")
        
        # Add template context processor for season awareness
        context_processor_code = '''
# Season-aware template context processor
@app.context_processor
def inject_season_context():
    """Inject season context into all templates"""
    return {
        'current_season': get_current_season(),
        'get_user_team_in_season': get_user_team_in_season,
        'format_season_name': format_season_name,
        'is_continuing_team': is_continuing_team,
        'get_team_lineage_display': get_team_lineage_display,
        'SeasonContext': SeasonContext
    }
'''
        
        if '@app.context_processor' not in app_content:
            # Find a good place to add context processor (after login manager setup)
            login_manager_end = app_content.find("login_manager.login_view = 'login'")
            if login_manager_end != -1:
                login_manager_end = app_content.find('\n', login_manager_end) + 1
                app_content = app_content[:login_manager_end] + context_processor_code + '\n' + app_content[login_manager_end:]
                print("   ✅ Added season context processor to app.py")
        
        # Write updated app.py
        with open(app_path, 'w') as f:
            f.write(app_content)
        
        print("\n📋 Step 6: Creating user dashboard updates...")
        
        # Check if templates directory exists
        templates_dir = os.path.join(APP_DIR, "templates")
        if not os.path.exists(templates_dir):
            print("   ⚠️  Templates directory not found, skipping template updates")
        else:
            # Look for dashboard template
            dashboard_templates = ['dashboard.html', 'index.html', 'main.html']
            dashboard_found = False
            
            for template_name in dashboard_templates:
                template_path = os.path.join(templates_dir, template_name)
                if os.path.exists(template_path):
                    backup_template = backup_file(template_path)
                    print(f"   📋 Found dashboard template: {template_name}")
                    print(f"   📋 Created backup: {backup_template}")
                    
                    # Read template
                    with open(template_path, 'r') as f:
                        template_content = f.read()
                    
                    # Add season info display
                    season_info_html = '''
<!-- Season Information Panel -->
{% if current_season %}
<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
    <div class="flex items-center justify-between">
        <div>
            <h3 class="text-lg font-semibold text-blue-900">{{ format_season_name(current_season) }}</h3>
            <p class="text-blue-700">Active Season</p>
        </div>
        <div class="text-right">
            {% if current_user.current_season_team %}
                <p class="text-sm text-blue-600">Your Team:</p>
                <p class="font-semibold text-blue-900">{{ get_team_lineage_display(current_user.current_season_team) }}</p>
                {% if is_continuing_team(current_user.current_season_team) %}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                        Continuing Team
                    </span>
                {% else %}
                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                        New Team
                    </span>
                {% endif %}
            {% else %}
                <p class="text-sm text-gray-600">No team registered</p>
            {% endif %}
        </div>
    </div>
</div>
{% endif %}
'''
                    
                    if '<!-- Season Information Panel -->' not in template_content:
                        # Find a good place to insert (after any existing header/navigation)
                        insert_markers = ['{% extends', '{% block content %}', '<div class="container', '<main']
                        insert_point = None
                        
                        for marker in insert_markers:
                            pos = template_content.find(marker)
                            if pos != -1:
                                # Find the end of the line/tag
                                insert_point = template_content.find('\n', pos) + 1
                                break
                        
                        if insert_point:
                            template_content = template_content[:insert_point] + season_info_html + template_content[insert_point:]
                            
                            # Write updated template
                            with open(template_path, 'w') as f:
                                f.write(template_content)
                            
                            print(f"   ✅ Updated {template_name} with season information")
                            dashboard_found = True
                            break
            
            if not dashboard_found:
                print("   ⚠️  No dashboard template found to update")
        
        print("\n📋 Step 7: Creating database helper functions...")
        
        # Add season-aware database helper functions
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_user_current_team(user_id_param INTEGER)
            RETURNS TABLE(
                team_id INTEGER,
                team_name VARCHAR(50),
                team_balance INTEGER,
                team_lineage_id INTEGER,
                is_continuing_team BOOLEAN,
                season_name VARCHAR(100)
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    t.id,
                    t.name,
                    t.balance,
                    t.team_lineage_id,
                    t.is_continuing_team,
                    s.name
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.user_id = user_id_param 
                  AND s.is_active = true;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created get_user_current_team() database function")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_season_statistics(season_id_param INTEGER DEFAULT NULL)
            RETURNS TABLE(
                season_id INTEGER,
                season_name VARCHAR(100),
                total_teams BIGINT,
                continuing_teams BIGINT,
                new_teams BIGINT,
                total_rounds BIGINT,
                active_rounds BIGINT,
                total_bids BIGINT
            ) AS $$
            DECLARE
                target_season_id INTEGER;
            BEGIN
                -- Use provided season_id or get current active season
                IF season_id_param IS NULL THEN
                    SELECT id INTO target_season_id 
                    FROM season 
                    WHERE is_active = true 
                    LIMIT 1;
                ELSE
                    target_season_id := season_id_param;
                END IF;
                
                -- Return statistics for the target season
                RETURN QUERY
                SELECT 
                    s.id,
                    s.name,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as total_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id AND is_continuing_team = true) as continuing_teams,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id AND is_continuing_team = false) as new_teams,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as total_rounds,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id AND is_active = true) as active_rounds,
                    (SELECT COUNT(*) FROM bid WHERE season_id = s.id) as total_bids
                FROM season s
                WHERE s.id = target_season_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Created get_season_statistics() database function")
        
        # Commit database changes
        conn.commit()
        
        print("\n📋 Step 8: Verification...")
        
        # Verify files were created/updated
        files_to_check = [
            ("season_context.py", "Season context helper module"),
            ("template_helpers.py", "Template helper functions"),
            ("models.py", "Updated models with season awareness"),
            ("app.py", "Updated main application")
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
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN ('get_user_current_team', 'get_season_statistics')
            ORDER BY routine_name
        """)
        
        db_functions = [row[0] for row in cursor.fetchall()]
        expected_functions = ['get_season_statistics', 'get_user_current_team']
        
        print(f"   📊 Database functions: {len(db_functions)}/{len(expected_functions)}")
        for func in db_functions:
            print(f"      ✅ {func}()")
        
        # Test season context functionality
        cursor.execute("SELECT * FROM get_season_statistics()")
        stats = cursor.fetchone()
        
        if stats:
            s_id, s_name, teams, cont_teams, new_teams, rounds, active_rounds, bids = stats
            print(f"   📊 Current Season Statistics:")
            print(f"      • Season: {s_name} (ID: {s_id})")
            print(f"      • Teams: {teams} total ({cont_teams} continuing, {new_teams} new)")
            print(f"      • Rounds: {rounds} total ({active_rounds} active)")
            print(f"      • Bids: {bids} total")
        
        if all_files_ok and len(db_functions) == len(expected_functions):
            print("\n🎉 TASK 6 COMPLETED SUCCESSFULLY!")
            print("✅ Updated application code for multi-season awareness")
            print("✅ Created season context management system")
            print("✅ Added template helpers for season information")
            print("✅ Updated models with season-aware methods")
            print("✅ Enhanced main application with season context")
            print("✅ Created database helper functions")
            
            print("\n📝 KEY ENHANCEMENTS AVAILABLE:")
            print("   • Season-aware user authentication and team access")
            print("   • Template context with current season information") 
            print("   • Model methods for accessing season-specific data")
            print("   • Database functions for season statistics")
            print("   • Team lineage tracking and display")
            
            print("\n📋 NEXT STEPS TO COMPLETE INTEGRATION:")
            print("   • Update route handlers to use season context")
            print("   • Test the updated application functionality")
            print("   • Update existing templates to show season information")
            print("   • Add season management interfaces")
            
            return True
        else:
            print(f"\n❌ TASK 6 FAILED:")
            print(f"   • Files created: {'✅' if all_files_ok else '❌'}")
            print(f"   • Database functions: {len(db_functions)}/{len(expected_functions)}")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 6: {e}")
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

def rollback_task_06():
    """Rollback Task 6 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 6: Remove Season-Aware Application Updates")
        print("⚠️  WARNING: This will revert application code changes!")
        
        response = input("Are you sure you want to rollback Task 6? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        # Remove created files
        files_to_remove = [
            "season_context.py",
            "template_helpers.py"
        ]
        
        for filename in files_to_remove:
            filepath = os.path.join(APP_DIR, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
                print(f"   ✅ Removed {filename}")
        
        # Restore backups if they exist
        backup_files = []
        if os.path.exists(BACKUP_DIR):
            for file in os.listdir(BACKUP_DIR):
                if file.endswith('.backup_'):
                    backup_files.append(file)
        
        if backup_files:
            print("   📋 Available backups to restore:")
            for backup in backup_files:
                print(f"      • {backup}")
            
            restore = input("Restore from backups? (y/N): ").lower().strip()
            if restore == 'y':
                # Restore most recent backups
                for original_name in ['models.py', 'app.py']:
                    # Find most recent backup
                    matching_backups = [f for f in backup_files if f.startswith(original_name + '.backup_')]
                    if matching_backups:
                        latest_backup = max(matching_backups)
                        backup_path = os.path.join(BACKUP_DIR, latest_backup)
                        original_path = os.path.join(APP_DIR, original_name)
                        
                        shutil.copy2(backup_path, original_path)
                        print(f"   ✅ Restored {original_name} from {latest_backup}")
        
        # Remove database functions
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        functions_to_drop = ['get_user_current_team', 'get_season_statistics']
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER) CASCADE")
        
        conn.commit()
        
        print("✅ Task 6 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 6 rollback: {e}")
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
        success = rollback_task_06()
    else:
        success = execute_task_06()
    
    sys.exit(0 if success else 1)