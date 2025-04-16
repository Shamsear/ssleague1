from app import app, db
from models import User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker
from werkzeug.security import generate_password_hash
import argparse
import sqlite3

def create_players():
    print("Importing players from efootball_real.db...")
    conn = sqlite3.connect('efootball_real.db')
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
    players = []
    player_count = 0
    
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
        db.session.add(player)
        player_count += 1
    
    conn.close()
    db.session.commit()
    print(f"Imported {player_count} players successfully")
    return players

def init_db(drop_all=False, import_players=False):
    with app.app_context():
        if drop_all:
            print("Dropping all tables...")
            db.drop_all()
            print("All tables dropped successfully")
        
        # Create all tables
        print("Creating tables...")
        db.create_all()
        print("Tables created successfully")
        
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
        
        # Import players if requested
        if import_players:
            create_players()
        
        print("Database initialized successfully")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Initialize the database')
    parser.add_argument('--drop-all', action='store_true', help='Drop all tables before creating them')
    parser.add_argument('--import-players', action='store_true', help='Import players from efootball_real.db')
    args = parser.parse_args()
    
    init_db(drop_all=args.drop_all, import_players=args.import_players)