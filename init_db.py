from app import app, db
from models import User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker
from werkzeug.security import generate_password_hash
import os
import pandas as pd
import sqlite3
import logging
import sys

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    stream=sys.stdout)
logger = logging.getLogger(__name__)

def check_efootball_db():
    """Check if the efootball_real.db file exists and is accessible."""
    db_path = 'efootball_real.db'
    if not os.path.exists(db_path):
        logger.error(f"Error: {db_path} not found in current directory.")
        logger.info(f"Current directory: {os.getcwd()}")
        logger.info(f"Directory contents: {os.listdir('.')}")
        return False
    
    try:
        # Test connection
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM players_all")
        count = cursor.fetchone()[0]
        conn.close()
        logger.info(f"Successfully connected to {db_path}. Contains {count} players.")
        return True
    except Exception as e:
        logger.error(f"Error accessing {db_path}: {e}")
        return False

def import_players_from_db():
    """Import players from the efootball_real.db database."""
    db_path = 'efootball_real.db'
    logger.info(f"Importing players from {db_path}...")
    
    try:
        # Connect to SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
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
                logger.info(f"Adding batch of {len(batch)} players...")
                db.session.add_all(batch)
                db.session.commit()
                batch = []
        
        # Add remaining players
        if batch:
            logger.info(f"Adding final batch of {len(batch)} players...")
            db.session.add_all(batch)
            db.session.commit()
        
        conn.close()
        logger.info(f"Successfully imported {player_count} players")
        return player_count
    
    except Exception as e:
        logger.error(f"Error importing players: {e}")
        db.session.rollback()
        return 0

def init_database():
    """Initialize the database by creating all tables."""
    with app.app_context():
        logger.info("Creating database tables...")
        db.create_all()
        
        # Check if we already have an admin user
        admin_exists = User.query.filter_by(is_admin=True).first() is not None
        
        if not admin_exists:
            logger.info("Creating admin user...")
            admin = User(
                username='admin',
                is_admin=True,
                is_approved=True
            )
            admin.set_password('admin123')  # Change this in production!
            db.session.add(admin)
            
            # Commit admin user only
            db.session.commit()
            logger.info("Admin user created")
        
        # Check if we have players
        player_count = Player.query.count()
        if player_count == 0:
            # Check if efootball_real.db exists and is accessible
            if check_efootball_db():
                # Import players from SQLite database
                imported_count = import_players_from_db()
                if imported_count > 0:
                    logger.info(f"Database initialization complete with {imported_count} players")
                else:
                    logger.warning("No players were imported. Check the efootball_real.db file.")
            else:
                logger.warning("efootball_real.db not available. No players imported.")
        else:
            logger.info(f"Database already contains {player_count} players. Skipping import.")
        
        logger.info("Database initialization complete")

if __name__ == '__main__':
    init_database() 