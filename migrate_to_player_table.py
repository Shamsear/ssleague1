import sqlite3
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connections
SQLITE_DB_PATH = 'efootball_real.db'
NEON_DATABASE_URL = os.environ.get('DATABASE_URL')

def get_neon_connection():
    """Create connection to Neon PostgreSQL database"""
    return psycopg2.connect(NEON_DATABASE_URL)

def extract_sqlite_data():
    """Extract player data from SQLite database"""
    conn = sqlite3.connect(SQLITE_DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM players_all ORDER BY overall_rating DESC")
        players = cursor.fetchall()
        
        # Get column names
        cursor.execute("PRAGMA table_info(players_all)")
        columns = [col[1] for col in cursor.fetchall()]
        
        print(f"Extracted {len(players)} players from SQLite database")
        print(f"SQLite columns: {columns}")
        return players, columns
        
    finally:
        cursor.close()
        conn.close()

def migrate_to_player_table():
    """Migrate data from SQLite to existing Neon player table"""
    print("=== Migrating to existing 'player' table ===")
    
    # Extract data from SQLite
    players_data, sqlite_columns = extract_sqlite_data()
    
    # Connect to Neon
    conn = get_neon_connection()
    cursor = conn.cursor()
    
    try:
        # Check current count
        cursor.execute("SELECT COUNT(*) FROM player")
        current_count = cursor.fetchone()[0]
        print(f"Current players in Neon table: {current_count}")
        
        # Handle existing data
        if current_count > 0:
            print(f"⚠️  Found {current_count} existing players in the table.")
            print("This migration will clear all existing data and replace it with eFootball data.")
            print("Note: This will also clear related data due to foreign key constraints.")
            response = input("Do you want to proceed? (y/N): ").lower().strip()
            if response != 'y':
                print("Migration cancelled.")
                return
            
            # Clear existing data with CASCADE to handle foreign key constraints
            cursor.execute("TRUNCATE TABLE player RESTART IDENTITY CASCADE")
            print("Cleared existing data from player table and related tables")
        else:
            print("Player table is empty, proceeding with migration...")
        
        # Prepare insert statement matching the existing player table structure
        insert_sql = """
        INSERT INTO player (
            name, position, team_name, nationality, 
            offensive_awareness, ball_control, dribbling, tight_possession, 
            low_pass, lofted_pass, finishing, heading, set_piece_taking, curl,
            speed, acceleration, kicking_power, jumping, physical_contact, balance, stamina,
            defensive_awareness, tackling, aggression, defensive_engagement,
            gk_awareness, gk_catching, gk_parrying, gk_reflexes, gk_reach,
            overall_rating, playing_style, player_id, is_auction_eligible
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """
        
        # Insert data in batches for better performance
        batch_size = 50  # Smaller batches to avoid timeouts
        successful_inserts = 0
        failed_inserts = 0
        
        print(f"Starting migration in batches of {batch_size}...")
        
        for i in range(0, len(players_data), batch_size):
            batch = players_data[i:i+batch_size]
            batch_data = []
            
            for player in batch:
                # Map SQLite data to Neon player table
                # SQLite: id, position, player_name, team_name, nationality, ...
                player_data = (
                    player[2],   # player_name -> name
                    player[1],   # position
                    player[3],   # team_name  
                    player[4],   # nationality
                    player[5],   # offensive_awareness
                    player[6],   # ball_control
                    player[7],   # dribbling
                    player[8],   # tight_possession
                    player[9],   # low_pass
                    player[10],  # lofted_pass
                    player[11],  # finishing
                    player[12],  # heading
                    player[13],  # set_piece_taking
                    player[14],  # curl
                    player[15],  # speed
                    player[16],  # acceleration
                    player[17],  # kicking_power
                    player[18],  # jumping
                    player[19],  # physical_contact
                    player[20],  # balance
                    player[21],  # stamina
                    player[22],  # defensive_awareness
                    player[23],  # tackling
                    player[24],  # aggression
                    player[25],  # defensive_engagement
                    player[26],  # gk_awareness
                    player[27],  # gk_catching
                    player[28],  # gk_parrying
                    player[29],  # gk_reflexes
                    player[30],  # gk_reach
                    player[31],  # overall_rating
                    player[32],  # playing_style
                    int(player[33]) if player[33] else None,  # player_id (convert to int)
                    True         # is_auction_eligible (default to True)
                )
                batch_data.append(player_data)
            
            try:
                cursor.executemany(insert_sql, batch_data)
                conn.commit()
                successful_inserts += len(batch_data)
                print(f"✅ Batch {i//batch_size + 1}: {len(batch_data)} players (Total: {successful_inserts})")
                
            except Exception as e:
                print(f"❌ Error in batch {i//batch_size + 1}: {e}")
                conn.rollback()
                failed_inserts += len(batch_data)
                
                # Try individual inserts for this batch
                print(f"   Retrying individual inserts for this batch...")
                for j, player_data in enumerate(batch_data):
                    try:
                        cursor.execute(insert_sql, player_data)
                        conn.commit()
                        successful_inserts += 1
                        failed_inserts -= 1
                    except Exception as individual_error:
                        print(f"   Failed to insert player {player_data[0]}: {individual_error}")
        
        print(f"\n🏁 Migration Summary:")
        print(f"   ✅ Successfully inserted: {successful_inserts} players")
        print(f"   ❌ Failed inserts: {failed_inserts} players")
        print(f"   📊 Success rate: {successful_inserts/(successful_inserts+failed_inserts)*100:.1f}%")
        
        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM player")
        final_count = cursor.fetchone()[0]
        print(f"   📈 Final count in Neon: {final_count} players")
        
        # Show top players by rating
        cursor.execute("""
            SELECT name, team_name, position, overall_rating, nationality 
            FROM player 
            ORDER BY overall_rating DESC 
            LIMIT 10
        """)
        top_players = cursor.fetchall()
        
        print(f"\n🌟 Top 10 Players by Overall Rating:")
        print("-" * 80)
        for i, player in enumerate(top_players, 1):
            print(f"{i:2}. {player[0]:<25} ({player[1]:<20}) {player[2]:<5} - {player[3]} - {player[4]}")
        
        # Show position distribution
        cursor.execute("""
            SELECT position, COUNT(*) as count 
            FROM player 
            GROUP BY position 
            ORDER BY count DESC
        """)
        position_stats = cursor.fetchall()
        
        print(f"\n📊 Players by Position:")
        print("-" * 30)
        for pos, count in position_stats:
            print(f"{pos:<5}: {count:>4} players")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def main():
    """Main migration function"""
    print("=== eFootball to Neon Player Table Migration ===")
    print(f"Source: SQLite ({SQLITE_DB_PATH}) -> players_all table")
    print(f"Target: Neon PostgreSQL -> player table")
    print("=" * 60)
    
    try:
        migrate_to_player_table()
        print(f"\n✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    main()