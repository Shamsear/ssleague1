"""
Add GitHub Logo Support Fields

This migration adds support for storing team logos in GitHub repositories.
It adds new columns to track storage type and GitHub-specific metadata.
"""

from models import db, Team
from sqlalchemy import text

def add_github_logo_fields():
    """Add GitHub logo support fields to Team model"""
    try:
        # Check if we're using SQLite or another database
        engine = db.engine
        
        if 'sqlite' in str(engine.url):
            # SQLite doesn't support ALTER COLUMN, so we need to be careful
            # First, check if columns exist
            inspector = db.inspect(engine)
            columns = [col['name'] for col in inspector.get_columns('team')]
            
            # Add logo_storage_type if it doesn't exist
            if 'logo_storage_type' not in columns:
                db.session.execute(text("""
                    ALTER TABLE team ADD COLUMN logo_storage_type VARCHAR(20) DEFAULT 'local'
                """))
            
            # Add github_logo_sha if it doesn't exist
            if 'github_logo_sha' not in columns:
                db.session.execute(text("""
                    ALTER TABLE team ADD COLUMN github_logo_sha VARCHAR(100)
                """))
            
            # Extend logo_url length if needed (SQLite limitation - we'll handle this in app logic)
            print("Note: SQLite doesn't support column modification. logo_url length will be handled in app logic.")
        else:
            # For PostgreSQL, MySQL, etc.
            # Modify existing logo_url column to support longer URLs
            db.session.execute(text("""
                ALTER TABLE team ALTER COLUMN logo_url TYPE VARCHAR(500)
            """))
            
            # Add new columns
            db.session.execute(text("""
                ALTER TABLE team ADD COLUMN logo_storage_type VARCHAR(20) DEFAULT 'local'
            """))
            
            db.session.execute(text("""
                ALTER TABLE team ADD COLUMN github_logo_sha VARCHAR(100)
            """))
        
        db.session.commit()
        print("Successfully added GitHub logo support fields")
        
    except Exception as e:
        print(f"Error adding GitHub logo fields: {e}")
        db.session.rollback()
        raise

if __name__ == '__main__':
    from app import app
    
    with app.app_context():
        add_github_logo_fields()
