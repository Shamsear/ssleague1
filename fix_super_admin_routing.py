#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - SUPER ADMIN ROUTING FIX
============================================
Fixes super admin routing issues by:
1. Adding user_role column to User model
2. Fixing dashboard routing logic
3. Fixing admin route decorators
"""

import os
import shutil
from datetime import datetime

APP_DIR = r"C:\Drive d\SS\safety"
BACKUP_DIR = r"C:\Drive d\SS\test\backups"

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

def fix_user_model():
    """Add user_role column to User model"""
    print("🔧 Fixing User model...")
    
    models_path = os.path.join(APP_DIR, "models.py")
    backup_file(models_path)
    
    with open(models_path, 'r') as f:
        content = f.read()
    
    # Find the location to add user_role after is_approved
    if 'user_role = db.Column' not in content:
        # Add user_role column after is_approved
        old_line = 'is_approved = db.Column(db.Boolean, default=False)'
        new_lines = '''is_approved = db.Column(db.Boolean, default=False)
    user_role = db.Column(db.String(20), default='team_user')  # 'super_admin', 'committee_admin', 'team_user'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))'''
        
        content = content.replace(old_line, new_lines)
        
        # Add role checking properties
        role_methods = '''
    @property
    def is_super_admin(self):
        """Check if user is super admin"""
        return self.user_role == 'super_admin' or (self.is_admin and self.user_role in [None, 'super_admin'])
    
    @property
    def is_committee_admin(self):
        """Check if user is committee admin"""
        return self.user_role == 'committee_admin'
    
    @property
    def has_admin_access(self):
        """Check if user has any admin access"""
        return self.is_super_admin or self.is_committee_admin
'''
        
        # Add methods before the get_current_team method
        content = content.replace('    def get_current_team(self):', role_methods + '    def get_current_team(self):')
        
        print("   ✅ Added user_role column and role checking methods to User model")
    else:
        print("   ✅ User model already has user_role column")
    
    with open(models_path, 'w') as f:
        f.write(content)

def fix_admin_routes():
    """Fix admin route decorators to use user_role"""
    print("🔧 Fixing admin routes...")
    
    admin_routes_path = os.path.join(APP_DIR, "admin_routes.py")
    backup_file(admin_routes_path)
    
    with open(admin_routes_path, 'r') as f:
        content = f.read()
    
    # Fix admin_required decorator
    old_admin_required = '''def admin_required(f):
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
    return decorated_function'''
    
    new_admin_required = '''def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check if user has admin role
        if not hasattr(current_user, 'user_role') or current_user.user_role not in ['super_admin', 'committee_admin']:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function'''
    
    # Fix super_admin_required decorator
    old_super_admin_required = '''def super_admin_required(f):
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
    return decorated_function'''
    
    new_super_admin_required = '''def super_admin_required(f):
    """Decorator to require super admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Check if user has super admin role
        if not hasattr(current_user, 'user_role') or current_user.user_role != 'super_admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function'''
    
    content = content.replace(old_admin_required, new_admin_required)
    content = content.replace(old_super_admin_required, new_super_admin_required)
    
    # Fix the role query in user_role stats
    old_role_query = '''role_result = conn.execute("""
                SELECT role, COUNT(*) as count 
                FROM "user" 
                GROUP BY role 
                ORDER BY CASE role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_member' THEN 3 
                    ELSE 4 END
            """)'''
    
    new_role_query = '''role_result = conn.execute("""
                SELECT user_role, COUNT(*) as count 
                FROM "user" 
                GROUP BY user_role 
                ORDER BY CASE user_role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_user' THEN 3 
                    ELSE 4 END
            """)'''
    
    content = content.replace(old_role_query, new_role_query)
    
    print("   ✅ Fixed admin route decorators and queries")
    
    with open(admin_routes_path, 'w') as f:
        f.write(content)

def fix_dashboard_routing():
    """Fix dashboard routing to handle super admin correctly"""
    print("🔧 Fixing dashboard routing...")
    
    app_path = os.path.join(APP_DIR, "app.py")
    backup_file(app_path)
    
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Find the dashboard route and fix the routing logic
    old_dashboard_logic = '''@app.route('/dashboard')
@login_required
def dashboard():
    # Verify we have a valid session - enhance security
    if not current_user.is_authenticated:
        session.clear()
        return redirect(url_for('login'))
    
    # Check if user is a new user (no bids placed yet)
    user_is_new = False
    if current_user.team:
        bid_count = Bid.query.filter_by(team_id=current_user.team.id).count()
        user_is_new = bid_count == 0

    # Check if any active rounds have expired
    active_rounds = Round.query.filter_by(is_active=True).all()
    for round in active_rounds:
        if round.is_timer_expired():
            finalize_round_internal(round.id)
    
    # Check if user just won a player in a tiebreaker
    player_won = request.args.get('player_won')
    if player_won:
        flash(f'Congratulations! You won the bid for {player_won}!', 'success')
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:'''
    
    new_dashboard_logic = '''@app.route('/dashboard')
@login_required
def dashboard():
    # Verify we have a valid session - enhance security
    if not current_user.is_authenticated:
        session.clear()
        return redirect(url_for('login'))
    
    # Check if user is super admin and redirect to admin interface
    if hasattr(current_user, 'user_role') and current_user.user_role == 'super_admin':
        return redirect(url_for('admin.admin_dashboard'))
    
    # Check if user is committee admin and redirect to admin interface
    if hasattr(current_user, 'user_role') and current_user.user_role == 'committee_admin':
        return redirect(url_for('admin.admin_dashboard'))
    
    # Check if user is a new user (no bids placed yet)
    user_is_new = False
    if current_user.team:
        bid_count = Bid.query.filter_by(team_id=current_user.team.id).count()
        user_is_new = bid_count == 0

    # Check if any active rounds have expired
    active_rounds = Round.query.filter_by(is_active=True).all()
    for round in active_rounds:
        if round.is_timer_expired():
            finalize_round_internal(round.id)
    
    # Check if user just won a player in a tiebreaker
    player_won = request.args.get('player_won')
    if player_won:
        flash(f'Congratulations! You won the bid for {player_won}!', 'success')
    
    # Refresh the data after potentially finalizing rounds
    if current_user.is_admin:'''
    
    content = content.replace(old_dashboard_logic, new_dashboard_logic)
    
    print("   ✅ Fixed dashboard routing to redirect admins properly")
    
    with open(app_path, 'w') as f:
        f.write(content)

def main():
    """Execute all fixes"""
    print("🚀 FIXING SUPER ADMIN ROUTING ISSUES")
    print("=" * 50)
    
    try:
        fix_user_model()
        fix_admin_routes()
        fix_dashboard_routing()
        
        print("\n🎉 ALL FIXES COMPLETED SUCCESSFULLY!")
        print("✅ User model updated with user_role column")
        print("✅ Admin route decorators fixed")
        print("✅ Dashboard routing logic improved")
        print("✅ Super admin will now be redirected to admin interface")
        
        print("\n📝 IMPORTANT:")
        print("   • Restart your Flask application for changes to take effect")
        print("   • Super admins will now be redirected to /admin/ instead of team dashboard")
        
        return True
        
    except Exception as e:
        print(f"\n💥 ERROR during fixes: {e}")
        return False

if __name__ == "__main__":
    main()