#!/usr/bin/env python3
"""
MULTI-SEASON SYSTEM - TASK 6 EXECUTOR (FIXED)
====================================
Safely executes Task 6: Update Application Code for Season-Awareness

Fixed database function with proper column qualification.
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def fix_database_functions():
    """Fix the database functions with proper column qualification"""
    conn = None
    cursor = None
    
    try:
        print("🚀 FIXING TASK 6: Database Function Column Ambiguity")
        print("=" * 70)
        
        # Connect to database
        conn = psycopg2.connect(NEON_DATABASE_URL)
        cursor = conn.cursor()
        
        print("\n📋 Step 1: Fixing get_season_statistics() function...")
        
        # Drop and recreate the function with proper column qualification
        cursor.execute("DROP FUNCTION IF EXISTS get_season_statistics(INTEGER)")
        
        cursor.execute("""
            CREATE OR REPLACE FUNCTION get_season_statistics(season_id_param INTEGER DEFAULT NULL)
            RETURNS TABLE(
                season_id INTEGER,
                season_name VARCHAR(100),
                total_teams BIGINT,
                continuing_teams BIGINT,
                new_teams BIGINT,
                total_rounds BIGINT,
                active_rounds BIGINT,
                total_bids BIGINT
            ) AS $$
            DECLARE
                target_season_id INTEGER;
            BEGIN
                -- Use provided season_id or get current active season
                IF season_id_param IS NULL THEN
                    SELECT s.id INTO target_season_id 
                    FROM season s
                    WHERE s.is_active = true 
                    LIMIT 1;
                ELSE
                    target_season_id := season_id_param;
                END IF;
                
                -- Return statistics for the target season
                RETURN QUERY
                SELECT 
                    s.id,
                    s.name,
                    (SELECT COUNT(*) FROM team t WHERE t.season_id = s.id) as total_teams,
                    (SELECT COUNT(*) FROM team t WHERE t.season_id = s.id AND t.is_continuing_team = true) as continuing_teams,
                    (SELECT COUNT(*) FROM team t WHERE t.season_id = s.id AND t.is_continuing_team = false) as new_teams,
                    (SELECT COUNT(*) FROM round r WHERE r.season_id = s.id) as total_rounds,
                    (SELECT COUNT(*) FROM round r WHERE r.season_id = s.id AND r.is_active = true) as active_rounds,
                    (SELECT COUNT(*) FROM bid b WHERE b.season_id = s.id) as total_bids
                FROM season s
                WHERE s.id = target_season_id;
            END;
            $$ LANGUAGE plpgsql;
        """)
        print("   ✅ Fixed get_season_statistics() function")
        
        # Commit changes
        conn.commit()
        
        print("\n📋 Step 2: Testing fixed function...")
        
        # Test the function
        cursor.execute("SELECT * FROM get_season_statistics()")
        stats = cursor.fetchone()
        
        if stats:
            s_id, s_name, teams, cont_teams, new_teams, rounds, active_rounds, bids = stats
            print(f"   📊 Current Season Statistics:")
            print(f"      • Season: {s_name} (ID: {s_id})")
            print(f"      • Teams: {teams} total ({cont_teams} continuing, {new_teams} new)")
            print(f"      • Rounds: {rounds} total ({active_rounds} active)")
            print(f"      • Bids: {bids} total")
            
            print("\n🎉 TASK 6 DATABASE FIX COMPLETED SUCCESSFULLY!")
            return True
        else:
            print("❌ Function test failed")
            return False
            
    except Exception as e:
        print(f"\n💥 ERROR in Task 6 fix: {e}")
        if conn:
            conn.rollback()
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    success = fix_database_functions()
    sys.exit(0 if success else 1)