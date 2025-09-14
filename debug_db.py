#!/usr/bin/env python3
"""
Debug script for database connection issues during deployment
"""
import os
import sys

def debug_database_config():
    """Debug database configuration"""
    print("Database Configuration Debug")
    print("=" * 40)
    
    # Print environment info
    print(f"Python version: {sys.version}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check for DATABASE_URL
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        print(f"DATABASE_URL found: {database_url[:50]}...")
        
        # Check for problematic schema parameter
        if 'schema=' in database_url:
            print("⚠️  WARNING: DATABASE_URL contains 'schema=' parameter")
            print("This is known to cause issues with psycopg2")
        
        # Check URL format
        if database_url.startswith('postgres://'):
            print("⚠️  WARNING: URL starts with 'postgres://', should be 'postgresql://'")
        elif database_url.startswith('postgresql://'):
            print("✅ URL format looks correct (postgresql://)")
    else:
        print("❌ DATABASE_URL environment variable not found")
    
    print("\nTrying to load config...")
    try:
        from config import Config
        processed_url = Config.SQLALCHEMY_DATABASE_URI
        print(f"✅ Config loaded successfully")
        print(f"Processed URL: {processed_url[:50]}...")
        
        # Check if issues were fixed
        if 'schema=' not in processed_url:
            print("✅ Schema parameter removed (if it existed)")
        if processed_url.startswith('postgresql://'):
            print("✅ URL scheme correct")
            
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        print(f"Error type: {type(e).__name__}")
        return
    
    print("\nTrying to connect to database...")
    try:
        from app import app, db
        with app.app_context():
            # Test database connection
            db.engine.execute('SELECT 1')
            print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        
        # Provide specific guidance based on error
        error_str = str(e).lower()
        if 'schema' in error_str:
            print("\n🔧 SOLUTION: The error mentions 'schema'. This is likely the invalid schema parameter issue.")
            print("   Make sure the config.py fixes are applied correctly.")
        elif 'authentication' in error_str or 'password' in error_str:
            print("\n🔧 SOLUTION: Authentication error. Check if:")
            print("   - DATABASE_URL contains correct credentials")
            print("   - Database user exists and has proper permissions")
        elif 'connection' in error_str or 'host' in error_str:
            print("\n🔧 SOLUTION: Connection error. Check if:")
            print("   - Database server is running")
            print("   - Host and port are correct in DATABASE_URL")
            print("   - Network allows connection to database")

if __name__ == "__main__":
    debug_database_config()
