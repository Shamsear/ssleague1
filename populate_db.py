from app import app
from models import db, User, Team, Player, Round
from werkzeug.security import generate_password_hash

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
    positions = ['GK', 'CB', 'EB', 'LB', 'CMF', 'DMF', 'RMF', 'LMF', 'AMF', 'SS', 'CF']
    players = []
    
    for position in positions:
        for i in range(1, 21):  # 20 players per position
            player = Player(
                name=f'Player {i} {position}',
                position=position
            )
            db.session.add(player)
            players.append(player)
    
    return players

def main():
    with app.app_context():
        # Clear existing data
        db.drop_all()
        db.create_all()
        
        # Create admin
        admin = create_admin()
        
        # Create teams
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