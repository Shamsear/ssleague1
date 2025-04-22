from app import app, db
import psycopg2
from config import Config
from datetime import datetime

def create_team_management_tables():
    # Connect directly to database
    conn = psycopg2.connect(Config.SQLALCHEMY_DATABASE_URI)
    cursor = conn.cursor()
    
    try:
        # Create Category table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS category (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) UNIQUE NOT NULL,
            color VARCHAR(50) NOT NULL,
            priority INTEGER DEFAULT 0,
            points_same_category INTEGER DEFAULT 8,
            points_one_level_diff INTEGER DEFAULT 7,
            points_two_level_diff INTEGER DEFAULT 6,
            points_three_level_diff INTEGER DEFAULT 5
        )
        ''')
        
        # Create TeamMember table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_member (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            team_id INTEGER NOT NULL REFERENCES team(id),
            category_id INTEGER NOT NULL REFERENCES category(id),
            photo_url VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create Match table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS match (
            id SERIAL PRIMARY KEY,
            home_team_id INTEGER NOT NULL REFERENCES team(id),
            away_team_id INTEGER NOT NULL REFERENCES team(id),
            home_score INTEGER DEFAULT 0,
            away_score INTEGER DEFAULT 0,
            match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            round_number INTEGER NOT NULL,
            match_number INTEGER NOT NULL,
            is_completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create PlayerMatchup table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_matchup (
            id SERIAL PRIMARY KEY,
            match_id INTEGER NOT NULL REFERENCES match(id) ON DELETE CASCADE,
            home_player_id INTEGER NOT NULL REFERENCES team_member(id),
            away_player_id INTEGER NOT NULL REFERENCES team_member(id),
            home_goals INTEGER DEFAULT 0,
            away_goals INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Create TeamStats table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_stats (
            id SERIAL PRIMARY KEY,
            team_id INTEGER NOT NULL REFERENCES team(id) UNIQUE,
            played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            goals_for INTEGER DEFAULT 0,
            goals_against INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0
        )
        ''')
        
        # Create PlayerStats table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            id SERIAL PRIMARY KEY,
            team_member_id INTEGER NOT NULL REFERENCES team_member(id) UNIQUE,
            played INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            draws INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            goals_scored INTEGER DEFAULT 0,
            goals_conceded INTEGER DEFAULT 0,
            clean_sheets INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0
        )
        ''')
        
        # Insert default categories if they don't exist
        for category_data in [
            ('Red', 'red', 1, 8, 7, 6, 5),
            ('Black', 'black', 2, 8, 7, 6, 5),
            ('Blue', 'blue', 3, 8, 7, 6, 5),
            ('White', 'white', 4, 8, 7, 6, 5)
        ]:
            try:
                cursor.execute('''
                INSERT INTO category (name, color, priority, 
                                      points_same_category, points_one_level_diff, 
                                      points_two_level_diff, points_three_level_diff)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', category_data)
            except psycopg2.errors.UniqueViolation:
                # Category already exists, skip
                conn.rollback()
                continue
        
        # Initialize team stats for existing teams
        cursor.execute("SELECT id FROM team")
        team_ids = cursor.fetchall()
        
        for team_id in team_ids:
            try:
                cursor.execute('''
                INSERT INTO team_stats (team_id)
                VALUES (%s)
                ''', (team_id[0],))
            except psycopg2.errors.UniqueViolation:
                # Stats already exist for this team, skip
                conn.rollback()
                continue
        
        # Commit the transaction
        conn.commit()
        print("Team management tables created successfully!")
        
    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    create_team_management_tables() 