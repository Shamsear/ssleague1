import sqlite3
import psycopg2
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

# Load environment variables
load_dotenv()

# Database connections
SQLITE_DB_PATH = 'efootball_real.db'
NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def get_neon_connection():
    """Create connection to Neon PostgreSQL database"""
    return psycopg2.connect(NEON_DATABASE_URL)

def check_neon_tables():
    """Check existing tables in Neon database"""
    conn = get_neon_connection()
    cursor = conn.cursor()
    
    try:
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        
        print("Tables in Neon database:")
        for table in tables:
            print(f"  - {table[0]}")
        
        # Check if players table exists
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'players'
        """)
        players_table_exists = cursor.fetchone() is not None
        
        if players_table_exists:
            print("\n'players' table already exists!")
            # Get columns info
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'players'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            print("Existing columns:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
        else:
            print("\n'players' table does not exist. Will create it.")
            
        return players_table_exists
        
    finally:
        cursor.close()
        conn.close()

def create_players_table():
    """Create players table in Neon with schema matching SQLite data"""
    conn = get_neon_connection()
    cursor = conn.cursor()
    
    try:
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS players (
            id SERIAL PRIMARY KEY,
            position VARCHAR(10),
            player_name VARCHAR(255),
            team_name VARCHAR(255),
            nationality VARCHAR(100),
            offensive_awareness INTEGER,
            ball_control INTEGER,
            dribbling INTEGER,
            tight_possession INTEGER,
            low_pass INTEGER,
            lofted_pass INTEGER,
            finishing INTEGER,
            heading INTEGER,
            set_piece_taking INTEGER,
            curl INTEGER,
            speed INTEGER,
            acceleration INTEGER,
            kicking_power INTEGER,
            jumping INTEGER,
            physical_contact INTEGER,
            balance INTEGER,
            stamina INTEGER,
            defensive_awareness INTEGER,
            tackling INTEGER,
            aggression INTEGER,
            defensive_engagement INTEGER,
            gk_awareness INTEGER,
            gk_catching INTEGER,
            gk_parrying INTEGER,
            gk_reflexes INTEGER,
            gk_reach INTEGER,
            overall_rating INTEGER,
            playing_style VARCHAR(100),
            player_id VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        print("Players table created successfully!")
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_player_id ON players(player_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_position ON players(position)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_team ON players(team_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_players_overall_rating ON players(overall_rating)")
        conn.commit()
        print("Indexes created successfully!")
        
    except Exception as e:
        print(f"Error creating players table: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def extract_sqlite_data():
    """Extract player data from SQLite database"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM players_all")
        players = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(players_all)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Extracted {len(players)} players from SQLite database")
        return players, columns
        
    finally:
        cursor.close()
        conn.close()

def migrate_data():
    """Migrate data from SQLite to Neon PostgreSQL"""
    print("Starting data migration...")
    
    # Extract data from SQLite
    players_data, columns = extract_sqlite_data()
    
    # Connect to Neon
    conn = get_neon_connection()
    cursor = conn.cursor()
    
    try:
        # Clear existing data (optional - remove this if you want to append)
        cursor.execute("TRUNCATE TABLE players RESTART IDENTITY")
        print("Cleared existing data from players table")
        
        # Prepare insert statement (excluding the SQLite id, we'll use SERIAL)
        insert_sql = """
        INSERT INTO players (
            position, player_name, team_name, nationality, offensive_awareness,
            ball_control, dribbling, tight_possession, low_pass, lofted_pass,
            finishing, heading, set_piece_taking, curl, speed, acceleration,
            kicking_power, jumping, physical_contact, balance, stamina,
            defensive_awareness, tackling, aggression, defensive_engagement,
            gk_awareness, gk_catching, gk_parrying, gk_reflexes, gk_reach,
            overall_rating, playing_style, player_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s
        )
        """
        
        # Insert data in batches for better performance
        batch_size = 100
        successful_inserts = 0
        
        for i in range(0, len(players_data), batch_size):
            batch = players_data[i:i+batch_size]
            batch_data = []
            
            for player in batch:
                # Skip the first column (SQLite id) and use the rest
                player_data = player[1:]  # Skip SQLite id
                batch_data.append(player_data)
            
            try:
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                successful_inserts += len(batch_data)
                print(f"Inserted batch {i//batch_size + 1}: {len(batch_data)} players (Total: {successful_inserts})")
                
            except Exception as e:
                print(f"Error inserting batch {i//batch_size + 1}: {e}")
                conn.rollback()
                # Try individual inserts for this batch
                for player_data in batch_data:
                    try:
                        cursor.execute(insert_sql, player_data)
                        conn.commit()
                        successful_inserts += 1
                    except Exception as individual_error:
                        print(f"Error inserting individual player: {individual_error}")
                        conn.rollback()
        
        print(f"\nMigration completed! Successfully inserted {successful_inserts} out of {len(players_data)} players")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM players")
        count = cursor.fetchone()[0]
        print(f"Total players in Neon database: {count}")
        
        # Show sample data
        cursor.execute("SELECT player_name, team_name, position, overall_rating FROM players ORDER BY overall_rating DESC LIMIT 5")
        top_players = cursor.fetchall()
        print("\nTop 5 players by overall rating:")
        for player in top_players:
            print(f"  - {player[0]} ({player[1]}) - {player[2]} - Rating: {player[3]}")
            
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Main migration function"""
    print("=== eFootball Player Data Migration ===")
    print(f"Source: SQLite ({SQLITE_DB_PATH})")
    print(f"Target: Neon PostgreSQL")
    print("="*50)
    
    try:
        # Step 1: Check Neon database structure
        print("\n1. Checking Neon database...")
        players_table_exists = check_neon_tables()
        
        # Step 2: Create players table if it doesn't exist
        if not players_table_exists:
            print("\n2. Creating players table...")
            create_players_table()
        else:
            print("\n2. Players table already exists, skipping creation...")
        
        # Step 3: Migrate data
        print("\n3. Migrating player data...")
        migrate_data()
        
        print("\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()