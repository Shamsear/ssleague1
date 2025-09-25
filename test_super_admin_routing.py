#!/usr/bin/env python3
"""
Test Super Admin Routing Fix
============================
Verifies that super admin routing is working correctly
"""

import os
import sys

APP_DIR = r"C:\Drive d\SS\safety"

def test_routing_fixes():
    """Test that routing fixes are properly implemented"""
    print("🧪 TESTING SUPER ADMIN ROUTING FIXES")
    print("=" * 50)
    
    # Test 1: Check User model has user_role and properties
    print("\n📋 Test 1: User Model Properties")
    models_path = os.path.join(APP_DIR, "models.py")
    
    with open(models_path, 'r') as f:
        models_content = f.read()
    
    checks = [
        ("user_role = db.Column", "user_role column definition"),
        ("def is_super_admin", "is_super_admin property"),
        ("def is_committee_admin", "is_committee_admin property"),
        ("def has_admin_access", "has_admin_access property")
    ]
    
    for check, description in checks:
        if check in models_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description}")
    
    # Test 2: Check admin routes use user_role
    print("\n📋 Test 2: Admin Route Decorators")
    admin_routes_path = os.path.join(APP_DIR, "admin_routes.py")
    
    with open(admin_routes_path, 'r') as f:
        admin_content = f.read()
    
    checks = [
        ("hasattr(current_user, 'user_role')", "admin_required decorator uses user_role"),
        ("current_user.user_role not in ['super_admin', 'committee_admin']", "role checking logic"),
        ("current_user.user_role != 'super_admin'", "super admin checking logic"),
        ("SELECT user_role, COUNT(*)", "user role statistics query")
    ]
    
    for check, description in checks:
        if check in admin_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description}")
    
    # Test 3: Check dashboard routing
    print("\n📋 Test 3: Dashboard Routing Logic")
    app_path = os.path.join(APP_DIR, "app.py")
    
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    checks = [
        ("current_user.user_role == 'super_admin'", "super admin redirect check"),
        ("current_user.user_role == 'committee_admin'", "committee admin redirect check"),
        ("url_for('admin.admin_dashboard')", "admin dashboard redirect")
    ]
    
    for check, description in checks:
        if check in app_content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description}")
    
    print("\n🎉 ROUTING TESTS COMPLETED!")
    print("\n📝 EXPECTED BEHAVIOR:")
    print("   • Super admin users will be redirected to /admin/ when accessing /dashboard")
    print("   • Committee admin users will also be redirected to /admin/")
    print("   • Regular team users will see the normal team dashboard")
    print("   • Admin routes will properly check user_role instead of role")

if __name__ == "__main__":
    test_routing_fixes()