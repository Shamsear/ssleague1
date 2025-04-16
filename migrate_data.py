import sqlite3
import psycopg2
from flask import Flask
from config import Config
import sys
import os
from populate_db import populate_database  # Import the existing populate function if available

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    return app

def migrate_data():
    # Get the PostgreSQL connection string from the environment
    pg_connection_string = os.environ.get('DATABASE_URL')
    
    if not pg_connection_string:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    # Handle the potential prefix change in the connection string
    if pg_connection_string.startswith('postgres://'):
        pg_connection_string = pg_connection_string.replace('postgres://', 'postgresql://', 1)
    
    # Try to use the populate_database function if it exists
    app = create_app()
    with app.app_context():
        try:
            print("Starting database population...")
            populate_database()
            print("Database populated successfully!")
            return
        except Exception as e:
            print(f"Error using populate_db function: {e}")
            print("Falling back to manual data migration...")
    
    try:
        # Connect to SQLite database
        sqlite_conn = sqlite3.connect('efootball_real.db')
        sqlite_cursor = sqlite_conn.cursor()
        
        # Connect to PostgreSQL database
        pg_conn = psycopg2.connect(pg_connection_string)
        pg_cursor = pg_conn.cursor()
        
        # Get all tables from SQLite
        sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = sqlite_cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            
            # Skip SQLite system tables
            if table_name.startswith('sqlite_'):
                continue
                
            print(f"Migrating table: {table_name}")
            
            # Get table schema
            sqlite_cursor.execute(f"PRAGMA table_info({table_name});")
            columns = sqlite_cursor.fetchall()
            column_names = [column[1] for column in columns]
            
            # Get data from SQLite
            sqlite_cursor.execute(f"SELECT * FROM {table_name};")
            rows = sqlite_cursor.fetchall()
            
            if not rows:
                print(f"  No data in table {table_name}, skipping")
                continue
                
            # Insert data into PostgreSQL
            placeholders = ','.join(['%s'] * len(column_names))
            columns_str = ','.join([f'"{col}"' for col in column_names])
            
            for row in rows:
                insert_query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING;'
                try:
                    pg_cursor.execute(insert_query, row)
                except Exception as e:
                    print(f"  Error inserting row: {e}")
                    pg_conn.rollback()
                    continue
            
            pg_conn.commit()
            print(f"  Migrated {len(rows)} rows from {table_name}")
        
        print("Data migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        if 'pg_conn' in locals():
            pg_conn.rollback()
        sys.exit(1)
    finally:
        if 'sqlite_conn' in locals():
            sqlite_conn.close()
        if 'pg_conn' in locals():
            pg_conn.close()

if __name__ == "__main__":
    migrate_data() 