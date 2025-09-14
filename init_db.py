from app import app, db
# Import all models to ensure they're registered with SQLAlchemy
from models import (
    User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker,
    PasswordResetRequest, AuctionSettings, BulkBidTiebreaker, 
    BulkBidRound, BulkBid, TeamBulkTiebreaker, TeamMember, 
    Category, Match, PlayerMatchup, TeamStats, PlayerStats, 
    StarredPlayer
)
from werkzeug.security import generate_password_hash
import os
import pandas as pd
import sqlite3
import shutil
from datetime import datetime

def init_database():
    """Initialize the database by creating all tables."""
    
    # Check if build-time database initialization should be skipped
    if os.environ.get('SKIP_BUILD_DB_INIT', 'false').lower() == 'true':
        print("\n" + "="*60)
        print("🔄 BUILD-TIME DATABASE INITIALIZATION SKIPPED")
        print("="*60)
        print("SKIP_BUILD_DB_INIT environment variable is set to 'true'")
        print("Database initialization will be performed at runtime.")
        print("="*60)
        
        # Create skip flag file
        try:
            with open('/tmp/db_init_skipped', 'w') as f:
                f.write(f'Database initialization intentionally skipped at {datetime.now().isoformat()} due to SKIP_BUILD_DB_INIT=true')
            print("📁 Created runtime initialization flag: /tmp/db_init_skipped")
        except Exception as flag_error:
            print(f"⚠️  Could not create flag file: {flag_error}")
        
        print("\n✅ Build will continue - database setup deferred to runtime.")
        return
    
    with app.app_context():
        print("Initializing database...")
        print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'][:50]}...")
        
        # Test database connection with retries
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries}: Testing database connection...")
                # Test connection by running a simple query with timeout
                # Add connection pool settings to handle IPv6/network issues
                from sqlalchemy import create_engine
                test_engine = create_engine(
                    app.config['SQLALCHEMY_DATABASE_URI'],
                    pool_timeout=30,
                    pool_recycle=300,
                    pool_pre_ping=True,
                    connect_args={
                        "connect_timeout": 30,
                        "options": "-c statement_timeout=30000"
                    }
                )
                with test_engine.connect() as conn:
                    conn.execute(db.text("SELECT 1"))
                test_engine.dispose()
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
                    error_str = str(e)
                    if any(keyword in error_str for keyword in [
                        "Network is unreachable", "connection to server", 
                        "Name or service not known", "could not translate host name",
                        "No address associated with hostname", "nodename nor servname provided",
                        "Connection refused", "timeout", "Temporary failure in name resolution"
                    ]):
                        print("\n" + "="*60)
                        print("🔄 DATABASE CONNECTIVITY ISSUE DETECTED")
                        print("="*60)
                        print("This is common during Render deployment when:")
                        print("• The database service is still starting up")
                        print("• DNS propagation is in progress")
                        print("• Network routing is being established")
                        print("")
                        print("✅ SOLUTION: Database initialization will be deferred to runtime.")
                        print("The app will automatically initialize the database when it first starts.")
                        print("="*60)
                        
                        # Create an empty flag file to indicate initialization was skipped
                        try:
                            with open('/tmp/db_init_skipped', 'w') as f:
                                f.write(f'Database initialization skipped at {datetime.now().isoformat()} due to connectivity issues during build\nError: {error_str}')
                            print("📁 Created runtime initialization flag: /tmp/db_init_skipped")
                        except Exception as flag_error:
                            print(f"⚠️  Could not create flag file: {flag_error}")
                        
                        print("\n✅ Build will continue - database setup deferred to runtime.")
                        return  # Exit gracefully, don't raise an error
                    else:
                        print(f"\n❌ FATAL DATABASE ERROR (non-connectivity issue): {repr(e)}")
                        print("This error is not related to network connectivity and needs investigation.")
                        # Still create the flag file but also raise the error for debugging
                        try:
                            with open('/tmp/db_init_failed', 'w') as f:
                                f.write(f'Database initialization failed at {datetime.now().isoformat()} with error: {repr(e)}')
                        except Exception:
                            pass
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
        
        # Create uploads directory for team logos if it doesn't exist
        try:
            uploads_dir = os.path.join(app.root_path, 'static', 'uploads', 'logos')
            os.makedirs(uploads_dir, exist_ok=True)
            print(f"Ensured uploads directory exists: {uploads_dir}")
            
            # Create a simple placeholder logo if it doesn't exist
            placeholder_path = os.path.join(app.root_path, 'static', 'img', 'default-team-logo.png')
            img_dir = os.path.dirname(placeholder_path)
            os.makedirs(img_dir, exist_ok=True)
            
            # Only create placeholder if it doesn't exist
            if not os.path.exists(placeholder_path):
                print(f"Creating default team logo placeholder at: {placeholder_path}")
                # Note: You should replace this with an actual logo file
                # For now, we'll just create a text file as a placeholder
                # In production, you'd want to have an actual PNG image
                print("Note: Please add a default-team-logo.png file to static/img/ directory")
                
        except Exception as e:
            print(f"Warning: Could not set up uploads directory: {e}")
        
        # Initialize auction settings if they don't exist
        try:
            if not AuctionSettings.query.first():
                print("Creating default auction settings...")
                default_settings = AuctionSettings(
                    max_rounds=25,
                    min_balance_per_round=30
                )
                db.session.add(default_settings)
                db.session.commit()
                print("Default auction settings created")
        except Exception as e:
            print(f"Warning: Could not create default auction settings: {e}")
        
        print("Database initialization complete")

if __name__ == '__main__':
    init_database()
