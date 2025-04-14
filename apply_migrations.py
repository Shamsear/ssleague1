from app import app, db
from models import Round, AuctionStatus
from sqlalchemy import text, inspect
import os

def apply_migrations():
    """Apply all necessary database migrations"""
    print("Starting database migrations...")
    
    with app.app_context():
        try:
            # Check for the Round.status column
            inspector = db.inspect(db.engine)
            
            if 'round' in inspector.get_table_names():
                round_columns = [col['name'] for col in inspector.get_columns('round')]
                
                if 'status' not in round_columns:
                    print("Adding 'status' column to Round table...")
                    # Use raw SQL for PostgreSQL
                    with db.engine.begin() as conn:
                        conn.execute(text("ALTER TABLE round ADD COLUMN status VARCHAR(50) DEFAULT 'active'"))
                    print("Added 'status' column to Round table")
                else:
                    print("Round.status column already exists")
            else:
                print("Round table doesn't exist yet - will be created with db.create_all()")
            
            # Ensure the AuctionStatus table exists
            if 'auction_status' not in inspector.get_table_names():
                print("Creating AuctionStatus table...")
                with db.engine.begin() as conn:
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS auction_status (
                            id SERIAL PRIMARY KEY,
                            current_round INTEGER DEFAULT 0,
                            is_active BOOLEAN DEFAULT FALSE,
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(50) DEFAULT 'not_started',
                            finalization_status VARCHAR(100),
                            last_finalization_message VARCHAR(500)
                        )
                    """))
                print("Created AuctionStatus table")
            else:
                # Check if the AuctionStatus table has all necessary columns
                auction_status_columns = [col['name'] for col in inspector.get_columns('auction_status')]
                
                missing_columns = []
                for column in ['finalization_status', 'last_finalization_message']:
                    if column not in auction_status_columns:
                        missing_columns.append(column)
                
                if missing_columns:
                    print(f"Adding missing columns to AuctionStatus table: {missing_columns}")
                    with db.engine.begin() as conn:
                        for column in missing_columns:
                            conn.execute(text(f"ALTER TABLE auction_status ADD COLUMN {column} VARCHAR(500)"))
                    print("Added missing columns to AuctionStatus table")
                else:
                    print("AuctionStatus table has all required columns")
            
            # Create all tables that don't exist yet
            db.create_all()
            
            # Make sure all rounds have a status
            with db.engine.begin() as conn:
                conn.execute(text("UPDATE round SET status = 'active' WHERE status IS NULL"))
                
            print("All migrations applied successfully!")
            
        except Exception as e:
            print(f"Error during migration: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

if __name__ == "__main__":
    apply_migrations() 