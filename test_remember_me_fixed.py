#!/usr/bin/env python3
"""
Test script for Remember Me functionality with Supabase database.
This script tests the database structure and Remember Me implementation.
"""
import os
import sys
from datetime import datetime, timedelta
from app import app, db
from models import User, Team
from sqlalchemy import text, inspect
from werkzeug.security import generate_password_hash

def check_database_structure():
    """Check if the User table has the required remember token fields."""
    print("🔍 Checking database structure...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Use SQLAlchemy inspector to check table structure
            inspector = inspect(db.engine)
            columns = inspector.get_columns('user')
            column_names = [col['name'] for col in columns]
            
            print(f"📋 User table columns found: {len(columns)}")
            for col in columns:
                print(f"  - {col['name']} ({col['type']})")
            
            # Check for remember token fields
            has_remember_token = 'remember_token' in column_names
            has_token_expires = 'token_expires_at' in column_names
            
            print(f"\n🔐 Remember Me fields status:")
            print(f"  - remember_token: {'✅ Present' if has_remember_token else '❌ Missing'}")
            print(f"  - token_expires_at: {'✅ Present' if has_token_expires else '❌ Missing'}")
            
            return has_remember_token and has_token_expires
            
        except Exception as e:
            print(f"❌ Error checking database structure: {e}")
            return False

def add_missing_fields():
    """Add missing remember token fields if they don't exist."""
    print("\n🔧 Adding missing remember token fields...")
    print("=" * 50)
    
    with app.app_context():
        try:
            inspector = inspect(db.engine)
            columns = inspector.get_columns('user')
            column_names = [col['name'] for col in columns]
            
            statements = []
            if 'remember_token' not in column_names:
                statements.append('ALTER TABLE "user" ADD COLUMN remember_token VARCHAR(128);')
            if 'token_expires_at' not in column_names:
                statements.append('ALTER TABLE "user" ADD COLUMN token_expires_at TIMESTAMP;')
            
            if statements:
                with db.engine.begin() as connection:
                    for stmt in statements:
                        print(f"🔄 Executing: {stmt}")
                        connection.execute(text(stmt))
                print("✅ Remember token fields added successfully!")
                return True
            else:
                print("ℹ️  Remember token fields already exist.")
                return True
                
        except Exception as e:
            print(f"❌ Error adding remember token fields: {e}")
            return False

def test_user_model_methods():
    """Test the User model's remember token methods."""
    print("\n🧪 Testing User model remember token methods...")
    print("=" * 50)
    
    with app.app_context():
        try:
            # Find or create a test user
            test_user = User.query.filter_by(username='test_remember_user').first()
            if not test_user:
                test_user = User(
                    username='test_remember_user', 
                    password_hash=generate_password_hash('testpass123'),
                    is_admin=False,
                    is_approved=True
                )
                db.session.add(test_user)
                db.session.commit()
                print("👤 Created test user for remember me testing")
            else:
                print("👤 Using existing test user")
            
            # Test token generation
            print("\n🔐 Testing token generation...")
            token = test_user.generate_remember_token(days=30)
            db.session.commit()
            
            print(f"✅ Generated token: {token[:20]}...")
            print(f"✅ Token expires at: {test_user.token_expires_at}")
            
            # Test token retrieval
            print("\n🔍 Testing token retrieval...")
            retrieved_user = User.get_by_remember_token(token)
            
            if retrieved_user and retrieved_user.id == test_user.id:
                print("✅ Token retrieval successful!")
            else:
                print("❌ Token retrieval failed!")
                return False
            
            # Test expired token
            print("\n⏰ Testing expired token...")
            test_user.token_expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            
            expired_user = User.get_by_remember_token(token)
            if expired_user is None:
                print("✅ Expired token correctly rejected!")
            else:
                print("❌ Expired token was not rejected!")
                return False
            
            # Clean up test user
            db.session.delete(test_user)
            db.session.commit()
            print("🧹 Cleaned up test user")
            
            return True
            
        except Exception as e:
            print(f"❌ Error testing user model methods: {e}")
            return False

def test_cookie_setting():
    """Test if cookies are properly set with remember me."""
    print("\n🍪 Testing cookie setting functionality...")
    print("=" * 50)
    
    with app.test_client() as client:
        with app.app_context():
            try:
                # Create test user with team (to avoid dashboard errors)
                test_user = User(
                    username='test_cookie_user', 
                    password_hash=generate_password_hash('testpass123'),
                    is_admin=False,
                    is_approved=True
                )
                db.session.add(test_user)
                db.session.flush()  # Get the user ID
                
                # Create a team for the user to avoid NoneType errors in dashboard
                test_team = Team(
                    name='Test Cookie Team',
                    user_id=test_user.id
                )
                db.session.add(test_team)
                db.session.commit()
                
                print("👤 Created test user and team")
                
                # Login with remember me
                print("🔑 Testing login with remember me...")
                response = client.post('/login', data={
                    'username': 'test_cookie_user',
                    'password': 'testpass123',
                    'remember': 'on'
                })
                
                print(f"Login response code: {response.status_code}")
                
                # Check if the remember_token cookie was set
                cookies = [c for c in client.cookie_jar if c.name == 'remember_token']
                
                if cookies:
                    print(f"✅ Remember token cookie set: {cookies[0].value[:20]}...")
                    print(f"Cookie path: {cookies[0].path}")
                    print(f"Cookie expires: {cookies[0].expires}")
                else:
                    print("❌ Remember token cookie was not set")
                
                # Check the database for the token
                db_user = User.query.filter_by(username='test_cookie_user').first()
                if db_user and db_user.remember_token:
                    print(f"✅ Database has remember token: {db_user.remember_token[:20]}...")
                    print(f"Token expires at: {db_user.token_expires_at}")
                else:
                    print("❌ Database does not have remember token set")
                
                # Clean up
                db.session.delete(test_team)
                db.session.delete(test_user)
                db.session.commit()
                print("🧹 Cleaned up test user and team")
                
                return bool(cookies) and bool(db_user and db_user.remember_token)
                
            except Exception as e:
                print(f"❌ Error testing cookie setting: {e}")
                # Try to clean up in case of error
                try:
                    db.session.rollback()
                    test_users = User.query.filter_by(username='test_cookie_user').all()
                    test_teams = Team.query.filter_by(name='Test Cookie Team').all()
                    for team in test_teams:
                        db.session.delete(team)
                    for user in test_users:
                        db.session.delete(user)
                    db.session.commit()
                except Exception as cleanup_error:
                    print(f"Cleanup error: {cleanup_error}")
                return False

def main():
    """Run all Remember Me functionality tests."""
    print("🚀 Starting Remember Me Functionality Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 4
    
    # Test 1: Check database structure
    if check_database_structure():
        tests_passed += 1
        structure_ok = True
    else:
        structure_ok = False
    
    # Test 2: Add missing fields if needed
    if not structure_ok:
        if add_missing_fields():
            tests_passed += 1
            structure_ok = True
    else:
        tests_passed += 1  # Structure was already OK
    
    # Test 3: Test user model methods (only if structure is OK)
    if structure_ok:
        if test_user_model_methods():
            tests_passed += 1
    
    # Test 4: Test cookie setting functionality
    if structure_ok:
        if test_cookie_setting():
            tests_passed += 1
    
    # Final summary
    print("\n📊 Test Results Summary")
    print("=" * 60)
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("✅ All Remember Me tests PASSED!")
        print("🎉 Your Remember Me functionality is working correctly!")
        return 0
    else:
        print("❌ Some Remember Me tests FAILED")
        print("🔧 Please review the issues above and fix them.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
