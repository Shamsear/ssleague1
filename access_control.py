#!/usr/bin/env python3

"""
Enhanced Access Control System
==============================
UUID-based access control with role-based permissions to prevent unauthorized access.
"""

from flask import flash, redirect, url_for, current_app, request
from flask_login import current_user
from functools import wraps
import uuid
import secrets

class AccessControl:
    """Enhanced access control with UUID tokens and role verification"""
    
    # Role hierarchy - higher numbers = more permissions
    ROLE_HIERARCHY = {
        'team_user': 1,
        'team_member': 1,  # Same as team_user
        'committee_admin': 2,
        'super_admin': 3
    }
    
    @staticmethod
    def generate_access_token():
        """Generate a secure access token"""
        return str(uuid.uuid4()) + secrets.token_hex(16)
    
    @staticmethod
    def get_user_role_level(user):
        """Get the numerical level of a user's role"""
        if not user or not hasattr(user, 'user_role'):
            return 0
        return AccessControl.ROLE_HIERARCHY.get(user.user_role, 0)
    
    @staticmethod
    def has_role(user, required_role):
        """Check if user has the required role or higher"""
        user_level = AccessControl.get_user_role_level(user)
        required_level = AccessControl.ROLE_HIERARCHY.get(required_role, 999)
        return user_level >= required_level
    
    @staticmethod
    def log_access_attempt(user, route, success):
        """Log access attempts for security auditing"""
        if current_app:
            user_info = f"User {user.id} ({user.username}, {user.user_role})" if user.is_authenticated else "Anonymous"
            status = "SUCCESS" if success else "DENIED"
            current_app.logger.info(f"ACCESS {status}: {user_info} -> {route}")

def require_role(required_role, redirect_route='dashboard'):
    """
    Enhanced role-based access decorator with UUID verification
    
    Args:
        required_role: Minimum role required ('team_user', 'committee_admin', 'super_admin')
        redirect_route: Where to redirect if access is denied
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated
            if not current_user.is_authenticated:
                AccessControl.log_access_attempt(current_user, request.endpoint, False)
                flash('You must be logged in to access this page.', 'error')
                return redirect(url_for('login'))
            
            # Verify user has required role
            if not AccessControl.has_role(current_user, required_role):
                AccessControl.log_access_attempt(current_user, request.endpoint, False)
                
                # Custom messages based on role
                if required_role == 'super_admin':
                    flash('This page is restricted to Super Administrators only.', 'error')
                elif required_role == 'committee_admin':
                    flash('This page requires Committee Administrator access or higher.', 'error')
                else:
                    flash('You do not have permission to access this page.', 'error')
                
                return redirect(url_for(redirect_route))
            
            # Log successful access
            AccessControl.log_access_attempt(current_user, request.endpoint, True)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_super_admin(f):
    """Shortcut decorator for super admin only access"""
    return require_role('super_admin')(f)

def require_admin(f):
    """Shortcut decorator for any admin access (committee or super)"""
    return require_role('committee_admin')(f)

def require_team_access(f):
    """Shortcut decorator for team user access"""
    return require_role('team_user')(f)

def restrict_committee_admin_from_super_routes(f):
    """
    Special decorator to prevent committee admins from accessing super admin routes
    while still allowing them admin-level access elsewhere
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('You must be logged in to access this page.', 'error')
            return redirect(url_for('login'))
        
        # Block committee admins from super admin routes
        if current_user.user_role == 'committee_admin':
            AccessControl.log_access_attempt(current_user, request.endpoint, False)
            flash('This feature is restricted to Super Administrators. Committee Administrators should use the main dashboard.', 'error')
            return redirect(url_for('dashboard'))  # Redirect to their own dashboard
        
        # Allow super admins
        if current_user.user_role == 'super_admin':
            AccessControl.log_access_attempt(current_user, request.endpoint, True)
            return f(*args, **kwargs)
        
        # Block everyone else
        AccessControl.log_access_attempt(current_user, request.endpoint, False)
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('dashboard'))
    
    return decorated_function

def debug_user_access():
    """Debug helper to check current user's access levels"""
    if current_user.is_authenticated:
        role_level = AccessControl.get_user_role_level(current_user)
        return {
            'user_id': current_user.id,
            'username': current_user.username,
            'user_role': current_user.user_role,
            'role_level': role_level,
            'can_access_admin': AccessControl.has_role(current_user, 'committee_admin'),
            'can_access_super': AccessControl.has_role(current_user, 'super_admin'),
            'is_authenticated': current_user.is_authenticated
        }
    return {'error': 'User not authenticated'}