#!/usr/bin/env python3
import psycopg2
import os
from urllib.parse import urlparse

def test_database_connection():
    # Test the database URL from environment
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:zyiubE1EA8QHblQG@db.ibgcfbnqqbdqyukhxcuz.supabase.co:5432/postgres?sslmode=require')
    
    print(f"Testing connection to: {database_url}")
    
    try:
        # Parse the URL
        parsed = urlparse(database_url)
        print(f"Host: {parsed.hostname}")
        print(f"Port: {parsed.port}")
        print(f"Database: {parsed.path[1:]}")
        print(f"Username: {parsed.username}")
        
        # Test connection
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Connection successful!")
        print(f"PostgreSQL version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    test_database_connection()
