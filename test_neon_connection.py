#!/usr/bin/env python3
"""
Test script to verify Neon database connection
"""

import os
import sys
from urllib.parse import urlparse
from dotenv import load_dotenv
import psycopg2
from psycopg2 import sql
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

def test_direct_connection():
    """Test direct psycopg2 connection to Neon"""
    print("\n" + "="*60)
    print("Testing Direct Connection to Neon Database")
    print("="*60)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        return False
    
    # Parse the URL to check it's Neon
    if 'neon.tech' not in database_url:
        print("⚠️  WARNING: DATABASE_URL does not appear to be a Neon database")
        print(f"   Current URL domain: {urlparse(database_url).hostname}")
    else:
        print("✅ Neon database URL detected")
    
    try:
        # Connect using psycopg2
        print("\n🔄 Attempting psycopg2 connection...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"✅ Connected successfully!")
        print(f"   PostgreSQL version: {version}")
        
        # Get database info
        cursor.execute("SELECT current_database(), current_user, inet_server_addr();")
        db_info = cursor.fetchone()
        print(f"   Database: {db_info[0]}")
        print(f"   User: {db_info[1]}")
        print(f"   Server: {db_info[2] if db_info[2] else 'N/A (pooled connection)'}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Direct connection failed: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test SQLAlchemy connection to Neon"""
    print("\n" + "="*60)
    print("Testing SQLAlchemy Connection")
    print("="*60)
    
    try:
        # Import config to use the same settings as the app
        from config import Config
        
        print(f"🔄 Creating SQLAlchemy engine...")
        print(f"   Database URI configured: {'neon.tech' in Config.SQLALCHEMY_DATABASE_URI}")
        
        # Create engine with app's configuration
        engine = create_engine(
            Config.SQLALCHEMY_DATABASE_URI,
            **Config.SQLALCHEMY_ENGINE_OPTIONS
        )
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print(f"✅ SQLAlchemy connection successful!")
            
            # Get table count
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """))
            table_count = result.scalar()
            print(f"   Tables in public schema: {table_count}")
            
            # List tables if any exist
            if table_count > 0:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """))
                tables = [row[0] for row in result]
                print(f"   Existing tables: {', '.join(tables[:10])}")
                if len(tables) > 10:
                    print(f"   ... and {len(tables) - 10} more")
        
        engine.dispose()
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function"""
    print("\n" + "🚀 "*20)
    print("NEON DATABASE CONNECTION TEST")
    print("🚀 "*20)
    
    # Show current database URL (masked)
    database_url = os.environ.get('DATABASE_URL', '')
    if database_url:
        parsed = urlparse(database_url)
        masked_url = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}/{parsed.path.lstrip('/')}"
        print(f"\n📍 Database URL: {masked_url}")
    
    # Run tests
    direct_ok = test_direct_connection()
    sqlalchemy_ok = test_sqlalchemy_connection()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Direct Connection:     {'✅ PASSED' if direct_ok else '❌ FAILED'}")
    print(f"SQLAlchemy Connection: {'✅ PASSED' if sqlalchemy_ok else '❌ FAILED'}")
    
    if direct_ok and sqlalchemy_ok:
        print("\n🎉 All tests passed! Your Neon database is properly configured.")
        print("\nNext steps:")
        print("1. Run 'python init_db.py' to initialize the database schema")
        print("2. If you have data to migrate, run the migration script")
        return 0
    else:
        print("\n⚠️  Some tests failed. Please check the error messages above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())