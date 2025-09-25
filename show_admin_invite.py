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

def show_current_invites():
    """Show all current admin invites with their full details"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Get all admin invites
            invites = conn.execute(text("""
                SELECT ai.id, ai.invite_token, ai.expires_at, ai.max_uses, ai.current_uses, 
                       ai.is_active, ai.description, ai.created_at,
                       u.username as created_by_username
                FROM admin_invite ai
                LEFT JOIN "user" u ON ai.created_by = u.id
                ORDER BY ai.created_at DESC;
            """))
            
            print("🎫 All Admin Invites:")
            print("-" * 80)
            
            for invite in invites:
                print(f"ID: {invite[0]}")
                print(f"Token: {invite[1]}")
                print(f"Full Registration URL: http://localhost:5000/register?invite={invite[1]}")
                print(f"Expires: {invite[2]}")
                print(f"Uses: {invite[4]}/{invite[3]}")
                print(f"Active: {invite[5]}")
                print(f"Description: {invite[6]}")
                print(f"Created: {invite[7]}")
                print(f"Created by: {invite[8]}")
                
                # Check if expired
                if invite[2] and datetime.utcnow() > invite[2]:
                    print("❌ STATUS: EXPIRED")
                elif invite[4] >= invite[3]:
                    print("❌ STATUS: FULLY USED")
                elif not invite[5]:
                    print("❌ STATUS: INACTIVE")
                else:
                    print("✅ STATUS: VALID AND READY TO USE")
                
                print("-" * 80)
                
    except Exception as e:
        print(f"❌ Error: {e}")

def test_specific_token_validation(token):
    """Test validation with a specific token"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Simulate the exact query from the app
            invite_result = conn.execute(text("""
                SELECT id, expires_at, max_uses, current_uses, is_active, description
                FROM admin_invite 
                WHERE invite_token = :token AND is_active = true
            """), {'token': token})
            
            invite_data = invite_result.fetchone()
            
            print(f"🔍 Testing token: {token}")
            
            if invite_data:
                print("✅ Token found!")
                print(f"   ID: {invite_data[0]}")
                print(f"   Expires: {invite_data[1]}")
                print(f"   Uses: {invite_data[3]}/{invite_data[2]}")
                print(f"   Active: {invite_data[4]}")
                
                # Check validation conditions
                if invite_data[1] and datetime.utcnow() > invite_data[1]:
                    print("❌ VALIDATION FAILED: Invitation has expired")
                elif invite_data[3] >= invite_data[2]:
                    print("❌ VALIDATION FAILED: Invitation fully used")
                else:
                    print("✅ VALIDATION PASSED: Invitation is valid!")
            else:
                print("❌ Token not found or inactive")
                
    except Exception as e:
        print(f"❌ Error testing validation: {e}")

if __name__ == "__main__":
    print("🔍 Admin Invite Token Information")
    print("=" * 80)
    
    show_current_invites()
    
    # Test with the actual token if user provides one
    import sys
    if len(sys.argv) > 1:
        test_token = sys.argv[1]
        print(f"\n🔍 Testing provided token: {test_token}")
        test_specific_token_validation(test_token)
    
    print("\n" + "=" * 80)
    print("💡 To test a specific token, run: python show_admin_invite.py YOUR_TOKEN_HERE")