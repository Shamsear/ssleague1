#!/usr/bin/env python3
"""
Database migration to add ImageKit support

This migration adds the imagekit_file_id column to the Team table
and updates the logo_storage_type enum to include 'imagekit'.

Usage:
    python migrations/add_imagekit_support.py
"""

import os
import sys

# Add the parent directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Team
from sqlalchemy import text

def run_migration():
    """Run the ImageKit support migration"""
    
    with app.app_context():
        print("🚀 Starting ImageKit support migration...")
        
        try:
            # Check if the column already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name = 'team' 
                AND column_name = 'imagekit_file_id'
            """)).scalar()
            
            if result > 0:
                print("✅ imagekit_file_id column already exists")
            else:
                print("📝 Adding imagekit_file_id column...")
                db.session.execute(text("""
                    ALTER TABLE team 
                    ADD COLUMN imagekit_file_id VARCHAR(100)
                """))
                print("✅ Added imagekit_file_id column")
            
            # Update the comment for logo_storage_type to document new options
            print("📝 Updating logo_storage_type documentation...")
            db.session.execute(text("""
                COMMENT ON COLUMN team.logo_storage_type IS 'Storage type: local, github, or imagekit'
            """))
            
            # Commit the changes
            db.session.commit()
            print("✅ Migration completed successfully!")
            
            # Show summary
            total_teams = Team.query.count()
            github_teams = Team.query.filter_by(logo_storage_type='github').count()
            local_teams = Team.query.filter_by(logo_storage_type='local').count()
            imagekit_teams = Team.query.filter_by(logo_storage_type='imagekit').count()
            
            print(f"\n📊 Team logo storage summary:")
            print(f"  Total teams: {total_teams}")
            print(f"  GitHub storage: {github_teams}")
            print(f"  Local storage: {local_teams}")
            print(f"  ImageKit storage: {imagekit_teams}")
            
            if github_teams > 0:
                print(f"\n💡 You have {github_teams} team(s) using GitHub storage.")
                print("   Consider running the migration utility to move them to ImageKit:")
                print("   python migrate_to_imagekit.py --dry-run")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            db.session.rollback()
            return False
            
    return True

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)