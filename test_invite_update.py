#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

def get_database_url():
    """Get the database URL from environment"""
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost/auction_db'
    
    # Convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url

def check_invite_before_and_after(invite_token):
    """Check invite usage before and after simulating an update"""
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    print(f"🔍 Testing invite update for token: {invite_token}")
    print("=" * 70)
    
    try:
        # Check current state
        with engine.connect() as conn:
            invite_result = conn.execute(text("""
                SELECT id, invite_token, current_uses, max_uses, used_at, is_active
                FROM admin_invite 
                WHERE invite_token = :token
            """), {'token': invite_token})
            
            invite_data = invite_result.fetchone()
            
            if not invite_data:
                print("❌ Invite not found!")
                return False
                
            print("📊 BEFORE UPDATE:")
            print(f"   ID: {invite_data[0]}")
            print(f"   Token: {invite_data[1][:10]}...")
            print(f"   Current uses: {invite_data[2]}")
            print(f"   Max uses: {invite_data[3]}")
            print(f"   Used at: {invite_data[4]}")
            print(f"   Is active: {invite_data[5]}")
        
        # Simulate the update that happens during registration
        print(f"\n🔄 Simulating invite usage update...")
        
        with engine.begin() as conn:  # Use begin() for auto-commit like in the app
            result = conn.execute(text("""
                UPDATE admin_invite 
                SET current_uses = current_uses + 1, used_at = :used_at
                WHERE invite_token = :token
            """), {
                'token': invite_token, 
                'used_at': datetime.utcnow()
            })
            
            print(f"   Rows affected: {result.rowcount}")
            
            if result.rowcount == 0:
                print("❌ No rows were updated!")
                return False
            else:
                print("✅ Update executed successfully")
        
        # Check state after update
        with engine.connect() as conn:
            invite_result = conn.execute(text("""
                SELECT id, invite_token, current_uses, max_uses, used_at, is_active
                FROM admin_invite 
                WHERE invite_token = :token
            """), {'token': invite_token})
            
            updated_invite = invite_result.fetchone()
            
            print("\n📊 AFTER UPDATE:")
            print(f"   ID: {updated_invite[0]}")
            print(f"   Token: {updated_invite[1][:10]}...")
            print(f"   Current uses: {updated_invite[2]}")
            print(f"   Max uses: {updated_invite[3]}")
            print(f"   Used at: {updated_invite[4]}")
            print(f"   Is active: {updated_invite[5]}")
            
            # Check if usage was incremented
            if updated_invite[2] > invite_data[2]:
                print(f"\n✅ SUCCESS: Usage count incremented from {invite_data[2]} to {updated_invite[2]}")
                
                # Check if invite should be deactivated
                if updated_invite[2] >= updated_invite[3]:
                    print(f"⚠️  NOTE: Invite is now fully used ({updated_invite[2]}/{updated_invite[3]})")
                else:
                    print(f"✅ Invite still has {updated_invite[3] - updated_invite[2]} uses remaining")
                    
                return True
            else:
                print(f"❌ FAILED: Usage count did not change (still {updated_invite[2]})")
                return False
                
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

def reset_invite_usage(invite_token):
    """Reset invite usage to 0 for testing purposes"""
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    print(f"\n🔄 Resetting invite usage for token: {invite_token}")
    
    try:
        with engine.begin() as conn:
            result = conn.execute(text("""
                UPDATE admin_invite 
                SET current_uses = 0, used_at = NULL
                WHERE invite_token = :token
            """), {'token': invite_token})
            
            if result.rowcount > 0:
                print("✅ Invite usage reset successfully")
                return True
            else:
                print("❌ Failed to reset invite usage")
                return False
                
    except Exception as e:
        print(f"❌ Error resetting invite: {e}")
        return False

if __name__ == "__main__":
    token = "nYuIX7bjdugrc7ZUzaVJyyT2uVIcEA6l"
    
    print("🧪 TESTING ADMIN INVITE UPDATE MECHANISM")
    print("=" * 70)
    
    # First, reset the invite for testing
    reset_invite_usage(token)
    
    # Test the update mechanism
    success = check_invite_before_and_after(token)
    
    print("\n" + "=" * 70)
    if success:
        print("✅ CONCLUSION: Invite update mechanism works correctly!")
        print("💡 If the usage count is still not updating in your app,")
        print("   the issue might be in the Flask application logic.")
    else:
        print("❌ CONCLUSION: Invite update mechanism has issues")
    
    print(f"\n💡 You can now test with the reset invite:")
    print(f"   http://127.0.0.1:5000/register?invite={token}")