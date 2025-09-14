#!/usr/bin/env python3
"""
Enhanced database connection test script for debugging deployment issues.
This helps identify database connectivity problems before and during deployment.
"""
import os
import sys
from config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
import time

def test_database_url():
    """Test various DATABASE_URL formats to ensure proper parsing"""
    
    # Test URLs that might come from Render or other cloud providers
    test_urls = [
        # Standard PostgreSQL URL
        "postgresql://user:password@host:5432/dbname",
        
        # Postgres URL that needs conversion
        "postgres://user:password@host:5432/dbname",
        
        # URL with invalid schema parameter (common Render issue)
        "postgresql://user:password@host:5432/dbname?schema=public",
        
        # URL with schema and other parameters
        "postgresql://user:password@host:5432/dbname?sslmode=require&schema=public&connect_timeout=10",
        
        # URL with only schema parameter
        "postgres://user:password@host:5432/dbname?schema=public",
    ]
    
    print("🧪 Testing DATABASE_URL parsing...")
    print("=" * 50)
    
    for i, test_url in enumerate(test_urls, 1):
        print(f"\nTest {i}: {test_url}")
        
        # Temporarily set DATABASE_URL
        original_url = os.environ.get('DATABASE_URL')
        os.environ['DATABASE_URL'] = test_url
        
        # Reload config
        from importlib import reload
        import config
        reload(config)
        
        parsed_url = config.Config.SQLALCHEMY_DATABASE_URI
        print(f"Result: {parsed_url}")
        
        # Check if schema parameter was removed
        if 'schema=' in parsed_url:
            print("❌ ERROR: 'schema' parameter was not removed!")
        else:
            print("✅ SUCCESS: 'schema' parameter removed (if it existed)")
        
        # Check if postgres:// was converted to postgresql://
        if parsed_url.startswith('postgresql://'):
            print("✅ SUCCESS: URL starts with 'postgresql://'")
        else:
            print("❌ ERROR: URL should start with 'postgresql://'")
        
        # Restore original URL
        if original_url:
            os.environ['DATABASE_URL'] = original_url
        elif 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
    
    print("\n" + "=" * 50)
    print("✅ Database URL parsing test completed!")

def test_database_connection():
    """Test actual database connection with detailed diagnostics."""
    
    print("\n🔌 Testing Database Connection...")
    print("=" * 50)
    
    # Display current configuration
    db_uri = Config.SQLALCHEMY_DATABASE_URI
    print(f"Database URI (first 60 chars): {db_uri[:60]}...")
    print(f"Engine options: {Config.SQLALCHEMY_ENGINE_OPTIONS}")
    
    # Create engine with options
    try:
        engine = create_engine(
            db_uri,
            **Config.SQLALCHEMY_ENGINE_OPTIONS
        )
        print("✅ Engine created successfully")
    except Exception as e:
        print(f"❌ Engine creation failed: {e}")
        return False
    
    # Test connection with retry logic
    max_retries = 3
    for attempt in range(max_retries):
        try:
            print(f"\n🔌 Connection attempt {attempt + 1}/{max_retries}...")
            
            with engine.connect() as conn:
                # Test basic query
                result = conn.execute(text("SELECT 1 as test"))
                test_value = result.fetchone()[0]
                print(f"✅ Basic query successful: SELECT 1 = {test_value}")
                
                # Test current database
                result = conn.execute(text("SELECT current_database()"))
                db_name = result.fetchone()[0]
                print(f"✅ Connected to database: {db_name}")
                
                # Test version
                result = conn.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                print(f"✅ PostgreSQL version: {version[:80]}...")
                
                # Test table creation permissions
                try:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS test_connection_table (
                            id SERIAL PRIMARY KEY,
                            test_data VARCHAR(50)
                        )
                    """))
                    conn.execute(text("DROP TABLE IF EXISTS test_connection_table"))
                    conn.commit()
                    print("✅ Table creation/deletion permissions OK")
                except Exception as e:
                    print(f"⚠️  Table creation test failed: {e}")
                
            print("✅ Database connection test PASSED")
            return True
            
        except SQLAlchemyError as e:
            print(f"❌ SQLAlchemy error on attempt {attempt + 1}: {e}")
            if "Network is unreachable" in str(e):
                print("🌐 Network connectivity issue detected")
            elif "authentication failed" in str(e):
                print("🔐 Authentication issue detected")
            elif "does not exist" in str(e):
                print("🗄️  Database existence issue detected")
            elif "SSL" in str(e) or "ssl" in str(e):
                print("🔒 SSL configuration issue detected")
        except Exception as e:
            print(f"❌ Unexpected error on attempt {attempt + 1}: {e}")
        
        if attempt < max_retries - 1:
            wait_time = 2 ** attempt  # Exponential backoff
            print(f"⏳ Waiting {wait_time}s before retry...")
            time.sleep(wait_time)
    
    print("❌ All database connection attempts failed")
    return False

def test_environment_variables():
    """Test that all required environment variables are present."""
    
    print("\n🌍 Environment Variables Check")
    print("=" * 50)
    
    required_vars = ['SECRET_KEY', 'DATABASE_URL']
    optional_vars = ['VAPID_PRIVATE_KEY', 'VAPID_PUBLIC_KEY', 'VAPID_CLAIMS_SUB']
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(20, len(value))}... (set)")
        else:
            print(f"❌ {var}: Not set")
            missing_required.append(var)
    
    for var in optional_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var}: {'*' * min(20, len(value))}... (set)")
        else:
            print(f"⚠️  {var}: Not set (optional for local dev)")
            missing_optional.append(var)
    
    if missing_required:
        print(f"\n❌ Missing required environment variables: {', '.join(missing_required)}")
        return False
    
    if missing_optional:
        print(f"\n⚠️  Missing optional environment variables: {', '.join(missing_optional)}")
    
    print("✅ Environment variables check passed")
    return True

def main():
    """Run all diagnostic tests."""
    
    print("🚀 Starting Comprehensive Database Diagnostics")
    print("=" * 60)
    
    # Test URL parsing
    test_database_url()
    
    # Test environment variables
    env_ok = test_environment_variables()
    
    # Test database connection (only if env vars are OK)
    db_ok = False
    if env_ok:
        db_ok = test_database_connection()
    else:
        print("\n⚠️  Skipping database connection test due to missing environment variables")
    
    # Final summary
    print("\n📊 Final Summary")
    print("=" * 50)
    
    if env_ok and db_ok:
        print("✅ All tests PASSED - Ready for deployment!")
        return 0
    else:
        print("❌ Some tests FAILED - Review issues above")
        if not env_ok:
            print("   • Check environment variable setup")
        if not db_ok:
            print("   • Check database connectivity and configuration")
        return 1

if __name__ == "__main__":
    sys.exit(main())
