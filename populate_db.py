from app import app
from models import db, User, Team, Player, Round
from werkzeug.security import generate_password_hash
import sqlite3

def create_admin():
    admin = User(
        username='admin',
        password_hash=generate_password_hash('admin123'),
        is_admin=True
    )
    db.session.add(admin)
    return admin

def create_teams():
    teams = []
    team_data = [
        {'username': 'team1', 'password': 'team1pass', 'team_name': 'Team Alpha'},
        {'username': 'team2', 'password': 'team2pass', 'team_name': 'Team Beta'}
    ]
    
    for data in team_data:
        user = User(
            username=data['username'],
            password_hash=generate_password_hash(data['password'])
        )
        db.session.add(user)
        team = Team(name=data['team_name'], user=user)
        db.session.add(team)
        teams.append(team)
    
    return teams

def create_players():
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

def main():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create admin
        admin = create_admin()
        
        # Create teams - note that admin won't have a team
        teams = create_teams()
        
        # Create players
        players = create_players()
        
        # Commit all changes
        db.session.commit()
        
        print("Database populated successfully!")
        print(f"Admin created: username='admin', password='admin123'")
        print("Teams created:")
        print("1. Team Alpha - username='team1', password='team1pass'")
        print("2. Team Beta - username='team2', password='team2pass'")
        print(f"Total players created: {len(players)}")

if __name__ == '__main__':
    main() 