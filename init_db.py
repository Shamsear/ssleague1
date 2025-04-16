from flask import Flask
from flask_migrate import Migrate, upgrade
from models import db, User, Player
from config import Config
from werkzeug.security import generate_password_hash
import os
import subprocess
import sys
import sqlite3

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    Migrate(app, db)
    
    return app

def create_players(app):
    with app.app_context():
        # Check if players already exist
        if Player.query.count() > 0:
            print("Players already exist in the database. Skipping player creation.")
            return
            
        try:
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
            
            players_added = 0
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
                players_added += 1
                
                # Commit in batches to avoid memory issues
                if players_added % 100 == 0:
                    db.session.commit()
                    print(f"Added {players_added} players so far...")
            
            # Final commit for remaining players
            db.session.commit()
            print(f"Successfully created {players_added} players from efootball_real.db")
            
            conn.close()
            return players
        except Exception as e:
            db.session.rollback()
            print(f"Error creating players: {e}")
            return []

def init_database(app):
    with app.app_context():
        # Apply migrations
        upgrade()
        
        # Create admin user if it doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(username='admin', is_admin=True, is_approved=True)
            admin.set_password('admin123')  # Change this to a secure password
            db.session.add(admin)
            db.session.commit()
            print("Admin user created.")
        else:
            print("Admin user already exists.")
            
        print("Database structure initialization completed successfully.")
    
    # Create players from efootball_real.db
    print("Creating players from efootball_real.db...")
    create_players(app)
    
    # Run the data migration script
    print("Starting data migration process...")
    try:
        result = subprocess.run([sys.executable, 'migrate_data.py'], check=True)
        if result.returncode == 0:
            print("Data migration completed successfully.")
        else:
            print(f"Data migration failed with return code {result.returncode}")
    except Exception as e:
        print(f"Error running data migration: {e}")

if __name__ == '__main__':
    app = create_app()
    init_database(app) 