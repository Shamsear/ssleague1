import sqlite3
import sys

def run_migration():
    print("Adding position_group column to Player table...")
    
    # Connect to the database
    conn = sqlite3.connect('efootball_real.db')
    cursor = conn.cursor()
    
    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(player)")
        columns = cursor.fetchall()
        column_names = [column[1] for column in columns]
        
        if 'position_group' not in column_names:
            # Add the column with default value of NULL
            cursor.execute("ALTER TABLE player ADD COLUMN position_group VARCHAR(10)")
            print("Column added successfully!")
        else:
            print("Column already exists, skipping.")
        
        # Commit the changes
        conn.commit()
        print("Migration completed successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error during migration: {str(e)}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration() 