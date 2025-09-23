#!/usr/bin/env python3
"""
Team Round Page Performance Analysis
Analyze what's causing slow loading times in the team_round route
"""

import os
import sys
import time
from flask import Flask
from models import db, Round, Player, Team, User, AuctionSettings, BulkBidRound, TeamBulkTiebreaker, BulkBidTiebreaker, TeamTiebreaker, Tiebreaker, StarredPlayer
from config import Config

def create_app():
    """Create Flask app instance"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def simulate_team_round_loading():
    """Simulate the team_round route to identify performance bottlenecks"""
    app = create_app()
    
    with app.app_context():
        print("🔍 Analyzing Team Round Page Performance")
        print("=" * 60)
        
        overall_start = time.time()
        
        # Simulate having a team (get the first available team)
        test_team = Team.query.first()
        if not test_team:
            print("❌ No teams found in database for testing")
            return
            
        print(f"📊 Testing with team: {test_team.name} (ID: {test_team.id})")
        print("-" * 60)
        
        # Step 1: Check for bulk bid tiebreakers (FIRST QUERY)
        step_start = time.time()
        team_bulk_tiebreakers = TeamBulkTiebreaker.query.join(
            BulkBidTiebreaker, TeamBulkTiebreaker.tiebreaker_id == BulkBidTiebreaker.id
        ).filter(
            TeamBulkTiebreaker.team_id == test_team.id,
            TeamBulkTiebreaker.is_active == True,
            BulkBidTiebreaker.resolved == False
        ).all()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 1 - Check bulk tiebreakers: {step_time:.2f}ms")
        print(f"    Results: {len(team_bulk_tiebreakers)} bulk tiebreakers")
        
        if step_time > 1000:
            print("    ⚠️  SLOW! This query is taking over 1 second!")
            print("    💡 Possible missing indexes on team_bulk_tiebreaker or bulk_bid_tiebreaker")
        
        # Step 2: Check for regular tiebreakers (SECOND QUERY)  
        step_start = time.time()
        team_tiebreakers = TeamTiebreaker.query.join(
            Tiebreaker, TeamTiebreaker.tiebreaker_id == Tiebreaker.id
        ).filter(
            TeamTiebreaker.team_id == test_team.id,
            Tiebreaker.resolved == False
        ).all()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 2 - Check regular tiebreakers: {step_time:.2f}ms")
        print(f"    Results: {len(team_tiebreakers)} regular tiebreakers")
        
        if step_time > 1000:
            print("    ⚠️  SLOW! This query is taking over 1 second!")
            print("    💡 Possible missing indexes on team_tiebreaker or tiebreaker")
        
        # Step 3: Get active rounds (THIRD QUERY)
        step_start = time.time()
        active_rounds = Round.query.filter_by(is_active=True).all()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 3 - Get active rounds: {step_time:.2f}ms")
        print(f"    Results: {len(active_rounds)} active rounds")
        
        # Step 4: Get auction settings (FOURTH QUERY)
        step_start = time.time()
        settings = AuctionSettings.get_settings()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 4 - Get auction settings: {step_time:.2f}ms")
        
        # Step 5: Get completed rounds count (FIFTH QUERY)
        step_start = time.time()
        completed_rounds_count = Round.query.filter_by(is_active=False).count()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 5 - Count completed rounds: {step_time:.2f}ms")
        print(f"    Results: {completed_rounds_count} completed rounds")
        
        # Step 6: Get active bulk bid round (SIXTH QUERY)
        step_start = time.time()
        active_bulk_round = BulkBidRound.query.filter_by(is_active=True).first()
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 6 - Get active bulk round: {step_time:.2f}ms")
        print(f"    Results: {'Found' if active_bulk_round else 'None'}")
        
        # Step 7: Get starred players (SEVENTH QUERY)
        step_start = time.time()
        starred_players = StarredPlayer.query.filter_by(team_id=test_team.id).all()
        starred_player_ids = [sp.player_id for sp in starred_players]
        step_time = (time.time() - step_start) * 1000
        print(f"🔍 Step 7 - Get starred players: {step_time:.2f}ms")
        print(f"    Results: {len(starred_players)} starred players")
        
        if step_time > 500:
            print("    ⚠️  SLOW! Starred players query is taking over 500ms!")
            print("    💡 Possible missing index on starred_player.team_id")
        
        overall_time = (time.time() - overall_start) * 1000
        
        print("-" * 60)
        print(f"🎯 TOTAL TEAM ROUND PAGE LOAD TIME: {overall_time:.2f}ms")
        
        if overall_time < 1000:
            print("✅ GOOD: Page loads in under 1 second")
        elif overall_time < 3000:
            print("⚠️  SLOW: Page takes 1-3 seconds to load")
        else:
            print("❌ VERY SLOW: Page takes over 3 seconds to load!")
        
        return overall_time

def check_missing_indexes():
    """Check for missing indexes that might affect team_round performance"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 Checking for Missing Indexes")
        print("=" * 40)
        
        engine = db.engine
        
        # Check for specific indexes that team_round needs
        needed_indexes = [
            {
                'table': 'team_bulk_tiebreaker',
                'columns': ['team_id', 'is_active'],
                'description': 'For bulk tiebreaker lookup by team'
            },
            {
                'table': 'team_bulk_tiebreaker', 
                'columns': ['tiebreaker_id'],
                'description': 'For join with bulk_bid_tiebreaker'
            },
            {
                'table': 'bulk_bid_tiebreaker',
                'columns': ['resolved'],
                'description': 'For filtering unresolved tiebreakers'
            },
            {
                'table': 'team_tiebreaker',
                'columns': ['team_id'],
                'description': 'For regular tiebreaker lookup by team'
            },
            {
                'table': 'tiebreaker',
                'columns': ['resolved'],
                'description': 'For filtering unresolved regular tiebreakers'
            },
            {
                'table': 'starred_player',
                'columns': ['team_id'],
                'description': 'For starred players lookup by team'
            }
        ]
        
        try:
            from sqlalchemy import text
            
            # Get all existing indexes
            index_check_sql = """
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes 
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname;
            """
            
            with engine.connect() as connection:
                result = connection.execute(text(index_check_sql))
                existing_indexes = result.fetchall()
                
                # Create a set of existing table.columns combinations
                existing_combinations = set()
                for index in existing_indexes:
                    table_name = index[1]
                    index_def = index[3].lower()
                    
                    # Extract column names from index definition (basic parsing)
                    if '(' in index_def and ')' in index_def:
                        cols_part = index_def.split('(')[1].split(')')[0]
                        cols = [col.strip() for col in cols_part.split(',')]
                        for col in cols:
                            existing_combinations.add(f"{table_name}.{col}")
                
                print("📊 Analyzing needed indexes for team_round:")
                missing_indexes = []
                
                for needed in needed_indexes:
                    table = needed['table']
                    columns = needed['columns']
                    desc = needed['description']
                    
                    # Check if we have indexes for these columns
                    has_indexes = all(f"{table}.{col}" in existing_combinations for col in columns)
                    
                    if not has_indexes:
                        missing_columns = [col for col in columns if f"{table}.{col}" not in existing_combinations]
                        missing_indexes.append({
                            'table': table,
                            'missing_columns': missing_columns,
                            'description': desc
                        })
                        print(f"   ❌ Missing: {table}({', '.join(missing_columns)}) - {desc}")
                    else:
                        print(f"   ✅ Found: {table}({', '.join(columns)}) - {desc}")
                
                if missing_indexes:
                    print(f"\n⚠️  Found {len(missing_indexes)} missing indexes that could slow down team_round!")
                    return missing_indexes
                else:
                    print(f"\n✅ All needed indexes appear to be present!")
                    return []
                    
        except Exception as e:
            print(f"❌ Error checking indexes: {e}")
            return []

