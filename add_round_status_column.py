from app import app, db
from sqlalchemy import text

def add_column():
    """Add status column to the round table if it doesn't exist"""
    with app.app_context():
        # Check if the column exists
        try:
            db.session.execute(text("SELECT status FROM round LIMIT 1"))
            print("Column 'status' already exists in the 'round' table.")
            return
        except Exception as e:
            if "column round.status does not exist" in str(e):
                print("Column 'status' doesn't exist, adding it now...")
            else:
                print(f"Unexpected error: {e}")
                return
                
        # Add the column with a default value
        db.session.execute(text("ALTER TABLE round ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
        db.session.commit()
        print("Successfully added 'status' column to 'round' table")

if __name__ == "__main__":
    add_column() 