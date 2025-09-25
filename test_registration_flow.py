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

def test_invitation_validation_step_by_step(invite_token):
    """Test each step of the invitation validation process"""
    print(f"🔍 Testing invitation validation for token: {invite_token}")
    print("=" * 70)
    
    try:
        database_url = get_database_url()
        print(f"✅ Database URL loaded: {database_url[:50]}...")
        
        engine = create_engine(database_url)
        print("✅ Database engine created")
        
        with engine.connect() as conn:
            print("✅ Database connection established")
            
            # Step 1: Test the exact query from the app
            print("\n🔍 Step 1: Testing invite lookup query...")
            try:
                invite_result = conn.execute(text("""
                    SELECT id, expires_at, max_uses, current_uses, is_active, description
                    FROM admin_invite 
                    WHERE invite_token = :token AND is_active = true
                """), {'token': invite_token})
                
                invite_data = invite_result.fetchone()
                print("✅ Query executed successfully")
                
                if invite_data:
                    print(f"✅ Invite found: ID={invite_data[0]}")
                    print(f"   Expires: {invite_data[1]}")
                    print(f"   Max uses: {invite_data[2]}")
                    print(f"   Current uses: {invite_data[3]}")
                    print(f"   Is active: {invite_data[4]}")
                    print(f"   Description: {invite_data[5]}")
                else:
                    print("❌ No invite found with this token")
                    return False
                    
            except Exception as e:
                print(f"❌ Error in invite lookup: {e}")
                return False
            
            # Step 2: Test expiration check
            print(f"\n🔍 Step 2: Testing expiration check...")
            current_time = datetime.utcnow()
            expires_at = invite_data[1]
            
            print(f"   Current time: {current_time}")
            print(f"   Expires at: {expires_at}")
            
            if expires_at and current_time > expires_at:
                print("❌ VALIDATION FAILED: Invitation has expired")
                return False
            else:
                print("✅ Expiration check passed")
            
            # Step 3: Test usage limit check
            print(f"\n🔍 Step 3: Testing usage limit check...")
            current_uses = invite_data[3]
            max_uses = invite_data[2]
            
            print(f"   Current uses: {current_uses}")
            print(f"   Max uses: {max_uses}")
            
            if current_uses >= max_uses:
                print("❌ VALIDATION FAILED: Invitation fully used")
                return False
            else:
                print("✅ Usage limit check passed")
            
            # Step 4: Test the complete validation logic
            print(f"\n🔍 Step 4: Complete validation simulation...")
            
            # Simulate the exact logic from app.py
            if invite_data:
                # Check if invite is still valid
                if invite_data[1] and datetime.utcnow() > invite_data[1]:  # expired
                    print("❌ Would show: 'This invitation link has expired.'")
                    return False
                
                if invite_data[3] >= invite_data[2]:  # current_uses >= max_uses
                    print("❌ Would show: 'This invitation link has been fully used.'")
                    return False
                
                print("✅ All validation checks passed!")
                print("✅ is_admin_invite would be set to True")
                return True
            else:
                print("❌ Would show: 'Invalid invitation link.'")
                return False
                
    except Exception as e:
        print(f"❌ Error in validation process: {e}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Error details: {str(e)}")
        return False

def check_flask_app_issues():
    """Check for common Flask app issues that might cause problems"""
    print(f"\n🔍 Checking for potential Flask app issues...")
    print("=" * 70)
    
    # Check if the app imports are working
    try:
        sys.path.append('.')
        from datetime import datetime
        print("✅ datetime import works")
        
        from sqlalchemy import text
        print("✅ sqlalchemy text import works")
        
        # Check if the database models are importable
        try:
            from models import db, User
            print("✅ Models import works")
        except Exception as e:
            print(f"⚠️  Models import issue: {e}")
        
    except Exception as e:
        print(f"❌ Import error: {e}")

def simulate_registration_request(invite_token):
    """Simulate what happens when someone accesses the registration URL"""
    print(f"\n🔍 Simulating registration page request...")
    print("=" * 70)
    
    try:
        # This simulates request.args.get('invite')
        print(f"✅ invite_token from URL: {invite_token}")
        
        if invite_token:
            print("✅ Token found in request")
            
            # Test the database query that would run
            database_url = get_database_url()
            engine = create_engine(database_url)
            
            with engine.connect() as conn:
                print("✅ Database connection in registration route")
                
                invite_result = conn.execute(text("""
                    SELECT id, expires_at, max_uses, current_uses, is_active, description
                    FROM admin_invite 
                    WHERE invite_token = :token AND is_active = true
                """), {'token': invite_token})
                invite_data = invite_result.fetchone()
                
                if invite_data:
                    print("✅ Invite data retrieved successfully")
                    # Check validation conditions
                    if invite_data[1] and datetime.utcnow() > invite_data[1]:
                        print("❌ Would redirect with: 'This invitation link has expired.'")
                    elif invite_data[3] >= invite_data[2]:
                        print("❌ Would redirect with: 'This invitation link has been fully used.'")
                    else:
                        print("✅ Would set is_admin_invite = True")
                        print("✅ Registration form would show for admin invite")
                else:
                    print("❌ Would redirect with: 'Invalid invitation link.'")
        else:
            print("❌ No invite token found")
            
    except Exception as e:
        print(f"❌ Error in registration simulation: {e}")
        print(f"   This is likely where 'Error validating invitation' comes from")
        print(f"   Error type: {type(e).__name__}")
        
        # Check for specific error types
        if "relation" in str(e).lower():
            print("💡 This looks like a table doesn't exist")
        elif "column" in str(e).lower():
            print("💡 This looks like a column doesn't exist")
        elif "connection" in str(e).lower():
            print("💡 This looks like a database connection issue")

if __name__ == "__main__":
    token = "nYuIX7bjdugrc7ZUzaVJyyT2uVIcEA6l"
    
    if len(sys.argv) > 1:
        token = sys.argv[1]
    
    print("🧪 TESTING ADMIN INVITE REGISTRATION FLOW")
    print("=" * 70)
    print(f"Testing with token: {token}")
    print(f"URL: http://127.0.0.1:5000/register?invite={token}")
    
    # Run all tests
    validation_passed = test_invitation_validation_step_by_step(token)
    check_flask_app_issues()
    simulate_registration_request(token)
    
    print("\n" + "=" * 70)
    if validation_passed:
        print("✅ CONCLUSION: Token validation should work!")
        print("💡 If you're still getting 'Error validating invitation', the issue is likely:")
        print("   1. A different database connection in your Flask app")
        print("   2. An import error in the Flask application")
        print("   3. A Flask configuration issue")
        print("   4. The Flask app is using a different database")
    else:
        print("❌ CONCLUSION: Token validation has issues")
    
    print("\n💡 Try accessing this URL in your browser:")
    print(f"   http://127.0.0.1:5000/register?invite={token}")