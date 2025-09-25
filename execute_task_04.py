#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 4 EXECUTOR
====================================
Safely executes Task 4: Create Season 16 & Migrate Existing Data

This script:
✅ Creates Season 16 (SS Super League) as the first season
✅ Migrates all existing data to Season 16
✅ Sets Season 16 as active
✅ Preserves all data relationships and integrity
✅ Can be run multiple times safely
✅ Includes rollback functionality
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from datetime import datetime, date

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def execute_task_04():
    """Execute Task 4: Create Season 16 & Migrate Existing Data"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 4: Create Season 16 & Migrate Existing Data")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Checking if Season 16 already exists...")
        
        # Check if Season 16 already exists
        cursor.execute("SELECT id, name, is_active FROM season WHERE short_name = 'S16' OR name LIKE '%Season 16%'")
        existing_season = cursor.fetchone()
        
        season_16_id = None
        if existing_season:
            season_16_id, season_name, is_active = existing_season
            print(f"   ⚠️  Season 16 already exists: ID {season_16_id}, Name: {season_name}, Active: {is_active}")
            
            response = input("Continue with existing Season 16? (y/N): ").lower().strip()
            if response != 'y':
                print("❌ Task 4 cancelled by user")
                return False
        else:
            print("   ✅ No existing Season 16 found, will create new")
        
        print("\n📋 Step 2: Creating Season 16...")
        
        if not existing_season:
            # Get a super admin user for created_by (first user in system, or create system user)
            cursor.execute('SELECT id FROM "user" ORDER BY id LIMIT 1')
            first_user = cursor.fetchone()
            created_by_id = first_user[0] if first_user else None
            
            # Create Season 16
            cursor.execute("""
                INSERT INTO season (
                    name, short_name, description,
                    is_active, status, registration_open,
                    max_committee_admins, team_limit,
                    season_start_date, season_end_date,
                    created_by, created_at, updated_at
                ) VALUES (
                    'Season 16 - SS Super League',
                    'S16',
                    'The inaugural season of the multi-season system. All existing teams and data have been migrated to this season.',
                    true,
                    'active',
                    false,
                    15,
                    50,
                    '2024-01-01',
                    '2024-12-31',
                    %s,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                ) RETURNING id
            """, (created_by_id,))
            
            season_16_id = cursor.fetchone()[0]
            print(f"   ✅ Created Season 16 with ID: {season_16_id}")
        else:
            print(f"   ⏭️  Using existing Season 16 with ID: {season_16_id}")
        
        print("\n📋 Step 3: Analyzing existing data for migration...")
        
        # Get data counts before migration
        tables_to_migrate = ['team', 'round', 'bid', 'match']
        data_counts = {}
        
        for table_name in tables_to_migrate:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE season_id IS NULL')
            null_count = cursor.fetchone()[0]
            
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE season_id = %s', (season_16_id,))
            season_count = cursor.fetchone()[0]
            
            data_counts[table_name] = {'null': null_count, 'season_16': season_count}
            print(f"   📊 {table_name}: {null_count} records need migration, {season_count} already in Season 16")
        
        total_to_migrate = sum(counts['null'] for counts in data_counts.values())
        total_in_season = sum(counts['season_16'] for counts in data_counts.values())
        
        print(f"   📊 Total records to migrate: {total_to_migrate}")
        print(f"   📊 Total records already in Season 16: {total_in_season}")
        
        if total_to_migrate == 0:
            print("   ✅ No data migration needed")
        else:
            print(f"\n📋 Step 4: Migrating {total_to_migrate} records to Season 16...")
            
            migrated_counts = {}
            for table_name in tables_to_migrate:
                if data_counts[table_name]['null'] > 0:
                    print(f"   Migrating {table_name}...")
                    
                    cursor.execute(f"""
                        UPDATE "{table_name}" 
                        SET season_id = %s 
                        WHERE season_id IS NULL
                    """, (season_16_id,))
                    
                    migrated_count = cursor.rowcount
                    migrated_counts[table_name] = migrated_count
                    print(f"   ✅ Migrated {migrated_count} {table_name} records")
                else:
                    migrated_counts[table_name] = 0
                    print(f"   ⏭️  No {table_name} records to migrate")
            
            total_migrated = sum(migrated_counts.values())
            print(f"   📊 Total records migrated: {total_migrated}")
        
        print("\n📋 Step 5: Ensuring Season 16 is active...")
        
        # Make sure only Season 16 is active
        cursor.execute("UPDATE season SET is_active = false WHERE id != %s", (season_16_id,))
        cursor.execute("UPDATE season SET is_active = true, status = 'active' WHERE id = %s", (season_16_id,))
        
        print("   ✅ Season 16 set as the only active season")
        
        print("\n📋 Step 6: Creating Season 16 helper functions...")
        
        # Function to get current active season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_current_season()
            RETURNS TABLE(
                id INTEGER,
                name VARCHAR(100),
                short_name VARCHAR(20),
                is_active BOOLEAN,
                status VARCHAR(20)
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT s.id, s.name, s.short_name, s.is_active, s.status
                FROM season s
                WHERE s.is_active = true
                ORDER BY s.created_at DESC
                LIMIT 1;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_current_season() function created")
        
        # Function to get Season 16 specifically
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_season_16()
            RETURNS TABLE(
                id INTEGER,
                name VARCHAR(100),
                short_name VARCHAR(20),
                team_count BIGINT,
                round_count BIGINT,
                bid_count BIGINT
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    s.id, 
                    s.name, 
                    s.short_name,
                    (SELECT COUNT(*) FROM team WHERE season_id = s.id) as team_count,
                    (SELECT COUNT(*) FROM round WHERE season_id = s.id) as round_count,
                    (SELECT COUNT(*) FROM bid WHERE season_id = s.id) as bid_count
                FROM season s
                WHERE s.short_name = 'S16'
                LIMIT 1;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_season_16() function created")
        
        print("\n📋 Step 7: Creating migration audit view...")
        
        cursor.execute("""
            CREATE OR REPLACE VIEW season_16_migration_audit AS
            SELECT 
                'Season 16 Migration Summary' as audit_type,
                s.id as season_id,
                s.name as season_name,
                s.short_name,
                s.is_active,
                s.status,
                (SELECT COUNT(*) FROM team WHERE season_id = s.id) as teams_migrated,
                (SELECT COUNT(*) FROM round WHERE season_id = s.id) as rounds_migrated,
                (SELECT COUNT(*) FROM bid WHERE season_id = s.id) as bids_migrated,
                (SELECT COUNT(*) FROM match WHERE season_id = s.id) as matches_migrated,
                CASE 
                    WHEN EXISTS(SELECT 1 FROM team WHERE season_id IS NULL) THEN 'WARNING: Unmigrated teams exist'
                    WHEN EXISTS(SELECT 1 FROM round WHERE season_id IS NULL) THEN 'WARNING: Unmigrated rounds exist'
                    WHEN EXISTS(SELECT 1 FROM bid WHERE season_id IS NULL) THEN 'WARNING: Unmigrated bids exist'
                    WHEN EXISTS(SELECT 1 FROM match WHERE season_id IS NULL) THEN 'WARNING: Unmigrated matches exist'
                    ELSE 'SUCCESS: All data migrated'
                END as migration_status
            FROM season s
            WHERE s.short_name = 'S16';
        """)
        print("   ✅ season_16_migration_audit view created")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 8: Verification & Final Report...")
        
        # Verify Season 16 exists and is active
        cursor.execute("SELECT * FROM get_current_season()")
        current_season = cursor.fetchone()
        
        if current_season:
            s_id, s_name, s_short, s_active, s_status = current_season
            print(f"   ✅ Current Active Season: {s_name} ({s_short}) - Active: {s_active}, Status: {s_status}")
        else:
            print("   ❌ No active season found!")
            return False
        
        # Get Season 16 detailed stats
        cursor.execute("SELECT * FROM get_season_16()")
        season_16_stats = cursor.fetchone()
        
        if season_16_stats:
            s_id, s_name, s_short, team_count, round_count, bid_count = season_16_stats
            print(f"   📊 Season 16 Stats:")
            print(f"      • Teams: {team_count}")
            print(f"      • Rounds: {round_count}")  
            print(f"      • Bids: {bid_count}")
        else:
            print("   ❌ Could not retrieve Season 16 stats!")
            return False
        
        # Check migration audit
        cursor.execute("SELECT * FROM season_16_migration_audit")
        audit_result = cursor.fetchone()
        
        if audit_result:
            (audit_type, season_id, season_name, short_name, is_active, status,
             teams, rounds, bids, matches, migration_status) = audit_result
            
            print(f"   📋 Migration Audit Results:")
            print(f"      • Season: {season_name} (ID: {season_id})")
            print(f"      • Status: {migration_status}")
            print(f"      • Data Counts: {teams} teams, {rounds} rounds, {bids} bids, {matches} matches")
        
        # Check for any remaining null season_id records
        cursor.execute("""
            SELECT 
                'team' as table_name, COUNT(*) as null_count FROM team WHERE season_id IS NULL
            UNION ALL
            SELECT 
                'round' as table_name, COUNT(*) as null_count FROM round WHERE season_id IS NULL
            UNION ALL
            SELECT 
                'bid' as table_name, COUNT(*) as null_count FROM bid WHERE season_id IS NULL
            UNION ALL
            SELECT 
                'match' as table_name, COUNT(*) as null_count FROM match WHERE season_id IS NULL
        """)
        
        null_records = cursor.fetchall()
        total_null = sum(count for _, count in null_records)
        
        print(f"   📊 Remaining NULL season_id records: {total_null}")
        for table_name, null_count in null_records:
            if null_count > 0:
                print(f"      ⚠️  {table_name}: {null_count} unmigrated records")
        
        if total_null == 0 and current_season and season_16_stats:
            print("\n🎉 TASK 4 COMPLETED SUCCESSFULLY!")
            print("✅ Season 16 (SS Super League) created and activated")
            print("✅ All existing data migrated to Season 16")
            print("✅ Season 16 set as the only active season")
            print("✅ Migration audit functions created")
            print("✅ Data integrity preserved")
            print("✅ System ready for multi-season operations")
            print(f"\n📊 FINAL STATUS:")
            print(f"   • Active Season: {s_name} ({s_short})")
            print(f"   • Teams in Season 16: {team_count}")
            print(f"   • All historical data preserved and accessible")
            
            return True
        else:
            print(f"\n❌ TASK 4 FAILED:")
            print(f"   • Remaining unmigrated records: {total_null}")
            print(f"   • Active season check: {'✅' if current_season else '❌'}")
            print(f"   • Season 16 stats: {'✅' if season_16_stats else '❌'}")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 4: {e}")
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

def rollback_task_04():
    """Rollback Task 4 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 4: Remove Season 16 & Revert Migration")
        print("⚠️  WARNING: This will:")
        print("   • Delete Season 16")
        print("   • Set all migrated data season_id back to NULL")
        print("   • Remove Season 16 helper functions")
        
        response = input("Are you sure you want to rollback Task 4? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Get Season 16 ID first
        cursor.execute("SELECT id FROM season WHERE short_name = 'S16'")
        season_16_result = cursor.fetchone()
        
        if not season_16_result:
            print("   ⚠️  Season 16 not found, nothing to rollback")
            return True
        
        season_16_id = season_16_result[0]
        print(f"   🔍 Found Season 16 with ID: {season_16_id}")
        
        # Revert data migration (set season_id back to NULL)
        tables_to_revert = ['team', 'round', 'bid', 'match']
        for table_name in tables_to_revert:
            cursor.execute(f"""
                UPDATE "{table_name}" 
                SET season_id = NULL 
                WHERE season_id = %s
            """, (season_16_id,))
            
            reverted_count = cursor.rowcount
            print(f"   ✅ Reverted {reverted_count} {table_name} records")
        
        # Drop Season 16 functions
        functions_to_drop = ['get_current_season', 'get_season_16']
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE")
        
        # Drop audit view
        cursor.execute("DROP VIEW IF EXISTS season_16_migration_audit CASCADE")
        
        # Delete Season 16
        cursor.execute("DELETE FROM season WHERE id = %s", (season_16_id,))
        print(f"   ✅ Deleted Season 16")
        
        conn.commit()
        
        print("✅ Task 4 rollback completed")
        print("   • Season 16 deleted")
        print("   • All data reverted to season_id = NULL")
        print("   • Helper functions removed")
        
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 4 rollback: {e}")
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
        success = rollback_task_04()
    else:
        success = execute_task_04()
    
    sys.exit(0 if success else 1)