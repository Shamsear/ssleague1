#!/usr/bin/env python3

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get the database URL from environment"""
    database_url = os.environ.get('DATABASE_URL') or 'postgresql://postgres:password@localhost/auction_db'
    
    # Convert postgres:// to postgresql://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    
    return database_url

def check_admin_invite_table():
    """Check if admin_invite table exists and its structure"""
    try:
        database_url = get_database_url()
        print(f"Connecting to database: {database_url[:50]}...")
        
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if admin_invite table exists
            table_check = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'admin_invite'
                );
            """))
            table_exists = table_check.fetchone()[0]
            
            print(f"✅ Database connection successful!")
            print(f"admin_invite table exists: {table_exists}")
            
            if table_exists:
                # Get table structure
                structure = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable, column_default 
                    FROM information_schema.columns 
                    WHERE table_name = 'admin_invite' 
                    ORDER BY ordinal_position;
                """))
                
                print("\n📋 Table structure:")
                for row in structure:
                    print(f"  - {row[0]} ({row[1]}) - nullable: {row[2]}, default: {row[3]}")
                
                # Check for any existing invites
                invite_count = conn.execute(text("SELECT COUNT(*) FROM admin_invite;"))
                count = invite_count.fetchone()[0]
                print(f"\n📊 Total admin invites in database: {count}")
                
                if count > 0:
                    # Show active invites
                    active_invites = conn.execute(text("""
                        SELECT id, invite_token, expires_at, max_uses, current_uses, is_active, description
                        FROM admin_invite 
                        WHERE is_active = true
                        ORDER BY created_at DESC
                        LIMIT 5;
                    """))
                    
                    print("\n🎫 Active admin invites:")
                    for invite in active_invites:
                        print(f"  - ID: {invite[0]}, Token: {invite[1][:10]}..., Expires: {invite[2]}, Uses: {invite[4]}/{invite[3]}, Active: {invite[5]}")
            else:
                print("\n❌ admin_invite table does not exist!")
                print("You need to run the migration: migrations/001_create_season_tables.sql")
                
                # Check what tables do exist
                existing_tables = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """))
                
                print("\n📋 Existing tables:")
                for table in existing_tables:
                    print(f"  - {table[0]}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    return table_exists

def test_invite_validation(test_token="test123"):
    """Test the invite validation logic with a test token"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Try the same query that's failing in the app
            invite_result = conn.execute(text("""
                SELECT id, expires_at, max_uses, current_uses, is_active, description
                FROM admin_invite 
                WHERE invite_token = :token AND is_active = true
            """), {'token': test_token})
            
            invite_data = invite_result.fetchone()
            
            print(f"\n🔍 Testing invite validation with token: {test_token}")
            print(f"Result: {invite_data}")
            
            if not invite_data:
                print("❌ No active invite found with this token")
            else:
                print("✅ Invite found and validation query works!")
                
    except Exception as e:
        print(f"❌ Error testing invite validation: {e}")

if __name__ == "__main__":
    print("🔍 Checking admin_invite table and debugging invitation validation...")
    print("=" * 70)
    
    table_exists = check_admin_invite_table()
    
    if table_exists:
        test_invite_validation()
    
    print("\n" + "=" * 70)
    print("✅ Check complete!")