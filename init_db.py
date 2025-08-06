from app import app, db
from models import User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker
from werkzeug.security import generate_password_hash
import os
import pandas as pd
import sqlite3
import shutil

def init_database():
    """Initialize the database by creating all tables."""
    with app.app_context():
        print("Initializing database...")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Test database connection with retries
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries}: Testing database connection...")
                # Test connection by running a simple query
                with db.engine.connect() as conn:
                    conn.execute(db.text("SELECT 1"))
                print("Database connection successful!")
                break
            except Exception as e:
                print(f"Database connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    print("All database connection attempts failed.")
                    if "Network is unreachable" in str(e) or "connection to server" in str(e):
                        print("Network connectivity issue detected. This might be temporary.")
                        print("Skipping database initialization for now - will retry at runtime.")
                        return
                    else:
                        print(f"Fatal database error: {repr(e)}")
                        raise
        
        try:
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
            print(f"Full error: {repr(e)}")
            raise
        
        # Check if we already have an admin user
        admin_exists = User.query.filter_by(is_admin=True).first() is not None
        
        if not admin_exists:
            print("Creating admin user...")
            admin = User(
                username='admin',
                is_admin=True,
                is_approved=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            
            # Remove admin team creation
            
            # Commit admin user only
            db.session.commit()
            print("Admin user created")
        
        # Define possible paths for the SQLite database
        possible_paths = [
            'efootball_real.db',  # Local development path
            '/opt/render/project/src/efootball_real.db',  # Root path in Render
            '/opt/render/project/src/data/efootball_real.db'  # Persistent disk path in Render
        ]
        
        # Find the first existing SQLite database path
        db_path = None
        for path in possible_paths:
            if os.path.exists(path):
                db_path = path
                print(f"Found SQLite database at: {db_path}")
                break
        
        # If database file exists in repo but not in persistent storage on Render, copy it
        render_data_dir = '/opt/render/project/src/data'
        render_persistent_db = os.path.join(render_data_dir, 'efootball_real.db')
        if os.path.exists('efootball_real.db') and os.path.exists(render_data_dir) and not os.path.exists(render_persistent_db):
            print(f"Copying SQLite database to persistent storage: {render_persistent_db}")
            try:
                shutil.copy('efootball_real.db', render_persistent_db)
                db_path = render_persistent_db
                print("Database copied successfully")
            except Exception as e:
                print(f"Error copying database: {e}")
        
        # Check if we have players
        if Player.query.count() == 0 and db_path:
            print(f"Importing players from SQLite database at {db_path}...")
            # Import players from SQLite database
            try:
                # Connect to SQLite
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if the 'players_all' table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_all'")
                if not cursor.fetchone():
                    print("Error: 'players_all' table not found in the SQLite database")
                    conn.close()
                    return
                
                # Get player data
                cursor.execute("""
                    SELECT player_name, position, team_name, nationality,
                        offensive_awareness, ball_control, dribbling, tight_possession,
                        low_pass, lofted_pass, finishing, heading, set_piece_taking,
                        curl, speed, acceleration, kicking_power, jumping,
                        physical_contact, balance, stamina, defensive_awareness,
                        tackling, aggression, defensive_engagement, gk_awareness,
                        gk_catching, gk_parrying, gk_reflexes, gk_reach,
                        overall_rating, playing_style, player_id
                    FROM players_all
                """)
                
                player_count = 0
                batch_size = 100
                batch = []
                
                for row in cursor.fetchall():
                    player = Player(
                        name=row[0],
                        position=row[1],
                        team_name=row[2],
                        nationality=row[3],
                        offensive_awareness=row[4],
                        ball_control=row[5],
                        dribbling=row[6],
                        tight_possession=row[7],
                        low_pass=row[8],
                        lofted_pass=row[9],
                        finishing=row[10],
                        heading=row[11],
                        set_piece_taking=row[12],
                        curl=row[13],
                        speed=row[14],
                        acceleration=row[15],
                        kicking_power=row[16],
                        jumping=row[17],
                        physical_contact=row[18],
                        balance=row[19],
                        stamina=row[20],
                        defensive_awareness=row[21],
                        tackling=row[22],
                        aggression=row[23],
                        defensive_engagement=row[24],
                        gk_awareness=row[25],
                        gk_catching=row[26],
                        gk_parrying=row[27],
                        gk_reflexes=row[28],
                        gk_reach=row[29],
                        overall_rating=row[30],
                        playing_style=row[31],
                        player_id=row[32]
                    )
                    batch.append(player)
                    player_count += 1
                    
                    # Process in batches to avoid memory issues
                    if len(batch) >= batch_size:
                        db.session.add_all(batch)
                        db.session.commit()
                        batch = []
                
                # Add remaining players
                if batch:
                    db.session.add_all(batch)
                    db.session.commit()
                
                conn.close()
                print(f"Successfully imported {player_count} players")
            
            except Exception as e:
                print(f"Error importing players: {e}")
                db.session.rollback()
        elif Player.query.count() == 0 and not db_path:
            print("Error: No SQLite database found for player import")
        else:
            print(f"Player import skipped. Found {Player.query.count()} existing players.")
        
        print("Database initialization complete")

if __name__ == '__main__':
    init_database() 