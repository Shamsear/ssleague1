from app import app, db
from sqlalchemy import text
import sys

def check_and_add_column(table, column, column_type, default_value=None):
    """Check if a column exists in a table and add it if it doesn't"""
    try:
        db.session.execute(text(f"SELECT {column} FROM {table} LIMIT 1"))
        print(f"Column '{column}' already exists in the '{table}' table.")
        return False
    except Exception as e:
        if f"column {table}.{column} does not exist" in str(e):
            print(f"Column '{column}' doesn't exist in '{table}' table, adding it now...")
            
            # Build the ALTER TABLE statement
            sql = f"ALTER TABLE {table} ADD COLUMN {column} {column_type}"
            if default_value is not None:
                if isinstance(default_value, str):
                    sql += f" DEFAULT '{default_value}'"
                else:
                    sql += f" DEFAULT {default_value}"
                    
            db.session.execute(text(sql))
            db.session.commit()
            print(f"Successfully added '{column}' column to '{table}' table")
            return True
        else:
            print(f"Unexpected error checking '{column}' in '{table}': {e}")
            return False

def migrate_database():
    """Add missing columns to match the models"""
    with app.app_context():
        changes_made = False
        
        # Round table columns
        changes_made |= check_and_add_column("round", "status", "VARCHAR(50)", "active")
        changes_made |= check_and_add_column("round", "max_bids_per_team", "INTEGER", 1)
        
        # AuctionStatus table
        try:
            db.session.execute(text("SELECT * FROM auction_status LIMIT 1"))
            print("Table 'auction_status' already exists.")
        except Exception as e:
            if "relation \"auction_status\" does not exist" in str(e):
                print("Table 'auction_status' doesn't exist, creating it now...")
                db.session.execute(text("""
                    CREATE TABLE auction_status (
                        id SERIAL PRIMARY KEY,
                        current_round INTEGER DEFAULT 0,
                        is_active BOOLEAN DEFAULT FALSE,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status VARCHAR(50) DEFAULT 'not_started',
                        finalization_status VARCHAR(100),
                        last_finalization_message VARCHAR(500)
                    )
                """))
                db.session.commit()
                print("Successfully created 'auction_status' table")
                changes_made = True
            else:
                print(f"Unexpected error checking 'auction_status' table: {e}")
        
        # Add missing columns to AuctionStatus if it exists
        changes_made |= check_and_add_column("auction_status", "finalization_status", "VARCHAR(100)")
        changes_made |= check_and_add_column("auction_status", "last_finalization_message", "VARCHAR(500)")
        
        # Add is_active to Team if needed
        changes_made |= check_and_add_column("team", "is_active", "BOOLEAN", True)
        
        if changes_made:
            print("\nDatabase schema has been updated successfully.")
        else:
            print("\nNo changes were needed. Database schema is up to date.")
            
        return changes_made

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1) 