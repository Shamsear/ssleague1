#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 5 EXECUTOR
====================================
Safely executes Task 5: Add Team Lineage Tracking

This script:
✅ Adds team lineage tracking fields to team table
✅ Creates team lineage management functions
✅ Enables tracking team continuity across seasons
✅ Supports team identification without confusion
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

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = %s 
          AND column_name = %s
    """, (table_name, column_name))
    return cursor.fetchone() is not None

def execute_task_05():
    """Execute Task 5: Add Team Lineage Tracking"""
    conn = None
    cursor = None
    
    try:
        print("🚀 EXECUTING TASK 5: Add Team Lineage Tracking")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Analyzing current team table structure...")
        
        # Check existing columns in team table
        cursor.execute("""
            SELECT column_name, data_type, column_default, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'team'
            ORDER BY ordinal_position
        """)
        
        existing_columns = cursor.fetchall()
        print(f"   📊 Current team table has {len(existing_columns)} columns:")
        for col_name, data_type, default, nullable in existing_columns:
            print(f"      • {col_name} ({data_type})")
        
        # Check which lineage columns need to be added
        lineage_columns_needed = []
        lineage_columns = [
            ('team_lineage_id', 'INTEGER', 'Links teams across seasons with same core identity'),
            ('previous_team_id', 'INTEGER', 'Links to the previous season version of this team'),
            ('original_season_id', 'INTEGER', 'The season where this team lineage first started'),
            ('is_continuing_team', 'BOOLEAN', 'Whether this team is continuing from a previous season'),
            ('team_legacy_name', 'VARCHAR(100)', 'Original team name for historical reference')
        ]
        
        for col_name, col_type, description in lineage_columns:
            if not check_column_exists(cursor, 'team', col_name):
                lineage_columns_needed.append((col_name, col_type, description))
            else:
                print(f"   ⚠️  Column {col_name} already exists")
        
        if not lineage_columns_needed:
            print("   ✅ All lineage columns already exist")
        else:
            print(f"   📋 Need to add {len(lineage_columns_needed)} lineage columns")
        
        print("\n📋 Step 2: Adding team lineage columns...")
        
        columns_added = 0
        for col_name, col_type, description in lineage_columns_needed:
            print(f"   Adding {col_name}...")
            
            # Add column with appropriate defaults
            if col_name == 'is_continuing_team':
                cursor.execute(f'ALTER TABLE team ADD COLUMN {col_name} {col_type} DEFAULT false')
            elif col_name == 'team_lineage_id':
                cursor.execute(f'ALTER TABLE team ADD COLUMN {col_name} {col_type}')
            elif col_name == 'previous_team_id':
                cursor.execute(f'ALTER TABLE team ADD COLUMN {col_name} {col_type} REFERENCES team(id) ON DELETE SET NULL')
            elif col_name == 'original_season_id':
                cursor.execute(f'ALTER TABLE team ADD COLUMN {col_name} {col_type} REFERENCES season(id) ON DELETE SET NULL')
            else:
                cursor.execute(f'ALTER TABLE team ADD COLUMN {col_name} {col_type}')
            
            columns_added += 1
            print(f"   ✅ Added {col_name} ({description})")
        
        print(f"   📊 Added {columns_added} lineage columns to team table")
        
        print("\n📋 Step 3: Creating team lineage sequence...")
        
        # Create sequence for team_lineage_id if it doesn't exist
        cursor.execute("CREATE SEQUENCE IF NOT EXISTS team_lineage_seq START 1000")
        print("   ✅ Created team_lineage_seq sequence (starts at 1000)")
        
        print("\n📋 Step 4: Initializing existing teams with lineage data...")
        
        # Initialize existing teams in Season 16 with lineage information
        cursor.execute("""
            UPDATE team 
            SET 
                team_lineage_id = nextval('team_lineage_seq'),
                original_season_id = season_id,
                is_continuing_team = false,
                team_legacy_name = name
            WHERE team_lineage_id IS NULL 
              AND season_id IS NOT NULL
        """)
        
        initialized_count = cursor.rowcount
        print(f"   ✅ Initialized {initialized_count} existing teams with lineage data")
        
        print("\n📋 Step 5: Creating team lineage management functions...")
        
        # Function to create a continuing team for next season
        cursor.execute("""
            CREATE OR REPLACE FUNCTION create_continuing_team(
                previous_team_id_param INTEGER,
                new_season_id_param INTEGER,
                new_team_name_param VARCHAR(50),
                captain_id_param INTEGER
            )
            RETURNS INTEGER AS $$
            DECLARE
                previous_team RECORD;
                new_team_id INTEGER;
            BEGIN
                -- Get previous team information
                SELECT * INTO previous_team 
                FROM team 
                WHERE id = previous_team_id_param;
                
                IF NOT FOUND THEN
                    RAISE EXCEPTION 'Previous team with id % not found', previous_team_id_param;
                END IF;
                
                -- Check if team already exists in the new season
                IF EXISTS(
                    SELECT 1 FROM team 
                    WHERE team_lineage_id = previous_team.team_lineage_id 
                      AND season_id = new_season_id_param
                ) THEN
                    RAISE EXCEPTION 'Team with lineage_id % already exists in season %', 
                        previous_team.team_lineage_id, new_season_id_param;
                END IF;
                
                -- Create the new team
                INSERT INTO team (
                    name, captain_id, season_id,
                    team_lineage_id, previous_team_id, original_season_id,
                    is_continuing_team, team_legacy_name,
                    created_at
                ) VALUES (
                    new_team_name_param,
                    captain_id_param,
                    new_season_id_param,
                    previous_team.team_lineage_id,  -- Same lineage
                    previous_team_id_param,         -- Link to previous
                    previous_team.original_season_id, -- Keep original season
                    true,                           -- This is a continuing team
                    COALESCE(previous_team.team_legacy_name, previous_team.name), -- Preserve legacy name
                    CURRENT_TIMESTAMP
                ) RETURNING id INTO new_team_id;
                
                RETURN new_team_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ create_continuing_team() function created")
        
        # Function to create a completely new team
        cursor.execute("""
            CREATE OR REPLACE FUNCTION create_new_team(
                team_name_param VARCHAR(50),
                captain_id_param INTEGER,
                season_id_param INTEGER
            )
            RETURNS INTEGER AS $$
            DECLARE
                new_team_id INTEGER;
                new_lineage_id INTEGER;
            BEGIN
                -- Get new lineage ID
                SELECT nextval('team_lineage_seq') INTO new_lineage_id;
                
                -- Create the new team
                INSERT INTO team (
                    name, captain_id, season_id,
                    team_lineage_id, previous_team_id, original_season_id,
                    is_continuing_team, team_legacy_name,
                    created_at
                ) VALUES (
                    team_name_param,
                    captain_id_param,
                    season_id_param,
                    new_lineage_id,
                    NULL,                    -- No previous team
                    season_id_param,         -- This is the original season
                    false,                   -- Brand new team
                    team_name_param,         -- Legacy name same as current
                    CURRENT_TIMESTAMP
                ) RETURNING id INTO new_team_id;
                
                RETURN new_team_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ create_new_team() function created")
        
        # Function to get team lineage history
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_team_lineage_history(lineage_id_param INTEGER)
            RETURNS TABLE(
                team_id INTEGER,
                team_name VARCHAR(50),
                season_id INTEGER,
                season_name VARCHAR(100),
                captain_id INTEGER,
                is_continuing_team BOOLEAN,
                created_at TIMESTAMP
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    t.id,
                    t.name,
                    t.season_id,
                    s.name,
                    t.captain_id,
                    t.is_continuing_team,
                    t.created_at
                FROM team t
                JOIN season s ON t.season_id = s.id
                WHERE t.team_lineage_id = lineage_id_param
                ORDER BY s.created_at ASC;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_team_lineage_history() function created")
        
        # Function to get team's previous season performance
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_team_previous_season_info(current_team_id_param INTEGER)
            RETURNS TABLE(
                previous_team_id INTEGER,
                previous_team_name VARCHAR(50),
                previous_season_name VARCHAR(100),
                total_bids BIGINT,
                total_matches BIGINT,
                team_legacy_name VARCHAR(100)
            ) AS $$
            BEGIN
                RETURN QUERY
                SELECT 
                    pt.id,
                    pt.name,
                    ps.name,
                    (SELECT COUNT(*) FROM bid WHERE team_id = pt.id) as total_bids,
                    (SELECT COUNT(*) FROM match WHERE home_team_id = pt.id OR away_team_id = pt.id) as total_matches,
                    pt.team_legacy_name
                FROM team ct
                JOIN team pt ON ct.previous_team_id = pt.id
                JOIN season ps ON pt.season_id = ps.id
                WHERE ct.id = current_team_id_param;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ get_team_previous_season_info() function created")
        
        print("\n📋 Step 6: Creating team lineage indexes...")
        
        # Create indexes for optimal lineage queries
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_team_lineage_id ON team(team_lineage_id)",
            "CREATE INDEX IF NOT EXISTS idx_team_previous_team_id ON team(previous_team_id)",
            "CREATE INDEX IF NOT EXISTS idx_team_original_season_id ON team(original_season_id)",
            "CREATE INDEX IF NOT EXISTS idx_team_is_continuing ON team(is_continuing_team)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
        
        print(f"   ✅ Created {len(indexes)} lineage indexes")
        
        print("\n📋 Step 7: Creating team lineage statistics view...")
        
        cursor.execute("""
            CREATE OR REPLACE VIEW team_lineage_stats AS
            SELECT 
                tl.team_lineage_id,
                tl.team_legacy_name,
                tl.original_season_name,
                COUNT(tl.team_id) as seasons_participated,
                tl.first_season,
                tl.latest_season,
                CASE 
                    WHEN COUNT(tl.team_id) = 1 THEN 'New Team'
                    WHEN COUNT(tl.team_id) > 1 THEN 'Multi-Season Team'
                    ELSE 'Unknown'
                END as team_type
            FROM (
                SELECT 
                    t.team_lineage_id,
                    t.team_legacy_name,
                    t.id as team_id,
                    os.name as original_season_name,
                    MIN(s.created_at) OVER (PARTITION BY t.team_lineage_id) as first_season,
                    MAX(s.created_at) OVER (PARTITION BY t.team_lineage_id) as latest_season
                FROM team t
                JOIN season s ON t.season_id = s.id
                LEFT JOIN season os ON t.original_season_id = os.id
                WHERE t.team_lineage_id IS NOT NULL
            ) tl
            GROUP BY 
                tl.team_lineage_id, tl.team_legacy_name, tl.original_season_name,
                tl.first_season, tl.latest_season
            ORDER BY tl.team_lineage_id;
        """)
        print("   ✅ team_lineage_stats view created")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 8: Verification & Analysis...")
        
        # Verify lineage columns were added
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'team'
              AND column_name IN (
                  'team_lineage_id', 'previous_team_id', 'original_season_id',
                  'is_continuing_team', 'team_legacy_name'
              )
            ORDER BY column_name
        """)
        
        lineage_columns_verified = cursor.fetchall()
        print(f"   📊 Lineage columns verified: {len(lineage_columns_verified)}/5")
        for col_name, data_type, nullable in lineage_columns_verified:
            print(f"      ✅ {col_name} ({data_type}, nullable: {nullable})")
        
        # Verify functions exist
        cursor.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'public'
              AND routine_name IN (
                  'create_continuing_team', 'create_new_team',
                  'get_team_lineage_history', 'get_team_previous_season_info'
              )
            ORDER BY routine_name
        """)
        
        functions = [row[0] for row in cursor.fetchall()]
        expected_functions = [
            'create_continuing_team', 'create_new_team',
            'get_team_lineage_history', 'get_team_previous_season_info'
        ]
        
        print(f"   📊 Lineage functions: {len(functions)}/{len(expected_functions)}")
        for func in functions:
            print(f"      ✅ {func}()")
        
        # Show current team lineage distribution
        cursor.execute("SELECT * FROM team_lineage_stats ORDER BY team_lineage_id LIMIT 10")
        lineage_stats = cursor.fetchall()
        
        print(f"   📊 Team Lineage Statistics (showing first 10):")
        if lineage_stats:
            for lineage_id, legacy_name, orig_season, seasons_count, first, latest, team_type in lineage_stats:
                print(f"      Lineage {lineage_id}: {legacy_name} - {team_type} ({seasons_count} seasons)")
        else:
            print("      No lineage data found")
        
        # Show initialization summary
        cursor.execute("""
            SELECT 
                COUNT(*) as total_teams,
                COUNT(CASE WHEN team_lineage_id IS NOT NULL THEN 1 END) as teams_with_lineage,
                COUNT(CASE WHEN is_continuing_team = true THEN 1 END) as continuing_teams,
                COUNT(CASE WHEN is_continuing_team = false THEN 1 END) as new_teams
            FROM team
        """)
        
        summary = cursor.fetchone()
        if summary:
            total, with_lineage, continuing, new = summary
            print(f"   📊 Team Lineage Summary:")
            print(f"      • Total teams: {total}")
            print(f"      • Teams with lineage: {with_lineage}")
            print(f"      • Continuing teams: {continuing}")
            print(f"      • New teams: {new}")
        
        if (len(lineage_columns_verified) == 5 and len(functions) == len(expected_functions) 
            and initialized_count >= 0):
            
            print("\n🎉 TASK 5 COMPLETED SUCCESSFULLY!")
            print("✅ Added team lineage tracking to team table")
            print("✅ Created team lineage management functions")
            print("✅ Initialized existing teams with lineage data")
            print("✅ Created lineage statistics and analysis views")
            print("✅ Added database indexes for optimal lineage queries")
            print("✅ System ready for multi-season team continuity")
            
            print("\n📝 KEY CAPABILITIES NOW AVAILABLE:")
            print("   • Teams can continue across seasons with same identity")
            print("   • Track team history and performance across seasons")
            print("   • Distinguish between new teams and continuing teams")
            print("   • Maintain team legacy names for historical reference")
            print("   • Link teams to their previous season versions")
            
            return True
        else:
            print(f"\n❌ TASK 5 FAILED:")
            print(f"   • Lineage columns: {len(lineage_columns_verified)}/5")
            print(f"   • Functions: {len(functions)}/{len(expected_functions)}")
            print(f"   • Initialization: {initialized_count} teams")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 5: {e}")
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

def rollback_task_05():
    """Rollback Task 5 changes if needed"""
    conn = None
    cursor = None
    
    try:
        print("\n🔄 ROLLBACK TASK 5: Remove Team Lineage Tracking")
        print("⚠️  WARNING: This will remove all lineage tracking from teams!")
        
        response = input("Are you sure you want to rollback Task 5? (y/N): ").lower().strip()
        if response != 'y':
            print("❌ Rollback cancelled")
            return False
        
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        # Drop functions
        functions_to_drop = [
            'create_continuing_team', 'create_new_team',
            'get_team_lineage_history', 'get_team_previous_season_info'
        ]
        
        for func in functions_to_drop:
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER) CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(INTEGER, INTEGER, VARCHAR, INTEGER) CASCADE")
            cursor.execute(f"DROP FUNCTION IF EXISTS {func}(VARCHAR, INTEGER, INTEGER) CASCADE")
        
        # Drop view
        cursor.execute("DROP VIEW IF EXISTS team_lineage_stats CASCADE")
        
        # Drop sequence
        cursor.execute("DROP SEQUENCE IF EXISTS team_lineage_seq CASCADE")
        
        # Drop indexes
        indexes_to_drop = [
            "idx_team_lineage_id", "idx_team_previous_team_id",
            "idx_team_original_season_id", "idx_team_is_continuing"
        ]
        
        for index_name in indexes_to_drop:
            cursor.execute(f"DROP INDEX IF EXISTS {index_name}")
        
        # Remove lineage columns
        lineage_columns = [
            'team_lineage_id', 'previous_team_id', 'original_season_id',
            'is_continuing_team', 'team_legacy_name'
        ]
        
        for col_name in lineage_columns:
            if check_column_exists(cursor, 'team', col_name):
                cursor.execute(f'ALTER TABLE team DROP COLUMN {col_name} CASCADE')
                print(f"   ✅ Removed {col_name} from team table")
        
        conn.commit()
        
        print("✅ Task 5 rollback completed")
        return True
        
    except Exception as e:
        print(f"💥 ERROR in Task 5 rollback: {e}")
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
        success = rollback_task_05()
    else:
        success = execute_task_05()
    
    sys.exit(0 if success else 1)