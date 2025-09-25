#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - MIGRATION FIX
==================================
Completes missing migrations that weren't fully applied

This script:
✅ Adds missing season_id column to player table
✅ Renames role column to user_role in user table
✅ Creates team_lineage table if missing
✅ Safe to run multiple times
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def fix_migrations():
    """Fix missing database migrations"""
    conn = None
    cursor = None
    
    try:
        print("🔧 FIXING MISSING MIGRATIONS")
        print("=" * 50)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Checking player table...")
        
        # Check if player table has season_id
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'player' AND column_name = 'season_id'
        """)
        
        if not cursor.fetchone():
            print("   Adding season_id column to player table...")
            
            # Add season_id column
            cursor.execute("""
                ALTER TABLE player 
                ADD COLUMN season_id INTEGER REFERENCES season(id)
            """)
            
            # Update existing players to Season 16
            cursor.execute("""
                UPDATE player 
                SET season_id = (SELECT id FROM season WHERE is_active = true LIMIT 1)
                WHERE season_id IS NULL
            """)
            
            print("   ✅ Added season_id to player table")
        else:
            print("   ✅ Player table already has season_id")
        
        print("\n📋 Step 2: Checking user table...")
        
        # Check if user table has user_role vs role
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'user' AND column_name IN ('role', 'user_role')
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        if 'role' in columns and 'user_role' not in columns:
            print("   Renaming 'role' column to 'user_role'...")
            cursor.execute("""
                ALTER TABLE "user" 
                RENAME COLUMN role TO user_role
            """)
            print("   ✅ Renamed role to user_role")
        elif 'user_role' in columns:
            print("   ✅ User table already has user_role column")
        else:
            print("   Adding user_role column...")
            cursor.execute("""
                ALTER TABLE "user" 
                ADD COLUMN user_role VARCHAR(20) DEFAULT 'team_user'
            """)
            
            # Update admin user to super_admin
            cursor.execute("""
                UPDATE "user" 
                SET user_role = 'super_admin' 
                WHERE is_admin = true
            """)
            print("   ✅ Added user_role column")
        
        print("\n📋 Step 3: Checking team_lineage table...")
        
        # Check if team_lineage table exists
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_name = 'team_lineage'
        """)
        
        if not cursor.fetchone():
            print("   Creating team_lineage table...")
            cursor.execute("""
                CREATE TABLE team_lineage (
                    id SERIAL PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by INTEGER REFERENCES "user"(id),
                    description TEXT
                )
            """)
            
            print("   ✅ Created team_lineage table")
            
            # Create lineages for existing teams
            cursor.execute("""
                INSERT INTO team_lineage (created_by, description)
                SELECT user_id, 'Auto-generated lineage for ' || name
                FROM team
                WHERE team_lineage_id IS NULL
            """)
            
            # Update teams to reference their lineages
            cursor.execute("""
                UPDATE team 
                SET team_lineage_id = (
                    SELECT tl.id 
                    FROM team_lineage tl 
                    WHERE tl.created_by = team.user_id
                    LIMIT 1
                )
                WHERE team_lineage_id IS NULL
            """)
            
            print("   ✅ Created lineages for existing teams")
        else:
            print("   ✅ team_lineage table already exists")
        
        # Commit all changes
        conn.commit()
        
        print("\n🎉 ALL MIGRATIONS FIXED!")
        print("✅ Player table has season_id")
        print("✅ User table has user_role")
        print("✅ team_lineage table exists")
        print("✅ Database is ready for testing")
        
        return True
        
    except Exception as e:
        print(f"\n💥 ERROR fixing migrations: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    fix_migrations()