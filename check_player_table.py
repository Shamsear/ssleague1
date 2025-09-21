import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def check_player_table():
    """Check the existing player table structure in Neon"""
    conn = psycopg2.connect(NEON_DATABASE_URL)
    cursor = conn.cursor()
    
    try:
        # Get columns info for player table
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'player'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        
        print("Existing 'player' table structure:")
        print("=" * 50)
        for col in columns:
            nullable = "NULL" if col[2] == 'YES' else "NOT NULL"
            max_length = f"({col[4]})" if col[4] else ""
            default = f" DEFAULT {col[3]}" if col[3] else ""
            print(f"  - {col[0]}: {col[1]}{max_length} {nullable}{default}")
        
        # Check row count
        cursor.execute("SELECT COUNT(*) FROM player")
        count = cursor.fetchone()[0]
        print(f"\nCurrent row count: {count}")
        
        # Show sample data
        if count > 0:
            cursor.execute("SELECT * FROM player LIMIT 3")
            sample_rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description]
            print(f"\nSample data (showing first 3 rows):")
            print(f"Columns: {column_names}")
            for i, row in enumerate(sample_rows, 1):
                print(f"Row {i}: {row}")
        
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    check_player_table()