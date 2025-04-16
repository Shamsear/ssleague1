from app import app, db
from models import User, Player, Team, Round, Bid, TiebreakerBid, AuctionStatus
from werkzeug.security import generate_password_hash
import sqlite3
import os
import datetime

def create_players():
    # Check if the SQLite database file exists
    if not os.path.exists('efootball_real.db'):
        print("Warning: efootball_real.db not found. Skipping player import.")
        return []
        
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
        players.append(player)
    
    conn.close()
    return players

def create_teams():
    """Create default teams for the auction"""
    teams = []
    
    # Check if teams already exist
    if Team.query.count() > 0:
        print("Teams already exist, skipping team creation.")
        return teams
    
    # Create default teams with initial balance
    default_teams = [
        {"name": "Team Alpha", "balance": 1000000},
        {"name": "Team Beta", "balance": 1000000},
        {"name": "Team Gamma", "balance": 1000000},
        {"name": "Team Delta", "balance": 1000000},
        {"name": "Team Epsilon", "balance": 1000000},
        {"name": "Team Zeta", "balance": 1000000},
        {"name": "Team Eta", "balance": 1000000},
        {"name": "Team Theta", "balance": 1000000}
    ]
    
    for team_data in default_teams:
        team = Team(
            name=team_data["name"],
            balance=team_data["balance"],
            is_active=True
        )
        db.session.add(team)
        teams.append(team)
    
    print(f"{len(teams)} teams created successfully!")
    return teams

def initialize_auction_status():
    """Initialize or update the auction status"""
    status = AuctionStatus.query.first()
    
    if not status:
        status = AuctionStatus(
            current_round=0,
            is_active=False,
            last_updated=datetime.datetime.now(),
            status="not_started"
        )
        db.session.add(status)
        print("Auction status initialized!")
    else:
        print("Auction status already exists.")
    
    return status

def run_schema_migrations():
    """Run all necessary database schema migrations"""
    print("Checking for needed database schema updates...")
    
    # Check if Round.status column exists
    try:
        connection = db.engine.connect()
        transaction = connection.begin()
        
        # Check if the status column exists in the Round table
        inspector = db.inspect(db.engine)
        round_columns = [col['name'] for col in inspector.get_columns('round')]
        
        if 'status' not in round_columns:
            print("Adding 'status' column to Round table...")
            connection.execute(db.text('ALTER TABLE round ADD COLUMN status VARCHAR(50) DEFAULT \'active\''))
            transaction.commit()
            print("Added status column to Round table")
        else:
            transaction.rollback()
            print("Status column already exists in Round table")
            
    except Exception as e:
        try:
            transaction.rollback()
        except:
            pass
        print(f"Error during schema migration: {str(e)}")
        # If the table doesn't exist yet, create_all will handle it
        if "relation" not in str(e) and "does not exist" not in str(e):
            raise

def init_db():
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Run any needed schema migrations
        run_schema_migrations()
        
        # Check if admin user exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            # Create admin user
            admin = User(
                username='admin',
                is_admin=True,
                is_approved=True
            )
            admin.set_password('admin123')  # Change this password immediately after deployment
            db.session.add(admin)
            db.session.commit()
            print("Admin user created!")
        
        # Initialize teams
        teams = create_teams()
        
        # Check if players exist
        if Player.query.count() == 0:
            print("Importing players from SQLite database...")
            players = create_players()
            if players:
                db.session.commit()
                print(f"{len(players)} players imported successfully!")
        
        # Initialize auction status
        initialize_auction_status()
        
        # Commit all changes
        db.session.commit()
        
        print("Database initialized!")

if __name__ == '__main__':
    init_db() 