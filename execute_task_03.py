#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 3 EXECUTOR
====================================
Safely executes Task 3: Add Season ID Fields

This script:
✅ Adds season_id columns to core tables
✅ Creates proper foreign key relationships
✅ Does NOT modify existing data (leaves season_id as NULL for now)
✅ Prepares tables for season-specific data
✅ Can be run multiple times safely
✅ Includes rollback functionality
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def get_existing_tables(cursor):
    """Get list of existing tables in the database"""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """)
    return [row[0] for row in cursor.fetchall()]

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
          AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def execute_task_03():
    """Execute Task 3: Add Season ID Fields"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 3: Add Season ID Fields")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Get existing tables
        existing_tables = get_existing_tables(cursor)
        print(f"📊 Found {len(existing_tables)} tables in database")
        
        # Define tables that need season_id
        tables_needing_season_id = [
            ('team', 'Teams should be season-specific'),
            ('round', 'Rounds belong to specific seasons'),
            ('bid', 'Bids are made in specific seasons'),
            ('match', 'Matches happen in specific seasons'),
            ('teamstat', 'Team stats are season-specific'),
        ]
        
        # Filter to only tables that actually exist
        tables_to_modify = []
        for table_name, description in tables_needing_season_id:
            if table_name in existing_tables:
                tables_to_modify.append((table_name, description))
            else:
                print(f"⚠️  Table '{table_name}' not found, skipping")
        
        print(f"\n📋 Tables to modify: {len(tables_to_modify)}")
        for table_name, description in tables_to_modify:
            print(f"   • {table_name}: {description}")
        
        # Check for existing season_id columns
        existing_season_columns = []
        for table_name, _ in tables_to_modify:
            if check_column_exists(cursor, table_name, 'season_id'):
                existing_season_columns.append(table_name)
        
        if existing_season_columns:
            print(f"\n⚠️  Found existing season_id columns in: {existing_season_columns}")
            response = input("Continue with Task 3 anyway? (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Task 3 cancelled by user")
                return False
        
        print("\n📋 Step 1: Adding season_id columns...")
        
        added_columns = 0
        for table_name, description in tables_to_modify:
            if not check_column_exists(cursor, table_name, 'season_id'):
                print(f"   Adding season_id to {table_name}...")
                
                # Add season_id column (nullable for now to preserve existing data)
                cursor.execute(f"""
                    ALTER TABLE "{table_name}" 
                    ADD COLUMN season_id INTEGER 
                    REFERENCES season(id) ON DELETE RESTRICT
                """)
                
                added_columns += 1
                print(f"   ✅ Added season_id column to {table_name}")
            else:
                print(f"   ⏭️  season_id already exists in {table_name}, skipping")
        
        print(f"   📊 Added season_id to {added_columns} tables")
        
        print("\n📋 Step 2: Creating indexes for season_id columns...")
        
        indexes_created = 0
        for table_name, _ in tables_to_modify:
            if check_column_exists(cursor, table_name, 'season_id'):
                index_name = f"idx_{table_name}_season_id"
                
                cursor.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON "{table_name}"(season_id)
                """)
                
                indexes_created += 1
                print(f"   ✅ Created index {index_name}")
        
        print(f"   📊 Created {indexes_created} season_id indexes")
        
        print("\n📋 Step 3: Creating season-aware helper functions...")
        
        # Function to get teams for a specific season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_teams_for_season(season_id_param INTEGER)
            RETURNS TABLE(
                id INTEGER,
                name VARCHAR(50),
                created_at TIMESTAMP,
                captain_id INTEGER
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT t.id, t.name, t.created_at, t.captain_id
                FROM team t
                WHERE t.season_id = season_id_param OR (season_id_param IS NULL AND t.season_id IS NULL)
                ORDER BY t.created_at DESC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_teams_for_season() function created")
        
        # Function to get rounds for a specific season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_rounds_for_season(season_id_param INTEGER)
            RETURNS TABLE(
                id INTEGER,
                round_number INTEGER,
                created_at TIMESTAMP,
                is_active BOOLEAN
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT r.id, r.round_number, r.created_at, r.is_active
                FROM round r
                WHERE r.season_id = season_id_param OR (season_id_param IS NULL AND r.season_id IS NULL)
                ORDER BY r.round_number DESC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_rounds_for_season() function created")
        
        # Function to get bids for a specific season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_bids_for_season(season_id_param INTEGER)
            RETURNS TABLE(
                id INTEGER,
                team_id INTEGER,
                round_id INTEGER,
                amount INTEGER,
                created_at TIMESTAMP
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT b.id, b.team_id, b.round_id, b.amount, b.created_at
                FROM bid b
                WHERE b.season_id = season_id_param OR (season_id_param IS NULL AND b.season_id IS NULL)
                ORDER BY b.created_at DESC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_bids_for_season() function created")
        
        # Function to check if team belongs to season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION team_belongs_to_season(team_id_param INTEGER, season_id_param INTEGER)
            RETURNS BOOLEAN AS $$
            BEGIN
                RETURN EXISTS(
                    SELECT 1 FROM team 
                    WHERE id = team_id_param 
                      AND (season_id = season_id_param OR (season_id_param IS NULL AND season_id IS NULL))
                );
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ team_belongs_to_season() function created")
        
        print("\n📋 Step 4: Creating season statistics view...")
        
        cursor.execute("""
            CREATE OR REPLACE VIEW season_data_stats AS
            WITH season_counts AS (
                SELECT 
                    'team' as table_name,
                    season_id,
                    COUNT(*) as record_count
                FROM team
                GROUP BY season_id
                
                UNION ALL
                
                SELECT 
                    'round' as table_name,
                    season_id,
                    COUNT(*) as record_count
                FROM round
                GROUP BY season_id
                
                UNION ALL
                
                SELECT 
                    'bid' as table_name,
                    season_id,
                    COUNT(*) as record_count
                FROM bid
                GROUP BY season_id
            )
            SELECT 
                COALESCE(s.name, 'Legacy Data') as season_name,
                sc.table_name,
                sc.record_count,
                CASE 
                    WHEN sc.season_id IS NULL THEN 'Pre-season data (needs migration)'
                    ELSE 'Season-specific data'
                END as data_status
            FROM season_counts sc
            LEFT JOIN season s ON sc.season_id = s.id
            ORDER BY sc.season_id NULLS FIRST, sc.table_name;
        """)
        print("   ✅ season_data_stats view created")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 5: Verification...")
        
        # Verify season_id columns were added
        season_columns_added = []
        for table_name, _ in tables_to_modify:
            if check_column_exists(cursor, table_name, 'season_id'):
                season_columns_added.append(table_name)
        
        print(f"   📊 Season ID columns verified: {len(season_columns_added)}/{len(tables_to_modify)}")
        for table_name in season_columns_added:
            print(f"      ✅ {table_name}.season_id")
        
        # Verify functions exist
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN (
                  'get_teams_for_season', 'get_rounds_for_season', 
                  'get_bids_for_season', 'team_belongs_to_season'
              )
            ORDER BY routine_name
        """)
        
        functions = [row[0] for row in cursor.fetchall()]
        expected_functions = [
            'get_bids_for_season', 'get_rounds_for_season', 
            'get_teams_for_season', 'team_belongs_to_season'
        ]
        
        print(f"   📊 Season helper functions: {len(functions)}/{len(expected_functions)}")
        for func in functions:
            print(f"      ✅ {func}()")
        
        # Show current data distribution
        cursor.execute("SELECT * FROM season_data_stats")
        data_stats = cursor.fetchall()
        
        print("   📊 Current Data Distribution:")
        if data_stats:
            for season_name, table_name, record_count, data_status in data_stats:
                print(f"      {season_name} - {table_name}: {record_count} records ({data_status})")
        else:
            print("      No data found in season-aware tables")
        
        if len(season_columns_added) == len(tables_to_modify) and len(functions) == len(expected_functions):
            print("\n🎉 TASK 3 COMPLETED SUCCESSFULLY!")
            print("✅ Added season_id columns to all core tables")
            print("✅ Created foreign key relationships to season table")
            print("✅ Added database indexes for optimal performance")
            print("✅ Created season-aware helper functions")
            print("✅ Created season data statistics view")
            print("✅ Existing data preserved (season_id = NULL for now)")
            print("\n📝 NOTE: Existing data has season_id = NULL")
            print("   Next step will migrate this data to Season 16")
            
            return True
        else:
            print(f"\n❌ TASK 3 FAILED: Missing columns or functions")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 3: {e}")
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

def rollback_task_03():
    """Rollback Task 3 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 3: Remove Season ID Fields")
        print("⚠️  WARNING: This will remove season_id columns from tables!")
        
        response = input("Are you sure you want to rollback Task 3? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Tables that had season_id added
        tables_to_revert = ['team', 'round', 'bid', 'match', 'teamstat']
        
        # Drop functions
        functions_to_drop = [
            'get_teams_for_season', 'get_rounds_for_season', 
            'get_bids_for_season', 'team_belongs_to_season'
        ]
        
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER) CASCADE")
        
        # Drop view
        cursor.execute("DROP VIEW IF EXISTS season_data_stats CASCADE")
        
        # Remove season_id columns
        for table_name in tables_to_revert:
            # Check if table and column exist before dropping
            if check_column_exists(cursor, table_name, 'season_id'):
                cursor.execute(f'ALTER TABLE "{table_name}" DROP COLUMN season_id CASCADE')
                print(f"   ✅ Removed season_id from {table_name}")
        
        conn.commit()
        
        print("✅ Task 3 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 3 rollback: {e}")
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
        success = rollback_task_03()
    else:
        success = execute_task_03()
    
    sys.exit(0 if success else 1)