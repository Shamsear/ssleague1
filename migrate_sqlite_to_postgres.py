import os
import sqlite3
import psycopg2
from app import app, db
from models import Player
from dotenv import load_dotenv

load_dotenv()

def migrate_players():
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect('efootball_real.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all players from SQLite
    sqlite_cursor.execute('SELECT * FROM player')
    players = sqlite_cursor.fetchall()
    
    # Get column names
    sqlite_cursor.execute('PRAGMA table_info(player)')
    columns = [column[1] for column in sqlite_cursor.fetchall()]
    
    print(f"Found {len(players)} players to migrate")
    print(f"Columns: {columns}")
    
    # Prepare data for PostgreSQL
    with app.app_context():
        # Make sure tables exist
        db.create_all()
        
        # Clear existing players if needed
        # Uncomment the next line if you want to clear existing data
        # Player.query.delete()
        
        # Insert each player
        for player_data in players:
            player_dict = {columns[i]: player_data[i] for i in range(len(columns))}
            
            # Create new Player object using the right column mappings
            # Adjust this part according to your actual model structure
            player = Player(
                id=player_dict.get('id'),
                name=player_dict.get('name'),
                rating=player_dict.get('rating'),
                position=player_dict.get('position'),
                nationality=player_dict.get('nationality'),
                value=player_dict.get('value'),
                playing_style=player_dict.get('playing_style', None)
            )
            
            # Add to session
            db.session.add(player)
        
        # Commit all changes
        db.session.commit()
        print(f"Successfully migrated {len(players)} players to PostgreSQL")
    
    # Close SQLite connection
    sqlite_conn.close()

if __name__ == "__main__":
    try:
        migrate_players()
    except Exception as e:
        print(f"Error during migration: {e}") 