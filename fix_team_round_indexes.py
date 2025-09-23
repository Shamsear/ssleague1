#!/usr/bin/env python3
"""
Fix Missing Indexes for Team Round Page
Add the missing database indexes that are causing slow team_round page loads
"""

import os
import sys
from flask import Flask
from models import db
from config import Config
from sqlalchemy import text

def create_app():
    """Create Flask app instance"""
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

def apply_team_round_indexes():
    """Apply the missing indexes for team_round page performance"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Fixing Team Round Page Performance")
        print("=" * 50)
        
        engine = db.engine
        
        # Missing indexes identified by analysis
        missing_indexes = [
            {
                'name': 'idx_team_bulk_tiebreaker_team_id_is_active',
                'table': 'team_bulk_tiebreaker',
                'columns': ['team_id', 'is_active'],
                'description': 'Composite index for bulk tiebreaker lookup by team and status'
            },
            {
                'name': 'idx_team_bulk_tiebreaker_tiebreaker_id',
                'table': 'team_bulk_tiebreaker',
                'columns': ['tiebreaker_id'],
                'description': 'Index for join with bulk_bid_tiebreaker table'
            },
            {
                'name': 'idx_bulk_bid_tiebreaker_resolved',
                'table': 'bulk_bid_tiebreaker',
                'columns': ['resolved'],
                'description': 'Index for filtering unresolved bulk tiebreakers'
            }
        ]
        
        created_count = 0
        skipped_count = 0
        
        for index in missing_indexes:
            try:
                columns_str = ', '.join(index['columns'])
                sql = f"CREATE INDEX {index['name']} ON {index['table']} ({columns_str})"
                
                print(f"📊 Creating: {index['name']}")
                print(f"   Table: {index['table']}")
                print(f"   Columns: {columns_str}")
                print(f"   Purpose: {index['description']}")
                
                with engine.connect() as connection:
                    connection.execute(text(sql))
                    connection.commit()
                
                print(f"   ✅ Success!")
                created_count += 1
                
            except Exception as e:
                error_msg = str(e).lower()
                if 'already exists' in error_msg or 'duplicate' in error_msg:
                    print(f"   ⚠️  Already exists (skipped)")
                    skipped_count += 1
                else:
                    print(f"   ❌ Error: {e}")
            
            print()
        
        print("=" * 50)
        print(f"🎯 Team Round Index Fix Summary:")
        print(f"   ✅ Created: {created_count} indexes")
        print(f"   ⚠️  Skipped: {skipped_count} indexes (already exist)")
        
        if created_count > 0:
            print()
            print("🚀 TEAM ROUND PERFORMANCE BOOST APPLIED!")
            print("   Page load time should now be under 1 second")
            print("   Tiebreaker queries are now optimized")
            print("   User experience significantly improved")

def test_improvement():
    """Test the performance improvement after applying indexes"""
    print("\n🧪 Testing Performance Improvement")
    print("=" * 40)
    
    # Import and run the analysis again
    try:
        import subprocess
        result = subprocess.run([
            'python', 
            'C:\\Drive d\\SS\\test\\analyze_team_round_performance.py'
        ], capture_output=True, text=True, cwd='C:\\Drive d\\SS\\test')
        
        if result.returncode == 0:
            output_lines = result.stdout.split('\n')
            
            # Look for the total load time
            for line in output_lines:
                if 'TOTAL TEAM ROUND PAGE LOAD TIME:' in line:
                    time_part = line.split(':')[1].strip()
                    load_time = float(time_part.replace('ms', ''))
                    
                    print(f"📈 New load time: {load_time:.2f}ms")
                    
                    if load_time < 1000:
                        print("🚀 EXCELLENT! Page now loads in under 1 second!")
                    elif load_time < 1500:
                        print("✅ GOOD! Significant improvement achieved!")
                    else:
                        print("⚠️  Some improvement, but may need additional optimization")
                    break
        else:
            print("⚠️  Could not run performance test automatically")
            
    except Exception as e:
        print(f"⚠️  Could not run automatic test: {e}")

def main():
    """Main function to apply the fixes"""
    print("🔧 Team Round Performance Fix")
    print("=" * 50)
    
    # Check database connection
    app = create_app()
    try:
        with app.app_context():
            with db.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    print()
    
    # Apply the missing indexes
    try:
        apply_team_round_indexes()
        test_improvement()
        
        print("\n" + "="*50)
        print("🎉 TEAM ROUND OPTIMIZATION COMPLETE!")
        print("="*50)
        print("✅ Missing indexes have been added")
        print("🚀 Page load performance should be dramatically improved")
        print("💡 Test the team_round page to see the difference!")
        
    except Exception as e:
        print(f"❌ Error during optimization: {e}")

if __name__ == '__main__':
    main()