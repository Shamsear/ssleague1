from app import app, db
from models import User, Player
from werkzeug.security import generate_password_hash
import sqlite3
import os

def import_players():
    """Import players from efootball_real.db if it exists"""
    db_path = 'efootball_real.db'
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Warning: {db_path} not found, skipping player import")
        return 0
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all players from the database with all fields
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
        
        players_count = 0
        
        for row in cursor.fetchall():
            # Check if player already exists
            existing_player = Player.query.filter_by(player_id=row[32]).first()
            if existing_player:
                continue
                
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
            db.session.add(player)
            players_count += 1
            
            # Commit in batches to prevent memory issues
            if players_count % 100 == 0:
                db.session.commit()
        
        # Final commit for any remaining players
        db.session.commit()
        conn.close()
        return players_count
        
    except Exception as e:
        print(f"Error importing players: {str(e)}")
        return 0

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin'),
                is_admin=True,
                is_approved=True
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created")
        else:
            print("Admin user already exists")
        
        # Import players
        players_count = import_players()
        if players_count > 0:
            print(f"Imported {players_count} players from efootball_real.db")
        
        print("Database initialized successfully")

if __name__ == '__main__':
    init_db()