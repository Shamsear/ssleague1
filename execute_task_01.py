#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 1 EXECUTOR
====================================
Safely executes Task 1: Create Season and Admin Invite Tables

This script:
✅ Only adds NEW tables (season, admin_invite)
✅ Does NOT modify existing data
✅ Can be run multiple times safely
✅ Includes rollback functionality if needed
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def execute_task_01():
    """Execute Task 1: Create Season and Admin Invite Tables"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 1: Create Season and Admin Invite Tables")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Check if tables already exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('season', 'admin_invite')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        if existing_tables:
            print(f"⚠️  Found existing tables: {existing_tables}")
            response = input("Tables already exist. Continue anyway? (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Task 1 cancelled by user")
                return False
        
        print("\n📋 Step 1: Creating season table...")
        
        # Create season table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS season (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                short_name VARCHAR(20) NOT NULL,
                description TEXT,
                
                -- Season Status
                is_active BOOLEAN DEFAULT FALSE,
                status VARCHAR(20) DEFAULT 'upcoming',
                registration_open BOOLEAN DEFAULT FALSE,
                
                -- Season Configuration
                max_committee_admins INTEGER DEFAULT 15,
                team_limit INTEGER,
                registration_deadline DATE,
                season_start_date DATE,
                season_end_date DATE,
                
                -- Timestamps
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                
                -- Created by super admin
                created_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                
                -- Constraints
                CONSTRAINT valid_season_dates CHECK (
                    season_end_date IS NULL OR season_start_date IS NULL OR season_end_date >= season_start_date
                ),
                CONSTRAINT valid_registration_deadline CHECK (
                    registration_deadline IS NULL OR season_start_date IS NULL OR registration_deadline <= season_start_date
                )
            )
        """)
        print("   ✅ Season table created successfully")
        
        print("\n📋 Step 2: Creating admin_invite table...")
        
        # Create admin_invite table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_invite (
                id SERIAL PRIMARY KEY,
                invite_token VARCHAR(100) UNIQUE NOT NULL,
                
                -- Invite Configuration  
                expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
                max_uses INTEGER DEFAULT 1,
                current_uses INTEGER DEFAULT 0,
                
                -- Tracking
                created_by INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
                used_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
                is_active BOOLEAN DEFAULT TRUE,
                
                -- Metadata
                description TEXT,
                
                -- Timestamps
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP WITHOUT TIME ZONE,
                
                -- Constraints
                CONSTRAINT valid_expiry CHECK (expires_at > created_at),
                CONSTRAINT valid_uses CHECK (max_uses > 0 AND current_uses >= 0 AND current_uses <= max_uses)
            )
        """)
        print("   ✅ Admin invite table created successfully")
        
        print("\n📋 Step 3: Creating indexes...")
        
        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_season_is_active ON season(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_season_status ON season(status)",
            "CREATE INDEX IF NOT EXISTS idx_season_created_at ON season(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_admin_invite_token ON admin_invite(invite_token)",
            "CREATE INDEX IF NOT EXISTS idx_admin_invite_active ON admin_invite(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_admin_invite_expires ON admin_invite(expires_at)",
            "CREATE INDEX IF NOT EXISTS idx_admin_invite_created_by ON admin_invite(created_by)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print(f"   ✅ Created {len(indexes)} indexes successfully")
        
        print("\n📋 Step 4: Creating triggers...")
        
        # Create update trigger function
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_season_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql'
        """)
        
        # Create trigger
        cursor.execute("DROP TRIGGER IF EXISTS update_season_updated_at_trigger ON season")
        cursor.execute("""
            CREATE TRIGGER update_season_updated_at_trigger
                BEFORE UPDATE ON season
                FOR EACH ROW EXECUTE FUNCTION update_season_updated_at()
        """)
        
        print("   ✅ Triggers created successfully")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 5: Verification...")
        
        # Verify tables were created
        cursor.execute("""
            SELECT 
                table_name,
                CASE 
                    WHEN table_name = 'season' THEN 'Season management table'
                    WHEN table_name = 'admin_invite' THEN 'Admin invite system table'
                    ELSE table_name
                END as description
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
              AND table_name IN ('season', 'admin_invite')
            ORDER BY table_name
        """)
        
        verification_results = cursor.fetchall()
        
        print("   📊 Verification Results:")
        for table_name, description in verification_results:
            print(f"      ✅ {table_name}: {description}")
        
        if len(verification_results) == 2:
            print("\n🎉 TASK 1 COMPLETED SUCCESSFULLY!")
            print("✅ Created season table for multi-season management")
            print("✅ Created admin_invite table for committee admin system")
            print("✅ Added proper indexes and constraints")
            print("✅ Added automatic timestamp triggers")
            print("✅ NO existing data was modified")
            
            return True
        else:
            print(f"\n❌ TASK 1 FAILED: Expected 2 tables, found {len(verification_results)}")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 1: {e}")
        if conn:
            conn.rollback()
            print("🔄 Database changes rolled back")
        
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def rollback_task_01():
    """Rollback Task 1 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 1: Remove Season and Admin Invite Tables")
        print("⚠️  WARNING: This will remove the season and admin_invite tables!")
        
        response = input("Are you sure you want to rollback Task 1? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Drop tables in reverse order
        cursor.execute("DROP TABLE IF EXISTS admin_invite CASCADE")
        cursor.execute("DROP TABLE IF EXISTS season CASCADE")
        cursor.execute("DROP FUNCTION IF EXISTS update_season_updated_at() CASCADE")
        
        conn.commit()
        
        print("✅ Task 1 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 1 rollback: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_task_01()
    else:
        success = execute_task_01()
    
    sys.exit(0 if success else 1)