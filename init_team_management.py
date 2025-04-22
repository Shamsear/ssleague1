from app import app, db
from models import Category, TeamMember, Match, PlayerMatchup, TeamStats, PlayerStats, Team
from datetime import datetime

def init_team_management_db():
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        
        # Check if initial categories exist
        if Category.query.count() == 0:
            # Create default categories
            categories = [
                Category(name="Red", color="red", priority=1, 
                         points_same_category=8, points_one_level_diff=7, 
                         points_two_level_diff=6, points_three_level_diff=5),
                Category(name="Black", color="black", priority=2, 
                         points_same_category=8, points_one_level_diff=7, 
                         points_two_level_diff=6, points_three_level_diff=5),
                Category(name="Blue", color="blue", priority=3, 
                         points_same_category=8, points_one_level_diff=7, 
                         points_two_level_diff=6, points_three_level_diff=5),
                Category(name="White", color="white", priority=4, 
                         points_same_category=8, points_one_level_diff=7, 
                         points_two_level_diff=6, points_three_level_diff=5)
            ]
            
            db.session.add_all(categories)
            db.session.commit()
            print("Created default categories (Red, Black, Blue, White)")
        else:
            print("Categories already exist, skipping creation")
        
        # Initialize TeamStats for all teams if they don't exist
        teams = Team.query.all()
        for team in teams:
            if not TeamStats.query.filter_by(team_id=team.id).first():
                team_stats = TeamStats(team_id=team.id)
                db.session.add(team_stats)
                
        db.session.commit()
        print(f"Initialized team stats for {len(teams)} teams")
        
        print("Team management database initialization complete!")

if __name__ == "__main__":
    init_team_management_db() 