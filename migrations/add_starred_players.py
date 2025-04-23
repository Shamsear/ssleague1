from app import app, db
from models import StarredPlayer

def run_migration():
    """
    Create the starred_player table if it doesn't exist.
    This migration adds support for users to star players they're interested in.
    """
    with app.app_context():
        # Check if the table already exists
        engine = db.engine
        inspector = db.inspect(engine)
        tables = inspector.get_table_names()
        
        if 'starred_player' not in tables:
            print("Creating starred_player table...")
            # Create the table
            StarredPlayer.__table__.create(engine)
            print("Table created successfully!")
        else:
            print("starred_player table already exists, skipping migration")

if __name__ == "__main__":
    run_migration() 