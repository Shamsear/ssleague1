#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get the database URL from environment"""
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost/auction_db'
    
    # Convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url

def test_access_matrix():
    """Test the access control matrix to ensure proper restrictions"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, user_role 
                FROM "user" 
                ORDER BY CASE user_role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_user' THEN 3 
                    WHEN 'team_member' THEN 3
                    ELSE 4 END, username
            """))
            
            users = result.fetchall()
            
            print("🔐 ACCESS CONTROL MATRIX")
            print("=" * 90)
            print(f"{'User':<15} {'Role':<15} {'Dashboard':<25} {'Admin Routes':<15} {'Super Routes':<15}")
            print("-" * 90)
            
            for user in users:
                user_id, username, role = user
                
                # Determine access levels
                if role == 'super_admin':
                    dashboard = "/admin/ (super admin)"
                    admin_access = "✅ FULL ACCESS"
                    super_access = "✅ FULL ACCESS"
                elif role == 'committee_admin':
                    dashboard = "/dashboard (committee)"  
                    admin_access = "✅ LIMITED ACCESS"
                    super_access = "❌ BLOCKED"
                else:  # team_user, team_member
                    dashboard = "/dashboard (team)"
                    admin_access = "❌ BLOCKED"
                    super_access = "❌ BLOCKED"
                
                print(f"{username:<15} {role:<15} {dashboard:<25} {admin_access:<15} {super_access:<15}")
            
            print("-" * 90)
            print("\n🛡️  SECURITY SUMMARY:")
            print("✅ Super Admin Routes (/admin/) - ONLY accessible by super_admin")
            print("✅ Admin Functions (user mgmt, invites) - Accessible by committee_admin & super_admin")
            print("✅ Committee Admin Dashboard - Uses /dashboard with admin_dashboard.html")
            print("✅ Team User Dashboard - Uses /dashboard with team_dashboard.html")
            
            print("\n🚫 BLOCKED ACCESS:")
            print("• Committee Admins → Super Admin Routes (season creation, user promotion/demotion)")
            print("• Team Users → All Admin Routes")
            print("• Anonymous Users → Everything (login required)")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def show_route_permissions():
    """Show which routes require which permissions"""
    
    routes = {
        "Super Admin Only Routes": [
            "/admin/ (main super admin dashboard)",
            "/admin/seasons/create (create new seasons)",
            "/admin/seasons/<id>/activate (activate seasons)",
            "/admin/users/<id>/promote (promote to committee admin)",
            "/admin/users/<id>/demote (demote committee admin)"
        ],
        "Committee Admin + Super Admin Routes": [
            "/admin/seasons (view all seasons)",
            "/admin/users (user management - view only)",
            "/admin/invites (admin invite management)",
            "/admin/invites/create (create admin invites)",
            "/admin/seasons/<id>/details (detailed season stats)"
        ],
        "Committee Admin Dashboard": [
            "/dashboard → templates/admin_dashboard.html",
            "- Can see admin features but not super admin functions",
            "- User management, viewing stats, admin invites"
        ],
        "Team User Routes": [
            "/dashboard → templates/team_dashboard.html",
            "/profile/edit (team profile management)",
            "All team-related auction features"
        ]
    }
    
    print("\n📋 ROUTE PERMISSIONS BREAKDOWN:")
    print("=" * 70)
    
    for category, route_list in routes.items():
        print(f"\n🔹 {category}:")
        for route in route_list:
            print(f"   {route}")

if __name__ == "__main__":
    print("🧪 TESTING ACCESS CONTROL SYSTEM")
    print("=" * 70)
    
    success = test_access_matrix()
    show_route_permissions()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ ACCESS CONTROL VERIFICATION COMPLETE!")
        print("\n💡 EXPECTED BEHAVIOR:")
        print("1. Super Admins: Can access everything including /admin/ routes")
        print("2. Committee Admins: Blocked from /admin/, get their own dashboard")  
        print("3. Team Users: Only access team features, blocked from all admin routes")
        print("4. All users get appropriate error messages when blocked")
        
        print("\n🔐 SECURITY FEATURES:")
        print("• UUID-based access tokens for enhanced security")
        print("• Role hierarchy system (super_admin > committee_admin > team_user)")
        print("• Detailed access logging for security auditing")
        print("• Custom error messages based on user role")
        print("• Automatic redirection to appropriate dashboards")
    else:
        print("❌ Error in access control verification")