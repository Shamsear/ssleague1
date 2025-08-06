"""
Script to fix PostgreSQL collation version mismatch warning
"""
import psycopg2
from psycopg2 import sql
import sys

# Database connection parameters - update these with your actual values
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'postgres',  # Connect to postgres database first
    'user': 'postgres',      # Update with your PostgreSQL superuser
    'password': 'your_password'  # Update with your password
}

def fix_collation_mismatch():
    """Fix the collation version mismatch in auction_db"""
    conn = None
    cur = None
    
    try:
        # Connect to PostgreSQL
        print("Connecting to PostgreSQL...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True  # Required for ALTER DATABASE
        cur = conn.cursor()
        
        # Check if auction_db exists
        cur.execute("""
            SELECT 1 FROM pg_database WHERE datname = 'auction_db'
        """)
        
        if not cur.fetchone():
            print("Database 'auction_db' not found!")
            return False
        
        # Fix the collation version mismatch
        print("Refreshing collation version for auction_db...")
        cur.execute(sql.SQL("ALTER DATABASE {} REFRESH COLLATION VERSION").format(
            sql.Identifier('auction_db')
        ))
        
        print("✓ Collation version refreshed successfully!")
        
        # Optional: Connect to auction_db and reindex if needed
        print("\nDo you want to reindex the database? This can help with any text-based indexes.")
        print("This may take some time for large databases.")
        response = input("Reindex? (y/n): ").lower().strip()
        
        if response == 'y':
            # Close current connection
            cur.close()
            conn.close()
            
            # Connect to auction_db
            DB_CONFIG['database'] = 'auction_db'
            conn = psycopg2.connect(**DB_CONFIG)
            conn.autocommit = True
            cur = conn.cursor()
            
            print("Reindexing auction_db...")
            cur.execute("REINDEX DATABASE auction_db")
            print("✓ Database reindexed successfully!")
        
        return True
        
    except psycopg2.Error as e:
        print(f"PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("PostgreSQL Collation Version Fix Tool")
    print("=" * 40)
    
    # Prompt for database credentials if not set
    if DB_CONFIG['password'] == 'your_password':
        import getpass
        DB_CONFIG['password'] = getpass.getpass("Enter PostgreSQL password: ")
    
    if fix_collation_mismatch():
        print("\n✓ All operations completed successfully!")
        print("You can now restart your Flask application.")
    else:
        print("\n✗ Fix failed. Please check the error messages above.")
        sys.exit(1)
