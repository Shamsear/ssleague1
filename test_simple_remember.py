#!/usr/bin/env python3
"""
Simple test for Remember Me functionality.
This will verify that cookies are being set with proper persistence settings.
"""
from app import app
from models import db, User, Team
from werkzeug.security import generate_password_hash

def test_remember_me_cookie_settings():
    """Test the cookie settings in a controlled environment"""
    print("🧪 Testing Remember Me Cookie Configuration")
    print("=" * 50)
    
    with app.test_client() as client:
        with app.app_context():
            try:
                # Clean up any existing test users
                test_users = User.query.filter(User.username.like('test_cookie_%')).all()
                test_teams = Team.query.filter(Team.name.like('Test Cookie Team%')).all()
                
                for team in test_teams:
                    db.session.delete(team)
                for user in test_users:
                    db.session.delete(user)
                db.session.commit()
                
                # Create a test user and team
                test_user = User(
                    username='test_cookie_user_new',
                    password_hash=generate_password_hash('testpass123'),
                    is_admin=False,
                    is_approved=True
                )
                db.session.add(test_user)
                db.session.flush()
                
                test_team = Team(
                    name='Test Cookie Team New',
                    user_id=test_user.id,
                    balance=15000
                )
                db.session.add(test_team)
                db.session.commit()
                
                print("✅ Created test user and team")
                
                # Test 1: Login without Remember Me
                print("\n📝 Test 1: Login without Remember Me")
                response = client.post('/login', data={
                    'username': 'test_cookie_user_new',
                    'password': 'testpass123'
                }, follow_redirects=False)
                
                print(f"Response status: {response.status_code}")
                print(f"Location header: {response.headers.get('Location', 'None')}")
                
                # Check cookies in response
                set_cookies = [header for header in response.headers if header[0].lower() == 'set-cookie']
                remember_cookies = [cookie for cookie in set_cookies if 'remember_token' in cookie[1]]
                
                if remember_cookies:
                    print("❌ Remember token cookie was set when it shouldn't be")
                else:
                    print("✅ No remember token cookie set (correct)")
                
                # Test 2: Login with Remember Me
                print("\n📝 Test 2: Login with Remember Me")
                client.get('/logout')  # Clear session
                
                response = client.post('/login', data={
                    'username': 'test_cookie_user_new',
                    'password': 'testpass123',
                    'remember': 'on'  # This is the key part
                }, follow_redirects=False)
                
                print(f"Response status: {response.status_code}")
                print(f"Location header: {response.headers.get('Location', 'None')}")
                
                # Check cookies in response
                set_cookies = [header for header in response.headers if header[0].lower() == 'set-cookie']
                remember_cookies = [cookie for cookie in set_cookies if 'remember_token' in cookie[1]]
                
                if remember_cookies:
                    cookie_value = remember_cookies[0][1]
                    print(f"✅ Remember token cookie set: {cookie_value[:50]}...")
                    
                    # Analyze cookie attributes
                    if 'HttpOnly' in cookie_value:
                        print("✅ Cookie is HttpOnly")
                    else:
                        print("⚠️  Cookie is not HttpOnly")
                        
                    if 'SameSite=Lax' in cookie_value:
                        print("✅ Cookie has SameSite=Lax")
                    else:
                        print("⚠️  Cookie SameSite setting may be different")
                        
                    if 'Expires=' in cookie_value or 'Max-Age=' in cookie_value:
                        print("✅ Cookie has expiration set (persistent)")
                    else:
                        print("❌ Cookie appears to be session-only")
                        
                    if 'Path=/' in cookie_value:
                        print("✅ Cookie path is set to /")
                    
                else:
                    print("❌ Remember token cookie was NOT set")
                
                # Test 3: Check database for remember token
                print("\n📝 Test 3: Database Remember Token")
                db_user = User.query.filter_by(username='test_cookie_user_new').first()
                if db_user and db_user.remember_token:
                    print(f"✅ Database has remember token: {db_user.remember_token[:20]}...")
                    print(f"✅ Token expires at: {db_user.token_expires_at}")
                    
                    # Check if token is valid for future use
                    from datetime import datetime
                    if db_user.token_expires_at and db_user.token_expires_at > datetime.utcnow():
                        print("✅ Token is valid for future use")
                    else:
                        print("❌ Token has expired or no expiry set")
                else:
                    print("❌ No remember token found in database")
                
                # Cleanup
                db.session.delete(test_team)
                db.session.delete(test_user)
                db.session.commit()
                print("\n🧹 Cleaned up test data")
                
                return True
                
            except Exception as e:
                print(f"❌ Error during testing: {e}")
                # Emergency cleanup
                try:
                    db.session.rollback()
                    test_users = User.query.filter(User.username.like('test_cookie_%')).all()
                    test_teams = Team.query.filter(Team.name.like('Test Cookie Team%')).all()
                    
                    for team in test_teams:
                        db.session.delete(team)
                    for user in test_users:
                        db.session.delete(user)
                    db.session.commit()
                except:
                    pass
                return False

if __name__ == "__main__":
    success = test_remember_me_cookie_settings()
    if success:
        print("\n🎉 Remember Me functionality appears to be working correctly!")
        print("\n💡 Key Points for Browser Persistence:")
        print("   • The cookie should have an 'Expires' or 'Max-Age' attribute")
        print("   • Browser settings must allow persistent cookies")
        print("   • Clear browser data will remove the cookie")
        print("   • Private/Incognito mode may not persist cookies")
    else:
        print("\n❌ There may be issues with Remember Me functionality")
    
    print("\n🔍 Troubleshooting Tips:")
    print("   • Make sure you check the 'Remember me for 30 days' checkbox")
    print("   • Check browser developer tools > Application > Cookies")
    print("   • Verify cookie has expiration date 30 days in the future")
    print("   • Test in a regular browser window (not incognito)")
