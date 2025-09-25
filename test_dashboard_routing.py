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

def test_routing_logic():
    """Test what dashboard each user type should get"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, user_role 
                FROM "user" 
                WHERE user_role IN ('super_admin', 'committee_admin')
                ORDER BY user_role, username
            """))
            
            admin_users = result.fetchall()
            
            print("🔀 DASHBOARD ROUTING TEST")
            print("=" * 70)
            
            for user in admin_users:
                user_id, username, role = user
                print(f"\n👤 User: {username} (Role: {role})")
                
                if role == 'super_admin':
                    print("   🎯 Should redirect to: /admin/ (admin routes)")
                    print("   📄 Template: templates/admin/dashboard.html")
                    print("   🔧 Features: Full admin access (season creation, etc.)")
                    
                elif role == 'committee_admin':
                    print("   🎯 Should go to: /dashboard (main dashboard)")
                    print("   📄 Template: templates/admin_dashboard.html")
                    print("   🔧 Features: Committee admin access (no season creation)")
                
            print(f"\n" + "=" * 70)
            print("✅ EXPECTED BEHAVIOR:")
            print("- Super admins: /admin/ → templates/admin/dashboard.html")
            print("- Committee admins: /dashboard → templates/admin_dashboard.html")
            print("- Team users: /dashboard → templates/team_dashboard.html")
            
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_routing_logic()
    
    print(f"\n💡 To test:")
    print(f"1. Login as super admin (admin) - should go to /admin/")
    print(f"2. Login as committee admin (Committe1/Committe2) - should go to /dashboard")
    print(f"3. Each should see their respective templates and features")