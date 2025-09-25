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

def check_all_user_roles():
    """Check all users and their roles"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, user_role, is_admin, is_approved 
                FROM "user" 
                ORDER BY user_role, username
            """))
            
            users = result.fetchall()
            
            print("👥 ALL USERS AND THEIR ROLES:")
            print("=" * 70)
            print(f"{'ID':<4} {'Username':<15} {'Role':<15} {'Is Admin':<10} {'Approved':<10}")
            print("-" * 70)
            
            for user in users:
                print(f"{user[0]:<4} {user[1]:<15} {user[2]:<15} {user[3]:<10} {user[4]:<10}")
            
            print("\n📊 ROLE SUMMARY:")
            role_counts = conn.execute(text("""
                SELECT user_role, COUNT(*) as count 
                FROM "user" 
                GROUP BY user_role 
                ORDER BY CASE user_role 
                    WHEN 'super_admin' THEN 1 
                    WHEN 'committee_admin' THEN 2 
                    WHEN 'team_user' THEN 3 
                    ELSE 4 END
            """))
            
            for role, count in role_counts:
                role_display = {
                    'super_admin': 'Super Admins',
                    'committee_admin': 'Committee Admins', 
                    'team_user': 'Team Users'
                }.get(role, role)
                print(f"  {role_display}: {count}")
                
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("🔍 CHECKING USER ROLES IN DATABASE")
    print("=" * 70)
    
    success = check_all_user_roles()
    
    print("\n" + "=" * 70)
    if success:
        print("✅ Role check complete!")
        print("\n💡 Committee admins should now be able to:")
        print("  - Access /admin/ routes")
        print("  - See the admin dashboard")
        print("  - View most admin features (except super-admin-only ones)")
        print("\n🔒 Super-admin-only features:")
        print("  - Creating new seasons")
        print("  - Activating/deactivating seasons")
        print("  - Some advanced system management")
    else:
        print("❌ Error checking roles")