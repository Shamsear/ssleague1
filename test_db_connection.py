#!/usr/bin/env python3
"""
Simple script to test database connection configuration
"""
import os
from config import Config

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
    
    print("Testing DATABASE_URL parsing...")
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
    print("Database URL parsing test completed!")

if __name__ == "__main__":
    test_database_url()
