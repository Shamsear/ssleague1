#!/usr/bin/env python3

import os
import sys
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

def simulate_flask_validation(invite_token):
    """Simulate the exact Flask app validation logic"""
    print(f"🔍 Simulating Flask validation for fully used invite")
    print("=" * 70)
    
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # This is the exact query from your app.py
        with engine.connect() as conn:
            print("✅ Connected to database")
            
            invite_result = conn.execute(text("""
                SELECT id, expires_at, max_uses, current_uses, is_active, description
                FROM admin_invite 
                WHERE invite_token = :token AND is_active = true
            """), {'token': invite_token})
            
            invite_data = invite_result.fetchone()
            print(f"✅ Query executed, found data: {invite_data is not None}")
            
            if invite_data:
                print(f"📊 Invite data:")
                print(f"   ID: {invite_data[0]}")
                print(f"   Expires at: {invite_data[1]}")
                print(f"   Max uses: {invite_data[2]}")
                print(f"   Current uses: {invite_data[3]}")
                print(f"   Is active: {invite_data[4]}")
                print(f"   Description: {invite_data[5]}")
                
                # Check if invite is still valid (exact logic from app.py)
                print(f"\n🔍 Running validation checks...")
                
                # Check 1: Expiration
                if invite_data[1] and datetime.utcnow() > invite_data[1]:  # expired
                    print("❌ RESULT: Would flash 'This invitation link has expired.'")
                    return "expired"
                else:
                    print("✅ Expiration check passed")
                
                # Check 2: Usage limit
                if invite_data[3] >= invite_data[2]:  # current_uses >= max_uses
                    print("❌ RESULT: Would flash 'This invitation link has been fully used.'")
                    return "fully_used"
                else:
                    print("✅ Usage limit check passed")
                
                print("✅ RESULT: Would set is_admin_invite = True (invite is valid)")
                return "valid"
            else:
                print("❌ RESULT: Would flash 'Invalid invitation link.'")
                return "invalid"
                
    except Exception as e:
        print(f"❌ EXCEPTION: {e}")
        print("❌ RESULT: Would flash 'Error validating invitation.'")
        return "error"

def test_different_scenarios():
    """Test different invite scenarios"""
    token = "nYuIX7bjdugrc7ZUzaVJyyT2uVIcEA6l"
    
    print("🧪 TESTING DIFFERENT INVITE SCENARIOS")
    print("=" * 70)
    
    # Test 1: Current fully used invite
    print("🔍 Test 1: Current fully used invite")
    result = simulate_flask_validation(token)
    print(f"Result: {result}")
    
    print(f"\n" + "=" * 70)
    
    # Test 2: Invalid token
    print("🔍 Test 2: Invalid/non-existent token")
    result = simulate_flask_validation("invalid_token_123")
    print(f"Result: {result}")
    
    print(f"\n" + "=" * 70)
    
    # Test 3: Check current invite status directly
    print("🔍 Test 3: Direct database check")
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    with engine.connect() as conn:
        invite_result = conn.execute(text("""
            SELECT invite_token, current_uses, max_uses, is_active, expires_at
            FROM admin_invite 
            WHERE invite_token = :token
        """), {'token': token})
        
        invite = invite_result.fetchone()
        if invite:
            print(f"   Token: {invite[0][:10]}...")
            print(f"   Uses: {invite[1]}/{invite[2]}")
            print(f"   Active: {invite[3]}")
            print(f"   Expires: {invite[4]}")
            
            if invite[1] >= invite[2]:
                print("   ✅ This should show: 'This invitation link has been fully used.'")
            else:
                print("   ✅ This should show the registration form")
        else:
            print("   ❌ Invite not found")

if __name__ == "__main__":
    test_different_scenarios()
    
    print(f"\n" + "=" * 70)
    print("💡 CONCLUSION:")
    print("If your Flask app is showing 'Error validating invitation' instead of")
    print("'This invitation link has been fully used', then there might be:")
    print("1. An exception occurring during validation (check Flask logs)")
    print("2. A database connection issue in the Flask app")
    print("3. A difference in how the Flask app handles the database connection")
    print("\n💡 Try accessing the invite URL and check the Flask console output for errors.")