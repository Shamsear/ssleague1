from app import app, db
from models import User, Team, Player, Round, Bid, Tiebreaker, TeamTiebreaker
from werkzeug.security import generate_password_hash
import os
import pandas as pd
import sqlite3

def init_database():
    """Initialize the database by creating all tables."""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
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
            
            # Create an admin team
            admin_team = Team(
                name='Admin Team',
                user=admin
            )
            db.session.add(admin_team)
            
            # Commit admin user and team
            db.session.commit()
            print("Admin user created")
        
        # Check if we have players
        if Player.query.count() == 0 and os.path.exists('efootball_real.db'):
            print("Importing players from SQLite database...")
            # Import players from SQLite database
            try:
                # Connect to SQLite
                conn = sqlite3.connect('efootball_real.db')
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
        
        print("Database initialization complete")

if __name__ == '__main__':
    init_database() 