def generate_index_fixes(missing_indexes):
    """Generate SQL statements to fix missing indexes"""
    if not missing_indexes:
        return
        
    print("\n🔧 Recommended Index Fixes")
    print("=" * 40)
    
    for missing in missing_indexes:
        table = missing['table']
        columns = missing['missing_columns']
        desc = missing['description']
        
        index_name = f"idx_{table}_{'_'.join(columns)}"
        columns_str = ', '.join(columns)
        
        sql = f"CREATE INDEX {index_name} ON {table} ({columns_str});"
        
        print(f"-- {desc}")
        print(f"{sql}")
        print()

def main():
    """Run the team_round performance analysis"""
    print("🔧 Team Round Performance Analysis")
    print("=" * 60)
    
    # Check database connection
    app = create_app()
    try:
        with app.app_context():
            from sqlalchemy import text
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Run performance analysis
    try:
        missing_indexes = check_missing_indexes()
        total_time = simulate_team_round_loading()
        
        print("\n" + "="*60)
        print("🎯 TEAM ROUND PERFORMANCE ANALYSIS SUMMARY")
        print("="*60)
        
        if total_time < 1000:
            print("🚀 GOOD: Team round page loads quickly!")
        elif total_time < 3000:
            print("⚠️  SLOW: Team round page needs optimization")
        else:
            print("❌ CRITICAL: Team round page is very slow!")
            
        print(f"📈 Total load time: {total_time:.2f}ms")
        
        if missing_indexes:
            print(f"⚠️  Found {len(missing_indexes)} missing indexes")
            generate_index_fixes(missing_indexes)
            print("💡 Run the suggested CREATE INDEX statements to improve performance")
        else:
            print("✅ All needed indexes are present")
            if total_time > 2000:
                print("💡 Performance issue may be due to:")
                print("   - Large amount of data in tables")
                print("   - Complex join operations")
                print("   - Network latency to database")
                print("   - Other database performance issues")
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")

if __name__ == '__main__':
    main()